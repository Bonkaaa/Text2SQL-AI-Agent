import logging
from typing import Any

from langgraph.types import interrupt

from src.agents.control_pipeline.hitl_evaluator import evaluate_query_risk
from src.config import get_settings
from src.models.artifacts import QueryArtifact
from src.models.state import ControlPipelineOutput, ControlState
from src.utils.ast_sanitizer import sanitize_and_validate_sql
from src.utils.audit_logger import AuditEvent, AuditLogger, log_audit_event
from src.utils.db_connector import BaseWarehouseConnector, get_duckdb_connector
from src.utils.rbac_enforcer import enforce_rbac_policy

logger = logging.getLogger(__name__)


def ast_check_node(state: ControlState) -> dict[str, Any]:
    """Kiểm tra cú pháp và an toàn SQL bằng AST Parser (sqlglot)."""
    sql = state.get("sql", "")
    settings = get_settings()

    result = sanitize_and_validate_sql(
        sql=sql,
        default_limit=settings.default_row_limit,
    )

    if not result.is_valid:
        return {
            "ast_valid": False,
            "status": "BLOCKED_AST",
            "error_type": result.error_type or "AST_VALIDATION_ERROR",
            "error_message": result.error_message,
        }

    return {
        "ast_valid": True,
        "sql": result.sanitized_sql,
        "tables_used": result.tables_used,
        "columns_used": result.columns_used,
    }


def rbac_check_node(state: ControlState) -> dict[str, Any]:
    """Kiểm tra quyền hạn truy cập bảng và cột (RBAC) theo UserContext."""
    tables_used = state.get("tables_used", [])
    columns_used = state.get("columns_used", [])
    user_context = state.get("user_context")

    if not user_context:
        return {
            "rbac_valid": False,
            "status": "BLOCKED_RBAC",
            "error_type": "MISSING_USER_CONTEXT",
            "error_message": "Thiếu thông tin ngữ cảnh người dùng (UserContext).",
        }

    result = enforce_rbac_policy(
        tables_used=tables_used,
        columns_used=columns_used,
        user_context=user_context,
    )

    if not result.is_allowed:
        return {
            "rbac_valid": False,
            "status": "BLOCKED_RBAC",
            "error_type": result.error_type or "UNAUTHORIZED_ACCESS",
            "error_message": result.error_message,
        }

    return {"rbac_valid": True}


def cost_guard_node(
    state: ControlState,
    db_connector: BaseWarehouseConnector | None = None,
) -> dict[str, Any]:
    """Ước lượng chi phí quét dữ liệu (EXPLAIN / dry-run) và so với budget."""
    sql = state.get("sql", "")
    user_context = state.get("user_context")
    connector = db_connector or get_duckdb_connector()

    max_budget = (
        user_context.max_cost_bytes
        if user_context
        else get_settings().max_bytes_scanned
    )

    estimate = connector.estimate_query_cost(sql=sql, max_budget_bytes=max_budget)

    if not estimate.is_within_budget:
        return {
            "cost_valid": False,
            "estimated_bytes": estimate.estimated_bytes,
            "status": "BLOCKED_COST",
            "error_type": "EXCEEDED_COST_LIMIT",
            "error_message": estimate.explanation
            or "Chi phí quét dữ liệu của truy vấn vượt quá ngân sách cho phép.",
        }

    # Đánh giá rủi ro truy vấn đa tiêu chí cho enterprise database
    is_hitl, hitl_reason, _ = evaluate_query_risk(
        sql=sql,
        estimate=estimate,
        tables_used=state.get("tables_used", []),
        user_context=user_context,
    )

    return {
        "cost_valid": True,
        "estimated_bytes": estimate.estimated_bytes,
        "hitl_required": is_hitl or state.get("hitl_required", False),
        "hitl_reason": hitl_reason if is_hitl else None,
    }


def hitl_gate_node(state: ControlState) -> dict[str, Any]:
    """Chốt chặn Human-in-the-loop tạm dừng graph qua interrupt() chờ duyệt."""
    # Nếu không yêu cầu HITL hoặc đã được phê duyệt từ trước
    if not state.get("hitl_required", False):
        return {"hitl_approved": True}

    if state.get("hitl_approved") is True:
        return {"hitl_approved": True}

    # Kích hoạt tạm dừng phiên chờ người dùng phản hồi
    interrupt_payload = {
        "sql": state.get("sql", ""),
        "estimated_bytes": state.get("estimated_bytes", 0),
        "tables_used": state.get("tables_used", []),
        "session_id": state.get("session_id", ""),
        "hitl_reason": state.get("hitl_reason"),
    }

    decision = interrupt(interrupt_payload)

    # Phân tích phản hồi sau khi resume
    is_approved = False
    if isinstance(decision, dict):
        is_approved = bool(decision.get("hitl_approved", False))
    elif isinstance(decision, bool):
        is_approved = decision

    if not is_approved:
        return {
            "hitl_approved": False,
            "status": "BLOCKED_HITL",
            "error_type": "HITL_REJECTED",
            "error_message": "Truy vấn bị từ chối bởi người dùng qua phê duyệt HITL.",
        }

    return {"hitl_approved": True}


