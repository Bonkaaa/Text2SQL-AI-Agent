"""Router xử lý các yêu cầu truy vấn phân tích dữ liệu (/api/v1/query).

Bao gồm:
- POST /ask: Tiếp nhận câu hỏi, điều phối Deep Agent Supervisor, trả về kết quả hoặc yêu cầu làm rõ / chờ duyệt.
- POST /approve: Tiếp nhận quyết định phê duyệt Human-in-the-loop (HITL).
- GET /history: Truy xuất lịch sử các phiên và tệp artifacts đã sinh.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from langgraph.types import Command

from src.agents.supervisor import arun_supervisor
from src.api.dependencies import (
    get_current_user_context,
    get_shared_checkpointer,
    require_admin_role,
)
from src.config import get_settings
from src.models.api_schemas import (
    ApprovalRequest,
    ApprovalResponse,
    AskQueryRequest,
    QueryHistoryItem,
    QueryHistoryResponse,
    QueryResponse,
)
from src.models.rbac import UserContext, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


def verify_session_ownership(
    session_id: str,
    user_id: str,
    session_token: str | None = None,
    is_admin: bool = False,
) -> str | None:
    """Xác minh quyền sở hữu phiên làm việc trong SQLite bền vững, chống can thiệp chéo phiên."""
    from src.agents.control_pipeline.pending_store import register_or_verify_session

    is_allowed, err_msg, active_token = register_or_verify_session(
        session_id=session_id,
        user_id=user_id,
        session_token=session_token,
        is_admin=is_admin,
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=err_msg,
        )
    return active_token


@router.post(
    "/ask",
    response_model=QueryResponse,
    summary="Gửi câu hỏi phân tích dữ liệu tự nhiên",
    description=(
        "Tiếp nhận câu hỏi ngôn ngữ tự nhiên từ người dùng, gọi Deep Agent Supervisor "
        "bất đồng bộ và trả về bảng số liệu, biểu đồ Recharts hoặc yêu cầu làm rõ."
    ),
)
async def ask_query(
    request: AskQueryRequest,
    response: Response,
    user_context: Annotated[UserContext, Depends(get_current_user_context)],
) -> QueryResponse:
    """Xử lý câu hỏi phân tích kinh doanh qua Deep Agent Supervisor."""
    start_time = time.perf_counter()

    # 1. Xác định Session ID & User Context
    active_session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    # Chống leo quyền (Role Escalation Protection - ISSUE-01):
    # Server-side UserContext từ authentication dependency là căn cứ xác thực duy nhất.
    authenticated_role = user_context.role
    if request.role and request.role != authenticated_role:
        if authenticated_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản vai trò '{authenticated_role.value}' không được phép tự nâng quyền thành '{request.role.value}'.",
            )
        effective_role = request.role
    else:
        effective_role = authenticated_role

    provided_session_token = request.session_token or user_context.session_token

    active_user = UserContext(
        user_id=user_context.user_id
        if user_context.user_id != "anonymous_user"
        else request.user_id,
        session_id=active_session_id,
        role=effective_role,
        session_token=provided_session_token,
    )

    # Ràng buộc quyền sở hữu phiên làm việc (Session Ownership Protection)
    # Xác thực chống giả mạo danh tính qua Session Secret Token (ISSUE-1)
    active_session_token = verify_session_ownership(
        session_id=active_session_id,
        user_id=active_user.user_id,
        session_token=active_user.session_token,
        is_admin=(active_user.role == UserRole.ADMIN),
    )
    if active_session_token:
        active_user.session_token = active_session_token
        response.headers["X-Session-Token"] = active_session_token

    logger.info(
        "Nhận yêu cầu truy vấn session '%s', user '%s' (role: %s): %s",
        active_session_id,
        active_user.user_id,
        active_user.role.value,
        request.question,
    )

    # 2. Gọi Supervisor bất đồng bộ với shared checkpointer để lưu trữ context đa lượt
    result: dict[str, Any] = await arun_supervisor(
        question=request.question,
        user_context=active_user,
        session_id=active_session_id,
        checkpointer=get_shared_checkpointer(),
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # 3. Định dạng kết quả trả về theo chuẩn QueryResponse
    from src.utils.response_assembler import assemble_query_response

    query_response = assemble_query_response(
        result=result,
        question=request.question,
        session_id=active_session_id,
        elapsed_ms=elapsed_ms,
        user_context=active_user,
        session_token=active_session_token,
    )

    tracer = result.get("tracer")
    if tracer:
        tracer.log_artifact(
            "query_response.json", query_response.model_dump(mode="json")
        )

    return query_response


@router.post(
    "/approve",
    response_model=ApprovalResponse,
    summary="Phê duyệt hoặc từ chối câu truy vấn chờ duyệt HITL",
    description="Gửi quyết định tiếp tục hoặc hủy bỏ khi câu truy vấn bị tạm dừng tại interrupt().",
)
async def approve_query(
    request: ApprovalRequest,
    admin_user: Annotated[UserContext, Depends(require_admin_role)],
) -> ApprovalResponse:
    """Xử lý tiếp tục luồng thực thi sau khi nhận quyết định phê duyệt từ người dùng.

    Resume graph đang bị tạm dừng tại hitl_gate_node bằng cách gửi Command(resume=...)
    với key 'hitl_approved' đúng với contract mà hitl_gate_node mong đợi.
    """
    logger.info(
        "Nhận quyết định phê duyệt cho session '%s': approved=%s",
        request.session_id,
        request.approved,
    )

    from src.agents.control_pipeline.pending_store import (
        claim_pending_approval,
        get_pending_approval,
        resolve_pending_approval,
    )
    from src.config import get_settings

    # 1. Tra cứu và xác thực tính nhất quán giữa approval_id và session_id (ISSUE-E)
    target_approval_id = request.approval_id
    if target_approval_id:
        existing = get_pending_approval(approval_id=target_approval_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy yêu cầu phê duyệt với mã '{target_approval_id}'.",
            )
        if existing.session_id != request.session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã phê duyệt '{target_approval_id}' thuộc phiên '{existing.session_id}', không khớp với phiên '{request.session_id}' được gửi.",
            )
    else:
        pending_record = get_pending_approval(
            session_id=request.session_id,
            task_id=request.task_id,
            status="PENDING",
        )
        if not pending_record:
            pending_record = get_pending_approval(
                session_id=request.session_id,
                task_id=request.task_id,
            )
        if pending_record:
            target_approval_id = pending_record.approval_id

    # 2. Xử lý qua SQLite PendingApprovalStore bền vững với Atomic Compare-And-Set (ISSUE-C)
    if target_approval_id:
        claimed, pending, claim_state = claim_pending_approval(
            approval_id=target_approval_id,
            session_id=request.session_id,
        )

        if claim_state == "ALREADY_APPROVED":
            logger.info(
                "Yêu cầu phê duyệt '%s' cho phiên '%s' đã được duyệt trước đó (Idempotent).",
                target_approval_id,
                request.session_id,
            )
            exec_res_data = (pending.execution_result or {}) if pending else {}
            return ApprovalResponse(
                session_id=pending.session_id if pending else request.session_id,
                approval_id=target_approval_id,
                approved=True,
                status="ALREADY_APPROVED",
                message="Truy vấn này đã được phê duyệt và thực thi trước đó (Idempotent).",
                data=exec_res_data.get("data"),
                columns=exec_res_data.get("columns"),
            )

        if claim_state == "ALREADY_REJECTED":
            return ApprovalResponse(
                session_id=pending.session_id if pending else request.session_id,
                approval_id=target_approval_id,
                approved=False,
                status="ALREADY_REJECTED",
                message=f"Truy vấn này đã bị từ chối trước đó. Lý do: {(pending.rejection_reason if pending else None) or 'Quản trị viên từ chối.'}",
            )

        if claim_state == "IN_PROGRESS":
            return ApprovalResponse(
                session_id=pending.session_id if pending else request.session_id,
                approval_id=target_approval_id,
                approved=True,
                status="PROCESSING",
                message="Truy vấn đang trong tiến trình xử lý bởi một worker khác.",
            )

        if claimed and pending is not None:
            official_session_id = pending.session_id

            if request.approved:
                from src.utils.audit_logger import AuditEvent, log_audit_event
                from src.utils.db_connector import get_duckdb_connector

                try:
                    connector = get_duckdb_connector()
                    query_timeout = get_settings().query_timeout_seconds
                    exec_res = connector.execute_query(
                        pending.sql, timeout_seconds=query_timeout
                    )

                    log_audit_event(
                        AuditEvent(
                            session_id=official_session_id,
                            user_id=admin_user.user_id,
                            role=admin_user.role.value,
                            question=pending.reason or pending.sql,
                            sql=pending.sql,
                            status="SUCCESS" if exec_res.success else "DB_ERROR",
                            execution_time_ms=exec_res.execution_time_ms,
                            error_message=exec_res.error_message,
                        )
                    )

                    resolve_pending_approval(
                        session_id=official_session_id,
                        approved=True,
                        task_id=pending.task_id,
                        approval_id=pending.approval_id,
                        execution_result={
                            "data": exec_res.data,
                            "columns": exec_res.columns,
                            "row_count": exec_res.row_count,
                            "execution_time_ms": exec_res.execution_time_ms,
                            "success": exec_res.success,
                            "error_message": exec_res.error_message,
                        },
                    )

                    return ApprovalResponse(
                        session_id=official_session_id,
                        approval_id=pending.approval_id,
                        approved=True,
                        status="SUCCESS" if exec_res.success else "DB_ERROR",
                        message=(
                            f"Đã phê duyệt và thực thi thành công câu truy vấn ({len(exec_res.data or [])} bản ghi)."
                            if exec_res.success
                            else f"Phê duyệt thành công nhưng lỗi DB: {exec_res.error_message}"
                        ),
                        data=exec_res.data,
                        columns=exec_res.columns,
                    )
                except Exception as exc:
                    logger.exception(
                        "Lỗi thực thi truy vấn phê duyệt HITL cho session '%s', approval '%s'",
                        official_session_id,
                        pending.approval_id,
                    )
                    resolve_pending_approval(
                        session_id=official_session_id,
                        approved=False,
                        task_id=pending.task_id,
                        approval_id=pending.approval_id,
                        status="FAILED",
                        rejection_reason=f"Lỗi khi thực thi truy vấn sau phê duyệt: {exc}",
                    )
                    return ApprovalResponse(
                        session_id=official_session_id,
                        approval_id=pending.approval_id,
                        approved=False,
                        status="FAILED",
                        message=f"Lỗi khi thực thi truy vấn sau phê duyệt: {exc}",
                    )
            else:
                from src.utils.audit_logger import AuditEvent, log_audit_event

                log_audit_event(
                    AuditEvent(
                        session_id=official_session_id,
                        user_id=admin_user.user_id,
                        role=admin_user.role.value,
                        question=pending.reason or pending.sql,
                        sql=pending.sql,
                        status="BLOCKED_HITL",
                        error_message=request.rejection_reason
                        or "Từ chối bởi Quản trị viên.",
                    )
                )

                resolve_pending_approval(
                    session_id=official_session_id,
                    approved=False,
                    task_id=pending.task_id,
                    approval_id=pending.approval_id,
                    rejection_reason=request.rejection_reason,
                )

                return ApprovalResponse(
                    session_id=official_session_id,
                    approval_id=pending.approval_id,
                    approved=False,
                    status="REJECTED",
                    message=f"Đã từ chối thực thi truy vấn. Lý do: {request.rejection_reason or 'Quản trị viên từ chối.'}",
                )

    # 2. Fallback kiểm tra LangGraph checkpointer tuple
    # Tạo Command với key 'hitl_approved' đúng contract của hitl_gate_node
    resume_command = Command(
        resume={
            "hitl_approved": request.approved,
            "rejection_reason": request.rejection_reason,
        }
    )

    # Resume graph thực sự bằng cách gọi ainvoke với Command
    checkpointer = get_shared_checkpointer()
    config = {"configurable": {"thread_id": request.session_id}}

    checkpoint_tuple = checkpointer.get_tuple(config)
    if checkpoint_tuple is None:
        logger.info(
            "Không tìm thấy checkpoint đang tạm dừng cho session '%s'. Trả về phản hồi xác nhận.",
            request.session_id,
        )
        if request.approved:
            return ApprovalResponse(
                session_id=request.session_id,
                approved=True,
                status="SUCCESS",
                message="Đã tiếp nhận phê duyệt thành công. Truy vấn được phép thực thi.",
            )
        else:
            return ApprovalResponse(
                session_id=request.session_id,
                approved=False,
                status="REJECTED",
                message=f"Đã từ chối thực thi truy vấn. Lý do: {request.rejection_reason or 'Người dùng từ chối.'}",
            )

    try:
        from src.agents.supervisor import (
            create_text2sql_supervisor,
            extract_message_text,
        )

        agent = create_text2sql_supervisor(checkpointer=checkpointer)
        output_state = await agent.ainvoke(resume_command, config=config)

        if request.approved:
            # Trích xuất kết quả sau khi graph resume thành công
            messages = output_state.get("messages", [])
            final_text = extract_message_text(messages[-1].content) if messages else ""

            return ApprovalResponse(
                session_id=request.session_id,
                approved=True,
                status="SUCCESS",
                message=final_text
                or "Đã tiếp nhận phê duyệt thành công. Truy vấn được phép thực thi.",
            )
        else:
            return ApprovalResponse(
                session_id=request.session_id,
                approved=False,
                status="REJECTED",
                message=f"Đã từ chối thực thi truy vấn. Lý do: {request.rejection_reason or 'Người dùng từ chối.'}",
            )

    except Exception as exc:
        logger.exception(
            "Lỗi khi resume graph sau phê duyệt HITL cho session '%s'",
            request.session_id,
        )
        return ApprovalResponse(
            session_id=request.session_id,
            approved=request.approved,
            status="ERROR",
            message=f"Lỗi khi xử lý phê duyệt: {exc}",
        )


@router.get(
    "/history",
    response_model=QueryHistoryResponse,
    summary="Lấy danh sách lịch sử truy vấn của phiên",
)
async def get_query_history(
    session_id: str = Query(..., description="Mã phiên cần xem lịch sử"),
) -> QueryHistoryResponse:
    """Truy xuất danh sách các tệp artifact và lịch sử thực thi của phiên làm việc."""
    settings = get_settings()
    trace_base_dir = Path(settings.trace_output_dir)

    history_items: list[QueryHistoryItem] = []
    if trace_base_dir.exists():
        # Tìm các thư mục có hậu tố chứa session_id[:8]
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")[:8]
        matched_dirs = [
            d for d in trace_base_dir.iterdir() if d.is_dir() and safe_id in d.name
        ]

        for sdir in matched_dirs:
            artifacts = [f.name for f in sdir.iterdir() if f.is_file()]
            history_items.append(
                QueryHistoryItem(
                    session_id=session_id,
                    timestamp=sdir.name.split("_")[0] if "_" in sdir.name else None,
                    status="LOGGED",
                    artifacts=artifacts,
                )
            )

    return QueryHistoryResponse(
        session_id=session_id,
        history=history_items,
    )
