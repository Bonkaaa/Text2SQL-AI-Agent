import pytest

from src.utils.db_connector import DuckDBConnector
from src.utils.tpch_seeder import seed_tpch_data


@pytest.fixture(scope="module")
def memory_db_connector():
    """Fixture tạo connector kết nối tới DuckDB in-memory có sẵn dữ liệu TPC-H."""
    conn = seed_tpch_data(db_path=":memory:", scale_factor=0.01)
    connector = DuckDBConnector(connection=conn)
    yield connector
    conn.close()


def test_execute_valid_query(memory_db_connector: DuckDBConnector):
    """Kiểm tra thực thi truy vấn hợp lệ trả về dữ liệu bảng và thời gian thực thi."""
    sql = "SELECT c_custkey, c_name, c_mktsegment FROM customer LIMIT 5"
    result = memory_db_connector.execute_query(sql)

    assert result.success is True
    assert result.row_count == 5
    assert len(result.data) == 5
    assert result.columns == ["c_custkey", "c_name", "c_mktsegment"]
    assert result.execution_time_ms >= 0.0
    assert result.error_message is None

    # Kiểm tra cấu trúc bản ghi dạng dict
    first_row = result.data[0]
    assert "c_custkey" in first_row
    assert "c_name" in first_row
    assert "c_mktsegment" in first_row


def test_execute_empty_result(memory_db_connector: DuckDBConnector):
    """Kiểm tra truy vấn hợp lệ nhưng không có bản ghi nào khớp điều kiện."""
    sql = "SELECT * FROM customer WHERE c_custkey = -99999"
    result = memory_db_connector.execute_query(sql)

    assert result.success is True
    assert result.row_count == 0
    assert result.data == []
    assert len(result.columns) > 0


def test_execute_database_error(memory_db_connector: DuckDBConnector):
    """Kiểm tra xử lý lỗi khi query cột hoặc bảng không tồn tại trong database."""
    sql = "SELECT column_does_not_exist FROM customer"
    result = memory_db_connector.execute_query(sql)

    assert result.success is False
    assert result.error_message is not None
    assert "column_does_not_exist" in result.error_message.lower()


def test_estimate_query_cost_within_budget(memory_db_connector: DuckDBConnector):
    """Kiểm tra ước lượng chi phí bằng EXPLAIN nằm trong ngân sách cho phép (1GB)."""
    sql = "SELECT * FROM lineitem JOIN orders ON l_orderkey = o_orderkey LIMIT 100"
    estimate = memory_db_connector.estimate_query_cost(
        sql,
        max_budget_bytes=1073741824,  # 1GB
    )

    assert estimate.is_within_budget is True
    assert estimate.estimated_bytes > 0
    assert estimate.estimated_rows > 0
    assert estimate.max_budget_bytes == 1073741824
    # Kiểm tra đã sử dụng đúng DuckDB EXPLAIN execution plan
    assert "EXPLAIN Cost Guard" in estimate.explanation
    assert "lineitem" in estimate.explanation


def test_estimate_query_cost_exceeds_budget(memory_db_connector: DuckDBConnector):
    """Kiểm tra chặn truy vấn khi chi phí ước lượng từ EXPLAIN vượt quá ngân sách."""
    sql = "SELECT * FROM lineitem"
    # Đặt budget cực nhỏ (100 bytes) để kích hoạt vượt budget
    estimate = memory_db_connector.estimate_query_cost(sql, max_budget_bytes=100)

    assert estimate.is_within_budget is False
    assert estimate.estimated_bytes > estimate.max_budget_bytes
    assert estimate.explanation is not None
    assert "EXPLAIN Cost Guard" in estimate.explanation


def test_execute_query_timeout(memory_db_connector: DuckDBConnector):
    """Kiểm tra xử lý timeout khi thực thi truy vấn vượt quá thời gian cho phép."""
    import concurrent.futures
    from unittest.mock import patch

    sql = "SELECT * FROM lineitem"
    with patch(
        "concurrent.futures.Future.result",
        side_effect=concurrent.futures.TimeoutError(),
    ):
        result = memory_db_connector.execute_query(sql, timeout_seconds=1)

    assert result.success is False
    assert result.error_message is not None
    assert "thời gian tối đa" in result.error_message
