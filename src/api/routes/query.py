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

from src.agents.supervisor import arun_supervisor, extract_message_text
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

    # 3. Định dạng kết quả trả về
    status_str = result.get("status", "COMPLETED")

    # Trích xuất dữ liệu từ result & typed artifacts (Phase 1, 2, 3)
    artifacts = result.get("artifacts") or []
    data = result.get("data")
    columns = result.get("columns")
    recharts_config = result.get("recharts_config")
    sql = result.get("sql")
    final_answer = extract_message_text(result.get("final_answer"))
    response_package = result.get("response_package")
    output_artifacts = result.get("output_artifacts")

    # Ưu tiên lấy SQL, Data, Columns từ Typed QueryArtifacts nếu có
    if artifacts and isinstance(artifacts, list):
        for art in artifacts:
            art_status = getattr(art, "status", None) or (
                art.get("status") if isinstance(art, dict) else None
            )
            if art_status == "SUCCESS":
                if not sql:
                    sql = getattr(art, "sql", None) or (
                        art.get("sql") if isinstance(art, dict) else None
                    )
                if not data:
                    data = getattr(art, "data", None) or (
                        art.get("data") if isinstance(art, dict) else None
                    )
                if not columns:
                    columns = getattr(art, "columns", None) or (
                        art.get("columns") if isinstance(art, dict) else None
                    )
                break

    # Nếu agent hoàn tất mà có messages, trích xuất final_answer từ message cuối
    messages = result.get("messages", [])
    if not final_answer and messages:
        final_answer = extract_message_text(
            getattr(messages[-1], "content", messages[-1])
        )

    # Fallback trích xuất recharts_config từ final_answer nếu chưa có trực tiếp
    if not recharts_config and final_answer:
        import json
        import re

        json_matches = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", final_answer)
        for jm in json_matches:
            try:
                pj = json.loads(jm)
                if isinstance(pj, dict):
                    if "recharts_config" in pj and isinstance(
                        pj["recharts_config"], dict
                    ):
                        recharts_config = pj["recharts_config"]
                        if "chart_type" in pj and "chart_type" not in recharts_config:
                            recharts_config["chart_type"] = pj["chart_type"]
                        break
                    elif "chart_type" in pj or "x_key" in pj:
                        recharts_config = pj
                        break
            except (json.JSONDecodeError, ValueError):
                continue

    # Fallback trích xuất SQL và Data thực tế từ các ToolMessages của control-pipeline nếu cần
    if not sql and messages:
        import re

        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            sql_match = re.search(
                r"-\s*Câu lệnh đã chạy:\s*(SELECT[\s\S]+?)(?:\n-|\Z)",
                c_text,
                re.IGNORECASE,
            )
            if sql_match:
                sql = sql_match.group(1).strip()
                break

    if not data and messages:
        import json
        import re

        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            data_match = re.search(r"-\s*Dữ liệu mẫu thực tế:\s*(\[[\s\S]+?\])", c_text)
            if data_match:
                try:
                    parsed_sample = json.loads(data_match.group(1))
                    if isinstance(parsed_sample, list) and parsed_sample:
                        data = parsed_sample
                        if not columns and isinstance(data[0], dict):
                            columns = list(data[0].keys())
                    break
                except (json.JSONDecodeError, ValueError):
                    pass

    # Kiểm tra trạng thái tạm dừng chờ duyệt HITL từ state hoặc PendingApprovalStore (ISSUE-03)
    from src.agents.control_pipeline.pending_store import get_pending_approval

    pending_app = get_pending_approval(active_session_id)
    requires_hitl = (
        (status_str == "PENDING_APPROVAL")
        or bool(result.get("hitl_required", False))
        or (pending_app is not None)
    )
    estimated_cost_bytes = result.get("estimated_cost_bytes")
    if pending_app:
        status_str = "PENDING_APPROVAL"
        if not estimated_cost_bytes:
            estimated_cost_bytes = pending_app.estimated_bytes
        if not sql:
            sql = pending_app.sql

    if not requires_hitl and messages:
        import re

        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            if (
                "BLOCKED_HITL" in c_text
                or "HITL Required" in c_text
                or "TẠM DỪNG CHỜ PHÊ DUYỆT" in c_text
            ):
                requires_hitl = True
                status_str = "PENDING_APPROVAL"
                cost_m = re.search(r"Dung lượng quét ước tính:\s*(\d+)", c_text)
                if cost_m:
                    estimated_cost_bytes = int(cost_m.group(1))
                sql_m = re.search(
                    r"-\s*Câu lệnh:\s*(SELECT[\s\S]+?)(?:\n-|\Z)", c_text, re.IGNORECASE
                )
                if sql_m and not sql:
                    sql = sql_m.group(1).strip()
                break

    # Serialize ResponsePackage và AnalysisPlan tasks (Phase 3 & 4)
    pkg_dump = None
    if response_package:
        if hasattr(response_package, "model_dump"):
            pkg_dump = response_package.model_dump()
        elif isinstance(response_package, dict):
            pkg_dump = response_package

    if not output_artifacts and pkg_dump and "artifacts" in pkg_dump:
        output_artifacts = pkg_dump["artifacts"]

    plan = result.get("plan")
    tasks_dump = None
    if plan and hasattr(plan, "tasks"):
        tasks_dump = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "status": t.status,
            }
            for t in plan.tasks
        ]
    elif result.get("tasks"):
        tasks_dump = result.get("tasks")

    # An ninh và Hardcoded Refusal (Phase 2.5)
    is_safe = result.get("is_safe", True)
    safety_category = result.get("safety_category")
    refusal_reason = result.get("refusal_reason")
    if status_str == "SECURITY_BLOCKED":
        is_safe = False
        if not final_answer:
            final_answer = refusal_reason

    return QueryResponse(
        session_id=active_session_id,
        session_token=active_session_token,
        status=status_str,
        question=request.question,
        is_safe=is_safe,
        safety_category=safety_category,
        refusal_reason=refusal_reason,
        is_ambiguous=result.get("is_ambiguous", False),
        clarification_question=result.get("clarification_question"),
        suggested_options=result.get("suggested_options", []),
        final_answer=final_answer,
        sql=sql,
        data=data,
        columns=columns,
        recharts_config=recharts_config,
        intent=result.get("intent"),
        tasks=tasks_dump,
        artifacts=artifacts if artifacts else None,
        response_package=pkg_dump,
        output_artifacts=output_artifacts,
        insight=result.get("insight") or final_answer,
        visualization=result.get("visualization") or recharts_config,
        metadata={
            "query_count": len(artifacts) if isinstance(artifacts, list) else 0,
            "execution_time_ms": elapsed_ms,
        },
        requires_hitl=requires_hitl,
        estimated_cost_bytes=estimated_cost_bytes,
        execution_time_ms=elapsed_ms,
        error=result.get("error"),
    )


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
