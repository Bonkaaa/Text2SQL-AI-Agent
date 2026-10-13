"""Unit tests for Spider-like Benchmark Runner (evals/benchmark_runner.py)."""

import json
from datetime import UTC
from pathlib import Path

import duckdb
import pytest

from evals.benchmark_runner import (
    compare_query_results,
    evaluate_single_query,
    normalize_value,
    run_benchmark,
)
from src.config import get_settings


def test_runner_uses_default_tpch_db_path():
    settings = get_settings()
    assert "tpch.duckdb" in settings.duckdb_path
    # Check default in benchmark_runner function signature
    import inspect
    sig = inspect.signature(run_benchmark)
    default_db = sig.parameters["db_path"].default
    assert "tpcds" not in default_db.lower(), f"db_path default still points to TPC-DS: {default_db}"
    assert "tpch" in default_db.lower(), f"db_path default should point to TPC-H: {default_db}"


def test_normalize_value():
    from datetime import date, datetime
    from decimal import Decimal

    assert normalize_value(None) is None
    assert normalize_value(3.14159) == 3.14
    assert normalize_value(Decimal("100.50")) == 100.5
    assert normalize_value(Decimal("100.5")) == 100.5
    assert normalize_value(date(2023, 1, 1)) == "2023-01-01"
    assert normalize_value(datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)) == "2023-01-01T12:00:00+00:00"
    assert normalize_value(42) == 42
    assert normalize_value("test") == "test"
    assert normalize_value(float("nan")) == "NaN"


def test_compare_query_results_decimal_and_float_equivalence():
    from decimal import Decimal

    res1 = [(Decimal("100.50"), "A")]
    res2 = [(100.5, "A")]
    assert compare_query_results(res1, res2) is True


def test_compare_query_results_identical():
    res1 = [("A", 10.0, 1), ("B", 20.0, 2)]
    res2 = [("A", 10.0, 1), ("B", 20.0, 2)]
    assert compare_query_results(res1, res2) is True


def test_compare_query_results_multiset_unordered():
    res1 = [("A", 10.0), ("B", 20.0)]
    res2 = [("B", 20.0), ("A", 10.0)]
    assert compare_query_results(res1, res2) is True


def test_compare_query_results_mismatch():
    res1 = [("A", 10.0)]
    res2 = [("A", 15.0)]
    assert compare_query_results(res1, res2) is False

    res3 = [("A", 10.0), ("B", 20.0)]
    assert compare_query_results(res1, res3) is False


@pytest.mark.asyncio
async def test_evaluate_single_query_mock(tmp_path: Path):
    db_file = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_file))
    con.execute("CREATE TABLE orders (o_orderkey INT, o_totalprice DOUBLE);")
    con.execute("INSERT INTO orders VALUES (1, 100.0), (2, 250.0);")

    item = {
        "id": "q_test",
        "question": "Tổng số đơn hàng?",
        "difficulty": "EASY",
        "category": "Aggregation",
        "tables": ["orders"],
        "ground_truth_sql": "SELECT count(*) FROM orders;",
    }

    result = await evaluate_single_query(item, con, mock=True)
    assert result.is_valid_sql is True
    assert result.is_execution_match is True
    assert result.error_message is None
    assert result.expected_rows == 1
    assert result.actual_rows == 1
    con.close()


@pytest.mark.asyncio
async def test_run_benchmark_mock_workflow(tmp_path: Path):
    db_file = tmp_path / "test_benchmark.duckdb"
    con = duckdb.connect(str(db_file))
    con.execute("CREATE TABLE customer (c_custkey INT, c_name VARCHAR);")
    con.execute("INSERT INTO customer VALUES (1, 'Customer#1'), (2, 'Customer#2');")
    con.close()

    dataset_file = tmp_path / "bench_mini.json"
    dataset_content = [
        {
            "id": "q01",
            "question": "Đếm khách hàng?",
            "difficulty": "EASY",
            "category": "Aggregation",
            "tables": ["customer"],
            "ground_truth_sql": "SELECT count(*) FROM customer;",
        },
        {
            "id": "q02",
            "question": "Danh sách mã khách hàng?",
            "difficulty": "EASY",
            "category": "Scan",
            "tables": ["customer"],
            "ground_truth_sql": "SELECT c_custkey FROM customer ORDER BY c_custkey;",
        },
    ]
    dataset_file.write_text(json.dumps(dataset_content), encoding="utf-8")
    report_file = tmp_path / "reports" / "report.json"

    summary = await run_benchmark(
        dataset_path=str(dataset_file),
        limit=2,
        output_path=str(report_file),
        db_path=str(db_file),
        mock=True,
    )

    assert summary.total_queries == 2
    assert summary.valid_sql_count == 2
    assert summary.execution_match_count == 2
    assert summary.vsr == 100.0
    assert summary.ex == 100.0
    assert report_file.exists()

    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["total_queries"] == 2
    assert report_data["vsr"] == 100.0
    assert report_data["ex"] == 100.0
