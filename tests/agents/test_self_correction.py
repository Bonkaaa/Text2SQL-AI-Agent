"""Unit tests cho Component 3.3: Bounded Self-Correction Loop."""

from unittest.mock import patch

import pytest

from src.agents.self_correction import (
    run_self_correction_loop,
)
from src.models.rbac import UserContext, UserRole
from src.models.state import (
    SelfCorrectionResult,
    SQLGenerationResult,
)
from src.utils.db_connector import DuckDBConnector
from src.utils.tpch_seeder import seed_tpch_data


@pytest.fixture(scope="module")
def tpch_connector():
    """Fixture DuckDB in-memory với bảng TPC-H mẫu."""
    conn = seed_tpch_data(db_path=":memory:", scale_factor=0.01)
    connector = DuckDBConnector(connection=conn)
    yield connector
    conn.close()


@pytest.fixture
def default_user_context():
    """Fixture cung cấp UserContext chuẩn cho vai trò Analyst."""
    return UserContext(
        user_id="analyst_test",
        session_id="session_test_self_correction",
        role=UserRole.ANALYST,
    )


def test_self_correction_result_model():
    """Kiểm tra validation và các trường dữ liệu của SelfCorrectionResult."""
    res = SelfCorrectionResult(
        success=True,
        sql="SELECT c_custkey, c_name FROM customer LIMIT 5;",
        data=[{"c_custkey": 1, "c_name": "Customer#000000001"}],
        columns=["c_custkey", "c_name"],
        retry_count=1,
        explanation="Truy vấn lấy 5 khách hàng đầu tiên.",
        execution_time_ms=12.5,
        bytes_scanned=1024,
        history=[
            {"attempt": 1, "sql": "SELECT c_phone FROM customer", "is_valid": False},
            {"attempt": 2, "sql": "SELECT c_name FROM customer", "is_valid": True},
        ],
    )

    assert res.success is True
    assert res.retry_count == 1
    assert len(res.data) == 1
    assert len(res.history) == 2
    assert res.error_message is None


@patch("src.agents.self_correction.generate_sql")
@patch("src.agents.self_correction.run_control_pipeline")
def test_self_correction_immediate_success(
    mock_run_pipeline,
    mock_generate_sql,
    default_user_context,
):
    """Kiểm tra trường hợp câu query hợp lệ ngay từ lần sinh đầu tiên (retry_count = 0)."""
    mock_generate_sql.return_value = SQLGenerationResult(
        sql="SELECT c_custkey, c_name FROM customer LIMIT 10;",
        dialect="duckdb",
        explanation="Lấy 10 khách hàng",
        assumptions=[],
    )

    mock_run_pipeline.return_value = {
        "is_valid": True,
        "status": "SUCCESS",
        "error_type": None,
        "error_message": None,
        "actionable_feedback": None,
        "diagnostic_result": None,
        "data": [{"c_custkey": 1, "c_name": "Cust1"}],
        "columns": ["c_custkey", "c_name"],
        "bytes_scanned": 2048,
        "execution_time_ms": 15.0,
    }

    result = run_self_correction_loop(
        question="Lấy 10 khách hàng",
        schema_context="Bảng customer",
        user_context=default_user_context,
        session_id="session_immediate_success",
    )

    assert result.success is True
    assert result.retry_count == 0
    assert result.sql == "SELECT c_custkey, c_name FROM customer LIMIT 10;"
    assert len(result.data) == 1
    assert len(result.history) == 1
    assert result.history[0]["attempt"] == 1
    assert result.history[0]["is_valid"] is True

    # Chỉ gọi generate_sql đúng 1 lần với error_context=None
    mock_generate_sql.assert_called_once_with(
        question="Lấy 10 khách hàng",
        schema_context="Bảng customer",
        dialect="duckdb",
        error_context=None,
        llm=None,
    )


