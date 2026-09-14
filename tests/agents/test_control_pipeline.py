from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.agents.control_pipeline import (
    build_control_pipeline_graph,
    run_control_pipeline,
)
from src.models.rbac import UserContext, UserRole
from src.models.state import ControlPipelineInput, ControlState
from src.utils.audit_logger import AuditLogger
from src.utils.db_connector import DuckDBConnector
from src.utils.tpch_seeder import seed_tpch_data


@pytest.fixture(scope="module")
def shared_tpch_connector():
    """Fixture cung cấp kết nối DuckDB in-memory với 8 bảng TPC-H."""
    conn = seed_tpch_data(db_path=":memory:", scale_factor=0.01)
    connector = DuckDBConnector(connection=conn)
    yield connector
    conn.close()


@pytest.fixture
def temp_audit_logger(tmp_path: Path):
    """Fixture cung cấp AuditLogger ghi ra thư mục tạm thời."""
    log_file = tmp_path / "test_control_audit.jsonl"
    return AuditLogger(log_file_path=str(log_file))


def test_pipeline_valid_query_success(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra câu query hợp lệ: chạy thông suốt qua AST -> RBAC -> Cost -> Execute -> Audit."""
    user_context = UserContext(
        user_id="analyst_1",
        session_id="session_success",
        role=UserRole.ANALYST,
    )
    input_data: ControlPipelineInput = {
        "sql": "SELECT c_custkey, c_name, c_mktsegment FROM customer LIMIT 5",
        "user_context": user_context,
        "session_id": "session_success",
    }

    graph = build_control_pipeline_graph(
        db_connector=shared_tpch_connector, audit_logger=temp_audit_logger
    )
    output = run_control_pipeline(graph, input_data)

    assert output["is_valid"] is True
    assert output["status"] == "SUCCESS"
    assert output["data"] is not None
    assert len(output["data"]) == 5
    assert output["columns"] == ["c_custkey", "c_name", "c_mktsegment"]
    assert output["error_message"] is None
    assert output["execution_time_ms"] > 0

    # Kiểm tra Audit Log đã ghi nhận sự kiện SUCCESS
    logs = temp_audit_logger.get_logs(session_id="session_success")
    assert len(logs) == 1
    assert logs[0].status == "SUCCESS"
    assert logs[0].user_id == "analyst_1"


def test_pipeline_blocked_by_ast_sanitizer(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra chặn câu lệnh DDL/DML cấm (DROP TABLE) ngay tại AST_CHECK."""
    user_context = UserContext(
        user_id="analyst_bad",
        session_id="session_ast_block",
        role=UserRole.ANALYST,
    )
    input_data: ControlPipelineInput = {
        "sql": "DROP TABLE customer;",
        "user_context": user_context,
        "session_id": "session_ast_block",
    }

    graph = build_control_pipeline_graph(
        db_connector=shared_tpch_connector, audit_logger=temp_audit_logger
    )
    output = run_control_pipeline(graph, input_data)

    assert output["is_valid"] is False
    assert output["status"] == "BLOCKED_AST"
    assert output["error_type"] == "FORBIDDEN_STATEMENT"
    assert output["data"] is None
    # Actionable Feedback từ Diagnostic Agent phải được tạo ra
    assert output["actionable_feedback"] is not None
    assert len(output["actionable_feedback"]) > 0

    # Kiểm tra Audit Log
    logs = temp_audit_logger.get_logs(session_id="session_ast_block")
    assert len(logs) == 1
    assert logs[0].status == "BLOCKED_AST"


def test_pipeline_blocked_by_rbac_forbidden_column(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra chặn role Analyst khi truy vấn cột cấm (c_phone, c_acctbal)."""
    user_context = UserContext(
        user_id="analyst_rbac",
        session_id="session_rbac_block",
        role=UserRole.ANALYST,
    )
    input_data: ControlPipelineInput = {
        "sql": "SELECT c_name, c_phone FROM customer LIMIT 5",
        "user_context": user_context,
        "session_id": "session_rbac_block",
    }

    graph = build_control_pipeline_graph(
        db_connector=shared_tpch_connector, audit_logger=temp_audit_logger
    )
    output = run_control_pipeline(graph, input_data)

    assert output["is_valid"] is False
    assert output["status"] == "BLOCKED_RBAC"
    assert output["error_type"] == "UNAUTHORIZED_COLUMN"
    assert "c_phone" in output["error_message"]
    # Diagnostic feedback nhắc nhở cột thay thế
    assert output["actionable_feedback"] is not None
    assert "c_phone" in output["actionable_feedback"]

    logs = temp_audit_logger.get_logs(session_id="session_rbac_block")
    assert len(logs) == 1
    assert logs[0].status == "BLOCKED_RBAC"


def test_pipeline_blocked_by_cost_guard(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra chặn câu lệnh có chi phí quét dữ liệu vượt quá ngân sách."""
    user_context = UserContext(
        user_id="analyst_cost",
        session_id="session_cost_block",
        role=UserRole.ANALYST,
        max_cost_bytes=50,  # Ngân sách cực nhỏ để kích hoạt vi phạm
    )
    input_data: ControlPipelineInput = {
        "sql": "SELECT * FROM lineitem",
        "user_context": user_context,
        "session_id": "session_cost_block",
    }

    graph = build_control_pipeline_graph(
        db_connector=shared_tpch_connector, audit_logger=temp_audit_logger
    )
    output = run_control_pipeline(graph, input_data)

    assert output["is_valid"] is False
    assert output["status"] == "BLOCKED_COST"
    assert output["error_type"] == "EXCEEDED_COST_LIMIT"
    assert output["actionable_feedback"] is not None


def test_pipeline_runtime_database_error(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra xử lý lỗi runtime database (cột không tồn tại) và chẩn đoán."""
    user_context = UserContext(
        user_id="analyst_db_err",
        session_id="session_db_error",
        role=UserRole.ANALYST,
    )
    input_data: ControlPipelineInput = {
        "sql": "SELECT column_does_not_exist FROM customer",
        "user_context": user_context,
        "session_id": "session_db_error",
    }

    graph = build_control_pipeline_graph(
        db_connector=shared_tpch_connector, audit_logger=temp_audit_logger
    )
    output = run_control_pipeline(graph, input_data)

    assert output["is_valid"] is False
    assert output["status"] == "DB_ERROR"
    assert output["error_type"] == "RUNTIME_ERROR"
    assert output["error_message"] is not None
    assert output["actionable_feedback"] is not None

    logs = temp_audit_logger.get_logs(session_id="session_db_error")
    assert len(logs) == 1
    assert logs[0].status == "DB_ERROR"


def test_pipeline_query_timeout(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra xử lý timeout khi truy vấn chạy quá lâu."""
    user_context = UserContext(
        user_id="analyst_timeout",
        session_id="session_timeout",
        role=UserRole.ANALYST,
    )
    input_data: ControlPipelineInput = {
        "sql": "SELECT * FROM lineitem",
        "user_context": user_context,
        "session_id": "session_timeout",
    }

    # Mock execute_query để giả lập timeout
    import concurrent.futures

    with patch(
        "concurrent.futures.Future.result",
        side_effect=concurrent.futures.TimeoutError(),
    ):
        graph = build_control_pipeline_graph(
            db_connector=shared_tpch_connector, audit_logger=temp_audit_logger
        )
        output = run_control_pipeline(graph, input_data)

    assert output["is_valid"] is False
    assert output["status"] == "TIMEOUT"
    assert output["error_type"] == "TIMEOUT"
    assert output["actionable_feedback"] is not None

    logs = temp_audit_logger.get_logs(session_id="session_timeout")
    assert len(logs) == 1
    assert logs[0].status == "TIMEOUT"


def test_pipeline_hitl_approval_flow(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra cơ chế Human-in-the-loop (HITL) qua LangGraph interrupt()."""
    checkpointer = MemorySaver()
    graph = build_control_pipeline_graph(
        db_connector=shared_tpch_connector,
        audit_logger=temp_audit_logger,
        checkpointer=checkpointer,
    )

    user_context = UserContext(
        user_id="analyst_hitl",
        session_id="session_hitl_test",
        role=UserRole.ANALYST,
    )
    # Khởi tạo state với yêu cầu HITL
    initial_state: ControlState = {
        "sql": "SELECT c_name FROM customer LIMIT 3",
        "user_context": user_context,
        "session_id": "session_hitl_test",
        "hitl_required": True,
    }

    thread_config = {"configurable": {"thread_id": "session_hitl_test"}}

    # Chạy lần đầu -> graph sẽ tạm dừng tại hitl_gate do interrupt
    graph.invoke(initial_state, config=thread_config)

    # Lấy snapshot hiện tại của graph
    snapshot = graph.get_state(thread_config)
    assert len(snapshot.tasks) > 0
    # Kiểm tra payload interrupt
    interrupt_payload = snapshot.tasks[0].interrupts[0].value
    assert "sql" in interrupt_payload

    # Kịch bản 1: Người dùng Phê duyệt (approved = True)
    resume_command = {"hitl_approved": True}
    resumed_state = graph.invoke(Command(resume=resume_command), config=thread_config)

    output = resumed_state.get("execution_result")
    assert output is not None
    assert output["is_valid"] is True
    assert output["status"] == "SUCCESS"


def test_pipeline_hitl_rejection_flow(
    shared_tpch_connector: DuckDBConnector, temp_audit_logger: AuditLogger
):
    """Kiểm tra kịch bản người dùng từ chối (hitl_approved = False) -> BLOCKED_HITL."""
    checkpointer = MemorySaver()
    graph = build_control_pipeline_graph(
        db_connector=shared_tpch_connector,
        audit_logger=temp_audit_logger,
        checkpointer=checkpointer,
    )

    user_context = UserContext(
        user_id="analyst_hitl_reject",
        session_id="session_hitl_reject_test",
        role=UserRole.ANALYST,
    )
    initial_state: ControlState = {
        "sql": "SELECT c_name FROM customer LIMIT 5",
        "user_context": user_context,
        "session_id": "session_hitl_reject_test",
        "hitl_required": True,
    }

    thread_config = {"configurable": {"thread_id": "session_hitl_reject_test"}}
    graph.invoke(initial_state, config=thread_config)

    # Người dùng Từ chối (approved = False)
    reject_command = {"hitl_approved": False}
    resumed_state = graph.invoke(Command(resume=reject_command), config=thread_config)

    output = resumed_state.get("execution_result")
    assert output is not None
    assert output["is_valid"] is False
    assert output["status"] == "BLOCKED_HITL"
    assert output["error_type"] == "HITL_REJECTED"
    assert output["actionable_feedback"] is not None


def test_error_diagnostic_agent_with_mock_llm():
    """Kiểm tra node ERROR_DIAGNOSTIC_AGENT khi có LLM trả về phân tích dạng text."""
    from src.agents.control_pipeline.diagnostic import error_diagnostic_node
    from src.models.state import DiagnosticResult

    mock_llm = MagicMock(spec=["invoke"])
    mock_llm.invoke.return_value = AIMessage(
        content="Cột 'c_phone' là cột nhạy cảm bị cấm đối với Analyst. Hãy dùng 'c_name' hoặc 'c_custkey'."
    )

    state: ControlState = {
        "sql": "SELECT c_phone FROM customer",
        "session_id": "sess_diag",
        "schema_context": "Bảng customer có c_custkey, c_name, c_phone (PII cấm)",
        "execution_result": {
            "is_valid": False,
            "status": "BLOCKED_RBAC",
            "error_type": "UNAUTHORIZED_COLUMN",
            "error_message": "Cấm truy cập cột c_phone",
            "actionable_feedback": None,
            "diagnostic_result": None,
            "data": None,
            "columns": None,
            "bytes_scanned": 0,
            "execution_time_ms": 0.0,
        },
    }

    update = error_diagnostic_node(state, llm=mock_llm)
    assert "actionable_feedback" in update
    assert "diagnostic_result" in update
    assert isinstance(update["diagnostic_result"], DiagnosticResult)
    assert update["diagnostic_result"].error_category == "RBAC_VIOLATION"
    assert "c_phone" in update["actionable_feedback"]
    assert "c_name" in update["actionable_feedback"]


def test_error_diagnostic_agent_with_structured_output():
    """Kiểm tra node ERROR_DIAGNOSTIC_AGENT khi LLM hỗ trợ with_structured_output."""
    from src.agents.control_pipeline.diagnostic import error_diagnostic_node
    from src.models.state import DiagnosticResult

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    expected_result = DiagnosticResult(
        error_category="RBAC_VIOLATION",
        root_cause="Cột c_phone bị cấm truy cập theo chính sách RBAC.",
        offending_entity="c_phone",
        suggested_fix="Dùng c_name hoặc c_custkey thay thế.",
        actionable_feedback="Truy vấn vi phạm RBAC do cột c_phone. Hãy thay bằng c_name.",
    )
    mock_structured.invoke.return_value = expected_result
    mock_llm.with_structured_output.return_value = mock_structured

    state: ControlState = {
        "sql": "SELECT c_phone FROM customer",
        "session_id": "sess_diag_struct",
        "schema_context": "Bảng customer",
        "execution_result": {
            "is_valid": False,
            "status": "BLOCKED_RBAC",
            "error_type": "UNAUTHORIZED_COLUMN",
            "error_message": "Cấm truy cập cột c_phone",
            "actionable_feedback": None,
            "diagnostic_result": None,
            "data": None,
            "columns": None,
            "bytes_scanned": 0,
            "execution_time_ms": 0.0,
        },
    }

    update = error_diagnostic_node(state, llm=mock_llm)
    assert update["diagnostic_result"] == expected_result
    assert update["actionable_feedback"] == expected_result.actionable_feedback
    assert update["execution_result"]["diagnostic_result"] == expected_result


def test_error_diagnostic_agent_fallback_no_llm():
    """Kiểm tra cơ chế Fail-Safe của ERROR_DIAGNOSTIC_AGENT khi không có LLM."""
    from src.agents.control_pipeline.diagnostic import error_diagnostic_node

    state: ControlState = {
        "sql": "SELECT * FROM lineitem",
        "session_id": "sess_fallback",
        "execution_result": {
            "is_valid": False,
            "status": "BLOCKED_COST",
            "error_type": "EXCEEDED_COST_LIMIT",
            "error_message": "Ước lượng quét vượt quá ngân sách",
            "actionable_feedback": None,
            "diagnostic_result": None,
            "data": None,
            "columns": None,
            "bytes_scanned": 100000,
            "execution_time_ms": 0.0,
        },
    }

    update = error_diagnostic_node(state, llm=None)
    assert "actionable_feedback" in update
    assert "diagnostic_result" in update
    diag = update["diagnostic_result"]
    assert update["actionable_feedback"] == diag.actionable_feedback


def test_get_control_pipeline_subagent_spec():
    """Kiểm tra cấu hình CompiledSubAgent của Control Pipeline theo chuẩn deepagents."""
    from langchain_core.runnables import Runnable

    from src.agents.control_pipeline import (
        control_pipeline_subagent,
        get_control_pipeline_subagent,
    )

    spec = get_control_pipeline_subagent()
    assert spec["name"] == "control-pipeline"
    assert spec["mode"] == "isolated"
    assert isinstance(spec["runnable"], Runnable)
    assert "Hàng rào kiểm soát" in spec["description"]

    # Kiểm tra singleton instance
    assert control_pipeline_subagent["name"] == "control-pipeline"


def test_control_pipeline_runnable_execution_success(shared_tpch_connector, default_user_context):
    """Kiểm tra thực thi Runnable bọc Control Pipeline với câu lệnh SELECT hợp lệ."""
    from langchain_core.messages import AIMessage

    from src.agents.control_pipeline.builder import (
        build_control_pipeline_graph,
        create_control_pipeline_runnable,
    )

    graph = build_control_pipeline_graph(db_connector=shared_tpch_connector)
    runnable = create_control_pipeline_runnable(graph=graph)

    state = {
        "sql": "SELECT c_custkey, c_name FROM customer LIMIT 2",
        "user_context": default_user_context,
        "session_id": "test_compiled_subagent_sess",
    }

    result = runnable.invoke(state)

    # deepagents bắt buộc kết quả phải có 'messages' chứa AIMessage
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert "THÀNH CÔNG" in result["messages"][0].content

    # Kiểm tra dữ liệu trả về trong state
    assert result["is_valid"] is True
    assert len(result["data"]) == 2
    assert "c_name" in result["columns"]


def test_control_pipeline_runnable_execution_failure_ast(shared_tpch_connector, default_user_context):
    """Kiểm tra thực thi Runnable khi có lỗi vi phạm AST (DROP TABLE)."""
    from langchain_core.messages import AIMessage

    from src.agents.control_pipeline.builder import (
        build_control_pipeline_graph,
        create_control_pipeline_runnable,
    )

    graph = build_control_pipeline_graph(db_connector=shared_tpch_connector)
    runnable = create_control_pipeline_runnable(graph=graph)

    state = {
        "sql": "DROP TABLE customer",
        "user_context": default_user_context,
        "session_id": "test_compiled_subagent_fail",
    }

    result = runnable.invoke(state)

    assert "messages" in result
    assert isinstance(result["messages"][0], AIMessage)
    assert "THẤT BẠI" in result["messages"][0].content
    assert result["is_valid"] is False
    assert result["data"] is None
