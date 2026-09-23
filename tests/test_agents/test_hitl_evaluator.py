"""Unit test cho Dynamic Risk-based HITL Gatekeeper Evaluator (hitl_evaluator.py)."""

from src.agents.control_pipeline.hitl_evaluator import (
    evaluate_query_risk,
    has_cartesian_join_risk,
    has_time_filter_in_where,
)
from src.config import Settings
from src.utils.db_connector import CostEstimateResult


def test_has_time_filter_in_where_positive():
    time_cols = {"shipdate", "orderdate", "date"}

    sql1 = "SELECT * FROM lineitem WHERE l_shipdate >= DATE '1995-01-01'"
    assert has_time_filter_in_where(sql1, time_cols) is True

    sql2 = "SELECT * FROM orders WHERE o_orderdate BETWEEN '1995-01-01' AND '1995-12-31'"
    assert has_time_filter_in_where(sql2, time_cols) is True

    sql3 = "SELECT * FROM orders WHERE EXTRACT(year FROM o_orderdate) = 1995"
    assert has_time_filter_in_where(sql3, time_cols) is True


def test_has_time_filter_in_where_negative():
    time_cols = {"shipdate", "orderdate", "date"}

    sql1 = "SELECT * FROM lineitem WHERE l_discount > 0.05"
    assert has_time_filter_in_where(sql1, time_cols) is False

    sql2 = "SELECT count(*) FROM lineitem"
    assert has_time_filter_in_where(sql2, time_cols) is False


def test_has_cartesian_join_risk():
    sql_cross = "SELECT * FROM customer CROSS JOIN orders"
    assert has_cartesian_join_risk(sql_cross) is True

    sql_normal = "SELECT * FROM customer JOIN orders ON c_custkey = o_custkey"
    assert has_cartesian_join_risk(sql_normal) is False


def test_evaluate_query_risk_safe_query():
    """Truy vấn bảng nhỏ hoặc dung lượng thấp: không kích hoạt HITL."""
    cfg = Settings(
        hitl_enabled=True,
        hitl_heavy_tables="lineitem,orders",
        hitl_budget_ratio_threshold=0.4,
        hitl_rows_threshold=500_000,
    )
    estimate = CostEstimateResult(
        estimated_bytes=100_000,  # 100 KB
        estimated_rows=25,
        is_within_budget=True,
        max_budget_bytes=1_000_000_000,
    )
    is_hitl, reason, score = evaluate_query_risk(
        sql="SELECT * FROM nation WHERE n_regionkey = 1",
        estimate=estimate,
        tables_used=["nation"],
        settings=cfg,
    )
    assert is_hitl is False
    assert score < 50


def test_evaluate_query_risk_heavy_table_without_time_filter():
    """Truy vấn bảng lớn lineitem không có filter thời gian: kích hoạt HITL."""
    cfg = Settings(
        hitl_enabled=True,
        hitl_heavy_tables="lineitem,orders",
        hitl_budget_ratio_threshold=0.4,
        hitl_rows_threshold=500_000,
    )
    estimate = CostEstimateResult(
        estimated_bytes=300_000_000,  # 300 MB
        estimated_rows=600_000,
        is_within_budget=True,
        max_budget_bytes=1_000_000_000,
    )
    is_hitl, reason, score = evaluate_query_risk(
        sql="SELECT l_returnflag, sum(l_quantity) FROM lineitem GROUP BY l_returnflag",
        estimate=estimate,
        tables_used=["lineitem"],
        settings=cfg,
    )
    assert is_hitl is True
    assert score >= 50
    assert "bảng dữ liệu lớn" in reason.lower() or "lineitem" in reason.lower()


def test_evaluate_query_risk_heavy_table_with_time_filter():
    """Truy vấn bảng lớn lineitem nhưng có filter thời gian và dung lượng vừa phải: cho qua."""
    cfg = Settings(
        hitl_enabled=True,
        hitl_heavy_tables="lineitem,orders",
        hitl_budget_ratio_threshold=0.4,
        hitl_rows_threshold=500_000,
    )
    estimate = CostEstimateResult(
        estimated_bytes=50_000_000,  # 50 MB
        estimated_rows=50_000,
        is_within_budget=True,
        max_budget_bytes=1_000_000_000,
    )
    is_hitl, reason, score = evaluate_query_risk(
        sql="SELECT sum(l_extendedprice) FROM lineitem WHERE l_shipdate >= DATE '1995-01-01'",
        estimate=estimate,
        tables_used=["lineitem"],
        settings=cfg,
    )
    assert is_hitl is False
    assert score < 50


def test_evaluate_query_risk_disabled():
    """Khi cấu hình tắt HITL: luôn trả về False."""
    cfg = Settings(hitl_enabled=False)
    estimate = CostEstimateResult(
        estimated_bytes=900_000_000,
        estimated_rows=10_000_000,
        is_within_budget=True,
        max_budget_bytes=1_000_000_000,
    )
    is_hitl, reason, score = evaluate_query_risk(
        sql="SELECT * FROM lineitem",
        estimate=estimate,
        tables_used=["lineitem"],
        settings=cfg,
    )
    assert is_hitl is False
    assert score == 0