def execute_node(
    state: ControlState,
    db_connector: BaseWarehouseConnector | None = None,
) -> dict[str, Any]:
    """Thực thi câu truy vấn an toàn trên database với timeout."""
    sql = state.get("sql", "")
    connector = db_connector or get_duckdb_connector()
    timeout = get_settings().query_timeout_seconds

    result = connector.execute_query(sql=sql, timeout_seconds=timeout)

    if not result.success:
        err_msg = result.error_message or "Lỗi không xác định khi thực thi trên DB."
        is_timeout = "thời gian tối đa" in err_msg or "timeout" in err_msg.lower()

        status = "TIMEOUT" if is_timeout else "DB_ERROR"
        error_type = "TIMEOUT" if is_timeout else "RUNTIME_ERROR"

        return {
            "status": status,
            "error_type": error_type,
            "error_message": err_msg,
            "execution_time_ms": result.execution_time_ms,
        }

    output: ControlPipelineOutput = {
        "is_valid": True,
        "status": "SUCCESS",
        "error_type": None,
        "error_message": None,
        "actionable_feedback": None,
        "diagnostic_result": None,
        "data": result.data,
        "columns": result.columns,
        "bytes_scanned": state.get("estimated_bytes", 0),
        "execution_time_ms": result.execution_time_ms,
        "hitl_required": state.get("hitl_required", False),
        "hitl_reason": state.get("hitl_reason"),
    }

    artifact = QueryArtifact(
        sql=sql,
        status="SUCCESS",
        data=result.data or [],
        columns=result.columns or [],
        row_count=len(result.data) if result.data else 0,
        execution_time_ms=result.execution_time_ms,
        tables_used=state.get("tables_used", []),
        columns_used=state.get("columns_used", []),
    )

    return {
        "execution_result": output,
        "is_valid": True,
        "data": result.data,
        "columns": result.columns,
        "query_artifact": artifact,
    }


def err_node(state: ControlState) -> dict[str, Any]:
    """Đóng gói trạng thái lỗi chuẩn hóa ControlPipelineOutput."""
    output: ControlPipelineOutput = {
        "is_valid": False,
        "status": state.get("status", "DB_ERROR"),
        "error_type": state.get("error_type", "UNKNOWN_ERROR"),
        "error_message": state.get("error_message", "Đã xảy ra lỗi kiểm duyệt."),
        "actionable_feedback": state.get("actionable_feedback"),
        "diagnostic_result": state.get("diagnostic_result"),
        "data": None,
        "columns": None,
        "bytes_scanned": state.get("estimated_bytes", 0),
        "execution_time_ms": state.get("execution_time_ms", 0.0),
        "hitl_required": state.get("hitl_required", False),
        "hitl_reason": state.get("hitl_reason"),
    }

    status_val = state.get("status")
    error_type = state.get("error_type", "")
    if status_val in ("BLOCKED_AST", "BLOCKED_RBAC", "BLOCKED_COST", "BLOCKED_HITL", "TIMEOUT"):
        art_status = status_val
    elif "AST" in error_type:
        art_status = "BLOCKED_AST"
    elif "RBAC" in error_type:
        art_status = "BLOCKED_RBAC"
    elif "COST" in error_type:
        art_status = "BLOCKED_COST"
    elif "HITL" in error_type:
        art_status = "BLOCKED_HITL"
    elif "TIMEOUT" in error_type:
        art_status = "TIMEOUT"
    else:
        art_status = "DB_ERROR"

    artifact = QueryArtifact(
        sql=state.get("sql", ""),
        status=art_status,
        data=[],
        columns=[],
        row_count=0,
        execution_time_ms=state.get("execution_time_ms", 0.0),
        error_message=state.get("error_message", "Đã xảy ra lỗi kiểm duyệt."),
    )

    return {
        "execution_result": output,
        "is_valid": False,
        "query_artifact": artifact,
    }



def audit_node(
    state: ControlState,
    audit_logger: AuditLogger | None = None,
) -> dict[str, Any]:
    """Ghi nhận vết kiểm toán mọi truy vấn (thành công hoặc thất bại) - Fail-Safe."""
    result = state.get("execution_result")
    user_context = state.get("user_context")

    status = (
        result.get("status", "DB_ERROR") if result else state.get("status", "DB_ERROR")
    )
    error_msg = result.get("error_message") if result else state.get("error_message")

    event = AuditEvent(
        session_id=state.get("session_id", "anonymous"),
        user_id=user_context.user_id if user_context else "unknown",
        role=user_context.role.value if user_context else "Analyst",
        question=state.get("sql", ""),
        sql=state.get("sql", ""),
        status=status,
        bytes_scanned=result.get("bytes_scanned", 0) if result else 0,
        execution_time_ms=result.get("execution_time_ms", 0.0) if result else 0.0,
        error_message=error_msg,
    )

    if audit_logger:
        audit_logger.log_event(event)
    else:
        log_audit_event(event)

    return {}
