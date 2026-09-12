from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.control_pipeline.diagnostic import error_diagnostic_node
from src.agents.control_pipeline.nodes import (
    ast_check_node,
    audit_node,
    cost_guard_node,
    err_node,
    execute_node,
    hitl_gate_node,
    rbac_check_node,
)
from src.agents.control_pipeline.routers import (
    route_after_ast,
    route_after_cost,
    route_after_execute,
    route_after_hitl,
    route_after_rbac,
)
from src.models.state import ControlPipelineInput, ControlPipelineOutput, ControlState
from src.utils.audit_logger import AuditLogger
from src.utils.db_connector import BaseWarehouseConnector


def build_control_pipeline_graph(
    db_connector: BaseWarehouseConnector | None = None,
    audit_logger: AuditLogger | None = None,
    diagnostic_llm: BaseChatModel | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Xây dựng và compile đồ thị con LangGraph Control & Diagnostic Pipeline (v3.0)."""
    builder = StateGraph(ControlState)

    # 1. Đăng ký các Nodes
    builder.add_node("ast_check", ast_check_node)
    builder.add_node("rbac_check", rbac_check_node)
    builder.add_node(
        "cost_guard",
        lambda state: cost_guard_node(state, db_connector=db_connector),
    )
    builder.add_node("hitl_gate", hitl_gate_node)
    builder.add_node(
        "execute",
        lambda state: execute_node(state, db_connector=db_connector),
    )
    builder.add_node("err_node", err_node)
    builder.add_node(
        "diagnostic",
        lambda state: error_diagnostic_node(state, llm=diagnostic_llm),
    )
    builder.add_node(
        "audit",
        lambda state: audit_node(state, audit_logger=audit_logger),
    )

    # 2. Thiết lập các Cạnh (Edges) và Rẽ nhánh có điều kiện (Conditional Edges)
    builder.add_edge(START, "ast_check")
    builder.add_conditional_edges("ast_check", route_after_ast)
    builder.add_conditional_edges("rbac_check", route_after_rbac)
    builder.add_conditional_edges("cost_guard", route_after_cost)
    builder.add_conditional_edges("hitl_gate", route_after_hitl)
    builder.add_conditional_edges("execute", route_after_execute)

    # Nhánh xử lý lỗi: ERR -> DIAGNOSTIC (Agentic LLM) -> AUDIT
    builder.add_edge("err_node", "diagnostic")
    builder.add_edge("diagnostic", "audit")

    # Nhánh kết thúc: Sau khi ghi log Audit -> END
    builder.add_edge("audit", END)

    # 3. Compile thành Runnable Graph
    return builder.compile(checkpointer=checkpointer)


def run_control_pipeline(
    graph: CompiledStateGraph,
    input_data: ControlPipelineInput,
    thread_id: str | None = None,
) -> ControlPipelineOutput:
    """Hàm tiện ích chạy toàn bộ pipeline kiểm duyệt và trả về ControlPipelineOutput."""
    session_id = input_data.get("session_id", "default_session")
    thread = thread_id or session_id
    config = {"configurable": {"thread_id": thread}}

    initial_state: dict[str, Any] = {
        "sql": input_data["sql"],
        "user_context": input_data["user_context"],
        "session_id": session_id,
        "hitl_required": False,
        "hitl_approved": None,
    }

    final_state = graph.invoke(initial_state, config=config)
    execution_result = final_state.get("execution_result")

    if execution_result:
        return execution_result

    # Trường hợp dự phòng nếu graph kết thúc bất thường
    return {
        "is_valid": False,
        "status": "DB_ERROR",
        "error_type": "UNKNOWN_ERROR",
        "error_message": "Không thể lấy kết quả thực thi từ Control Pipeline.",
        "actionable_feedback": None,
        "diagnostic_result": None,
        "data": None,
        "columns": None,
        "bytes_scanned": 0,
        "execution_time_ms": 0.0,
    }
