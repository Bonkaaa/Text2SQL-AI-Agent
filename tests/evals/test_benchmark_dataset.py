"""Unit tests for TPC-H benchmark dataset integrity and ground-truth execution."""

import json
from pathlib import Path

import duckdb

from src.config import get_settings

settings = get_settings()

DATASET_PATH = Path("evals/datasets/benchmark_vi.json")
TPCH_TABLES = {
    "customer",
    "orders",
    "lineitem",
    "part",
    "partsupp",
    "supplier",
    "nation",
    "region",
}
TPCDS_OLD_TABLES = {
    "store_sales",
    "web_sales",
    "catalog_sales",
    "store_returns",
    "web_returns",
    "catalog_returns",
    "item",
    "date_dim",
    "customer_demographics",
    "household_demographics",
}


def load_dataset() -> list[dict]:
    assert DATASET_PATH.exists(), f"Dataset file does not exist: {DATASET_PATH}"
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_dataset_exists_and_has_50_queries():
    data = load_dataset()
    assert len(data) == 50, f"Expected 50 questions, found {len(data)}"


def test_question_schema_fields():
    data = load_dataset()
    for item in data:
        assert "id" in item, "Missing id"
        assert "question" in item and len(item["question"].strip()) > 0, f"Empty question in {item.get('id')}"
        assert "difficulty" in item and item["difficulty"] in {"EASY", "MEDIUM", "HARD"}, f"Invalid difficulty in {item.get('id')}"
        assert "category" in item, f"Missing category in {item.get('id')}"
        assert "tables" in item and isinstance(item["tables"], list) and len(item["tables"]) > 0, f"Invalid tables in {item.get('id')}"
        assert "ground_truth_sql" in item and len(item["ground_truth_sql"].strip()) > 0, f"Empty ground_truth_sql in {item.get('id')}"


def test_tables_are_strictly_tpch():
    data = load_dataset()
    for item in data:
        for tbl in item["tables"]:
            tbl_lower = tbl.lower()
            assert tbl_lower in TPCH_TABLES, f"Question {item['id']} references non-TPC-H table: {tbl}"
            assert tbl_lower not in TPCDS_OLD_TABLES, f"Question {item['id']} references old TPC-DS table: {tbl}"


def test_all_ground_truth_sqls_executable():
    data = load_dataset()
    db_path = settings.duckdb_path
    assert Path(db_path).exists(), f"DuckDB warehouse not found at {db_path}"
    con = duckdb.connect(db_path, read_only=True)
    failures = []
    try:
        for item in data:
            sql = item["ground_truth_sql"].strip().rstrip(";")
            try:
                con.execute(sql).fetchall()
            except Exception as e:  # noqa: BLE001
                failures.append((item["id"], str(e), sql))
    finally:
        con.close()

    assert not failures, f"{len(failures)} queries failed execution:\n" + "\n".join(
        f"- {qid}: {err}\n  SQL: {sql}" for qid, err, sql in failures
    )