@patch("src.agents.self_correction.generate_sql")
@patch("src.agents.self_correction.run_control_pipeline")
def test_self_correction_success_on_second_attempt(
    mock_run_pipeline,
    mock_generate_sql,
    default_user_context,
):
    """Kiểm tra sửa lỗi thành công ở lần thử thứ 2 (retry_count = 1)."""
    # Lần 1: sinh câu lệnh có c_phone (vi phạm RBAC)
    # Lần 2: sửa thành c_name (hợp lệ)
    mock_generate_sql.side_effect = [
        SQLGenerationResult(
            sql="SELECT c_name, c_phone FROM customer LIMIT 5;",
            dialect="duckdb",
            explanation="Lấy tên và số điện thoại",
        ),
        SQLGenerationResult(
            sql="SELECT c_name, c_custkey FROM customer LIMIT 5;",
            dialect="duckdb",
            explanation="Đã sửa loại bỏ c_phone",
        ),
    ]

    mock_run_pipeline.side_effect = [
        {
            "is_valid": False,
            "status": "BLOCKED_RBAC",
            "error_type": "UNAUTHORIZED_COLUMN",
            "error_message": "Cột c_phone bị cấm truy cập theo RBAC",
            "actionable_feedback": "Loại bỏ cột c_phone và thay bằng c_custkey.",
            "diagnostic_result": None,
            "data": None,
            "columns": None,
            "bytes_scanned": 0,
            "execution_time_ms": 5.0,
        },
        {
            "is_valid": True,
            "status": "SUCCESS",
            "error_type": None,
            "error_message": None,
            "actionable_feedback": None,
            "diagnostic_result": None,
            "data": [{"c_name": "Cust1", "c_custkey": 1}],
            "columns": ["c_name", "c_custkey"],
            "bytes_scanned": 2048,
            "execution_time_ms": 10.0,
        },
    ]

    result = run_self_correction_loop(
        question="Lấy khách hàng",
        schema_context="Bảng customer",
        user_context=default_user_context,
        session_id="session_retry_1",
    )

    assert result.success is True
    assert result.retry_count == 1
    assert result.sql == "SELECT c_name, c_custkey FROM customer LIMIT 5;"
    assert len(result.history) == 2
    assert result.history[0]["is_valid"] is False
    assert result.history[1]["is_valid"] is True

    # Kiểm tra lần gọi thứ 2 của generate_sql được nạp đúng error_context
    assert mock_generate_sql.call_count == 2
    second_call_kwargs = mock_generate_sql.call_args_list[1][1]
    assert second_call_kwargs["error_context"] is not None
    assert second_call_kwargs["error_context"]["error_type"] == "UNAUTHORIZED_COLUMN"
    assert (
        "Loại bỏ cột c_phone"
        in second_call_kwargs["error_context"]["actionable_feedback"]
    )


@patch("src.agents.self_correction.generate_sql")
@patch("src.agents.self_correction.run_control_pipeline")
def test_self_correction_success_on_third_attempt(
    mock_run_pipeline,
    mock_generate_sql,
    default_user_context,
):
    """Kiểm tra sửa lỗi thành công ở lần thử thứ 3 (retry_count = 2)."""
    mock_generate_sql.side_effect = [
        SQLGenerationResult(sql="SELECT * FORM orders", explanation="Lỗi syntax"),
        SQLGenerationResult(sql="SELECT * FROM lineitem", explanation="Lỗi cost"),
        SQLGenerationResult(
            sql="SELECT l_orderkey FROM lineitem LIMIT 10", explanation="Thành công"
        ),
    ]

    mock_run_pipeline.side_effect = [
        {
            "is_valid": False,
            "status": "BLOCKED_AST",
            "error_type": "SYNTAX_ERROR",
            "error_message": "Syntax error",
            "actionable_feedback": "Sửa FORM thành FROM",
        },
        {
            "is_valid": False,
            "status": "BLOCKED_COST",
            "error_type": "EXCEEDED_COST_LIMIT",
            "error_message": "Scan quá lớn",
            "actionable_feedback": "Thêm LIMIT",
        },
        {
            "is_valid": True,
            "status": "SUCCESS",
            "data": [{"l_orderkey": 1}],
            "columns": ["l_orderkey"],
            "bytes_scanned": 100,
            "execution_time_ms": 8.0,
        },
    ]

    result = run_self_correction_loop(
        question="Lấy lineitem",
        schema_context="Bảng lineitem",
        user_context=default_user_context,
        session_id="session_retry_2",
    )

    assert result.success is True
    assert result.retry_count == 2
    assert len(result.history) == 3
    assert result.sql == "SELECT l_orderkey FROM lineitem LIMIT 10"


