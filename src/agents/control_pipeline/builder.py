import json
import re
from typing import Any

from deepagents.middleware.subagents import CompiledSubAgent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda
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
from src.models.rbac import UserContext, UserRole
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
        "hitl_required": input_data.get("hitl_required", False),
        "hitl_approved": input_data.get("hitl_approved"),
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


def extract_sql_from_text(raw_text: str) -> str:
    """Trích xuất câu lệnh SQL thuần túy từ văn bản tự nhiên, Markdown hoặc JSON.

    Xử lý các tình huống:
    1. JSON object chứa key 'sql' hoặc 'query' (ví dụ tool output: {"sql": "SELECT ..."})
    2. Markdown codeblock: ```sql ... ``` hoặc ``` ... ```
    3. Văn bản tự nhiên có kèm SQL (ví dụ: 'Kiểm duyệt cú pháp AST: SELECT COUNT(*) FROM customer')
    4. Câu SQL thuần túy: SELECT ... hoặc WITH ...
    """
    if not raw_text or not isinstance(raw_text, str):
        return ""

    text = raw_text.strip()

    # 1. Thử parse JSON nếu chuỗi bắt đầu bằng '{'
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                for key in ("sql", "query", "sql_query"):
                    if key in data and isinstance(data[key], str):
                        return data[key].strip()
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. Trích xuất từ Markdown Code Block ```sql ... ```
    code_block_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if code_block_match:
        extracted = code_block_match.group(1).strip()
        if extracted:
            return extracted

    # 3. Dùng Regex tìm mệnh đề SQL hợp lệ bắt đầu bằng SELECT hoặc WITH
    sql_pattern = re.compile(
        r"\b(SELECT\s+[\s\S]+?|WITH\s+[\s\S]+?)(?:;|\Z)",
        re.IGNORECASE,
    )
    match = sql_pattern.search(text)
    if match:
        extracted = match.group(1).strip()
        if (extracted.startswith('"') and extracted.endswith('"')) or (
            extracted.startswith("'") and extracted.endswith("'")
        ):
            extracted = extracted[1:-1].strip()
        return extracted

    return text


def create_control_pipeline_runnable(
    graph: CompiledStateGraph | None = None,
) -> Runnable:
    """Tạo Runnable bọc Control Pipeline tương thích với deepagents CompiledSubAgent.

    deepagents yêu cầu SubAgent trả về state có chứa trường 'messages' để trích xuất nội dung
    gửi ngược lại cho parent agent dưới dạng ToolMessage.
    """
    active_graph = graph or build_control_pipeline_graph()

    def _sync_runner(state: dict[str, Any]) -> dict[str, Any]:
        # 1. Trích xuất câu lệnh SQL từ state hoặc từ messages
        raw_sql = state.get("sql")
        if not raw_sql:
            messages = state.get("messages", [])
            for msg in reversed(messages):
                content = getattr(msg, "content", "")
                if content:
                    raw_sql = str(content)
                    break

        sql = extract_sql_from_text(raw_sql or "")

        user_context = state.get("user_context")
        session_id = state.get("session_id", "default_session")

        # Phòng thủ chiều sâu (Defense-in-Depth):
        # Nếu state chưa có user_context, tự động gán vai trò quyền hạn tối thiểu (Analyst)
        if not user_context:
            user_context = UserContext(
                user_id="default_analyst",
                session_id=session_id,
                role=UserRole.ANALYST,
            )

        input_data: ControlPipelineInput = {
            "sql": sql or "",
            "user_context": user_context,
            "session_id": session_id,
        }

        output = run_control_pipeline(active_graph, input_data)

        # 2. Định dạng thông điệp tóm tắt gửi về cho Supervisor
        if output.get("is_valid", False):
            data = output.get("data") or []
            data_sample = data[:10]
            summary = (
                f"Truy vấn SQL thực thi THÀNH CÔNG trên database ({output.get('execution_time_ms', 0):.2f}ms).\n"
                f"- Câu lệnh đã chạy: {sql}\n"
                f"- Số lượng bản ghi: {len(data)}\n"
                f"- Dữ liệu mẫu thực tế: {json.dumps(data_sample, ensure_ascii=False, default=str)}"
            )
        elif output.get("status") == "BLOCKED_HITL":
            summary = (
                f"Truy vấn SQL TẠM DỪNG CHỜ PHÊ DUYỆT (HITL Required) [BLOCKED_HITL].\n"
                f"- Câu lệnh: {sql}\n"
                f"- Dung lượng quét ước tính: {output.get('bytes_scanned', 0)} bytes\n"
                f"- Lý do rủi ro: {output.get('hitl_reason') or output.get('error_message')}"
            )
        else:
            summary = (
                f"Truy vấn SQL THẤT BẠI [{output.get('error_type', 'ERROR')}]: {output.get('error_message')}.\n"
                f"- Câu lệnh bị lỗi: {sql}\n"
                f"- Actionable Feedback: {output.get('actionable_feedback')}"
            )

        return {
            **state,
            "messages": [AIMessage(content=summary)],
            "execution_result": output,
            "is_valid": output.get("is_valid", False),
            "data": output.get("data"),
            "columns": output.get("columns"),
            "status": output.get("status"),
            "executed_sql": sql,
            "hitl_required": output.get("hitl_required", False),
            "hitl_reason": output.get("hitl_reason"),
            "estimated_bytes": output.get("bytes_scanned", 0),
        }

    return RunnableLambda(_sync_runner)


def get_control_pipeline_subagent(
    graph: CompiledStateGraph | None = None,
) -> CompiledSubAgent:
    """Tạo cấu hình CompiledSubAgent cho Control Pipeline theo chuẩn deepagents.

    Đóng gói StateGraph tất định Phase 1 thành một CompiledSubAgent mà Deep Agent
    có thể gọi qua công cụ task('control-pipeline', ...).
    """
    runnable = create_control_pipeline_runnable(graph=graph)
    return {
        "name": "control-pipeline",
        "description": (
            "Hàng rào kiểm soát tất định (CompiledSubAgent) thực thi kiểm tra cú pháp AST (sqlglot), "
            "chính sách phân quyền RBAC, dự toán chi phí Cost guard, Human-in-the-loop (HITL) "
            "và thực thi truy vấn an toàn trên Data Warehouse."
        ),
        "runnable": runnable,
        "mode": "isolated",
    }


control_pipeline_subagent: CompiledSubAgent = get_control_pipeline_subagent()