@patch("src.agents.self_correction.generate_sql")
@patch("src.agents.self_correction.run_control_pipeline")
def test_self_correction_exceeds_max_retries_graceful_exit(
    mock_run_pipeline,
    mock_generate_sql,
    default_user_context,
):
    """Kiểm tra khi thất bại liên tiếp 3 lần retry (tổng 4 lượt gọi) -> dừng lại an toàn."""
    # 4 lần sinh đều bị fail
    mock_generate_sql.return_value = SQLGenerationResult(
        sql="DROP TABLE orders;",
        explanation="Thử drop table",
    )

    mock_run_pipeline.return_value = {
        "is_valid": False,
        "status": "BLOCKED_AST",
        "error_type": "FORBIDDEN_STATEMENT",
        "error_message": "Không được phép DROP TABLE",
        "actionable_feedback": "Chỉ được dùng câu lệnh SELECT đọc dữ liệu.",
        "diagnostic_result": None,
        "data": None,
        "columns": None,
        "bytes_scanned": 0,
        "execution_time_ms": 2.0,
    }

    result = run_self_correction_loop(
        question="Xóa đơn hàng",
        schema_context="Bảng orders",
        user_context=default_user_context,
        session_id="session_fail_max",
        max_retries=3,
    )

    assert result.success is False
    assert result.retry_count == 3
    # Tổng cộng 4 lần chạy (1 lần đầu + 3 lần retry)
    assert len(result.history) == 4
    assert mock_generate_sql.call_count == 4
    assert mock_run_pipeline.call_count == 4
    # Thông báo lỗi thân thiện được tạo ra
    assert result.error_message is not None
    assert (
        "sau 3 lần thử tự sửa lỗi" in result.error_message
        or "tự động sửa lỗi" in result.error_message.lower()
    )


@patch("src.agents.self_correction.generate_sql")
@patch("src.agents.self_correction.run_control_pipeline")
def test_self_correction_custom_max_retries(
    mock_run_pipeline,
    mock_generate_sql,
    default_user_context,
):
    """Kiểm tra tham số max_retries tùy biến (ví dụ max_retries = 1)."""
    mock_generate_sql.return_value = SQLGenerationResult(
        sql="SELECT c_phone FROM customer",
        explanation="Query cấm",
    )

    mock_run_pipeline.return_value = {
        "is_valid": False,
        "status": "BLOCKED_RBAC",
        "error_type": "UNAUTHORIZED_COLUMN",
        "error_message": "Cột cấm",
        "actionable_feedback": "Loại bỏ cột cấm",
    }

    result = run_self_correction_loop(
        question="Lấy số điện thoại",
        schema_context="Bảng customer",
        user_context=default_user_context,
        session_id="session_custom_retries",
        max_retries=1,
    )

    assert result.success is False
    assert result.retry_count == 1
    # 1 lần đầu + 1 lần retry = 2 attempts
    assert len(result.history) == 2
    assert mock_generate_sql.call_count == 2
    assert mock_run_pipeline.call_count == 2


def test_self_correction_with_real_duckdb_control_pipeline(
    tpch_connector,
    default_user_context,
):
    """Kiểm tra tích hợp thực tế với Control Pipeline Graph trên cơ sở dữ liệu DuckDB."""
    from src.agents.control_pipeline import build_control_pipeline_graph

    graph = build_control_pipeline_graph(db_connector=tpch_connector)

    # Giả lập LLM: lần 1 sinh SQL sai cú pháp, lần 2 sinh SQL chuẩn DuckDB
    call_count = 0

    def mock_generate(
        question, schema_context, dialect="duckdb", error_context=None, llm=None
    ):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Query lỗi cú pháp
            return SQLGenerationResult(
                sql="SELECT * FORM customer LIMIT 5;",
                dialect="duckdb",
                explanation="Cố tình sai FORM",
            )
        else:
            # Query đúng
            return SQLGenerationResult(
                sql="SELECT c_custkey, c_name FROM customer LIMIT 3;",
                dialect="duckdb",
                explanation="Đã sửa thành FROM",
            )

    with patch("src.agents.self_correction.generate_sql", side_effect=mock_generate):
        result = run_self_correction_loop(
            question="Lấy 3 khách hàng",
            schema_context="Bảng customer: c_custkey, c_name",
            user_context=default_user_context,
            session_id="session_real_duckdb_test",
            control_pipeline_graph=graph,
        )

        assert result.success is True
        assert result.retry_count == 1
        assert len(result.data) == 3
        assert result.columns == ["c_custkey", "c_name"]
        assert len(result.history) == 2
        assert result.history[0]["is_valid"] is False
        assert result.history[1]["is_valid"] is True
