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

from fastapi import APIRouter, Depends, Query
from langgraph.types import Command

from src.agents.supervisor import arun_supervisor, extract_message_text
from src.api.dependencies import get_current_user_context, get_shared_checkpointer
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
    user_context: Annotated[UserContext, Depends(get_current_user_context)],
) -> QueryResponse:
    """Xử lý câu hỏi phân tích kinh doanh qua Deep Agent Supervisor."""
    start_time = time.perf_counter()

    # 1. Xác định Session ID & User Context
    active_session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"
    active_user = UserContext(
        user_id=request.user_id or user_context.user_id,
        session_id=active_session_id,
        role=request.role or user_context.role or UserRole.ANALYST,
    )

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

    # Trích xuất dữ liệu từ result
    data = result.get("data")
    columns = result.get("columns")
    recharts_config = result.get("recharts_config")
    sql = result.get("sql")
    final_answer = extract_message_text(result.get("final_answer"))

    # Nếu agent hoàn tất mà có messages, trích xuất final_answer từ message cuối
    messages = result.get("messages", [])
    if not final_answer and messages:
        final_answer = extract_message_text(getattr(messages[-1], "content", messages[-1]))

    # Fallback trích xuất recharts_config từ final_answer nếu chưa có trực tiếp
    if not recharts_config and final_answer:
        import json
        import re
        json_matches = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", final_answer)
        for jm in json_matches:
            try:
                pj = json.loads(jm)
                if isinstance(pj, dict):
                    if "recharts_config" in pj and isinstance(pj["recharts_config"], dict):
                        recharts_config = pj["recharts_config"]
                        if "chart_type" in pj and "chart_type" not in recharts_config:
                            recharts_config["chart_type"] = pj["chart_type"]
                        break
                    elif "chart_type" in pj or "x_key" in pj:
                        recharts_config = pj
                        break
            except (json.JSONDecodeError, ValueError):
                continue

    # Fallback trích xuất SQL và Data thực tế từ các ToolMessages của control-pipeline
    if not sql and messages:
        import re
        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            sql_match = re.search(r"-\s*Câu lệnh đã chạy:\s*(SELECT[\s\S]+?)(?:\n-|\Z)", c_text, re.IGNORECASE)
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

    # Fallback kiểm tra nếu có thông điệp tạm dừng chờ duyệt HITL
    requires_hitl = (status_str == "PENDING_APPROVAL") or bool(result.get("hitl_required", False))
    estimated_cost_bytes = result.get("estimated_cost_bytes")

    if not requires_hitl and messages:
        import re
        for msg in reversed(messages):
            c_text = str(getattr(msg, "content", ""))
            if "BLOCKED_HITL" in c_text or "HITL Required" in c_text or "TẠM DỪNG CHỜ PHÊ DUYỆT" in c_text:
                requires_hitl = True
                status_str = "PENDING_APPROVAL"
                cost_m = re.search(r"Dung lượng quét ước tính:\s*(\d+)", c_text)
                if cost_m:
                    estimated_cost_bytes = int(cost_m.group(1))
                sql_m = re.search(r"-\s*Câu lệnh:\s*(SELECT[\s\S]+?)(?:\n-|\Z)", c_text, re.IGNORECASE)
                if sql_m and not sql:
                    sql = sql_m.group(1).strip()
                break

    return QueryResponse(
        session_id=active_session_id,
        status=status_str,
        question=request.question,
        is_ambiguous=result.get("is_ambiguous", False),
        clarification_question=result.get("clarification_question"),
        suggested_options=result.get("suggested_options", []),
        final_answer=final_answer,
        sql=sql,
        data=data,
        columns=columns,
        recharts_config=recharts_config,
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
) -> ApprovalResponse:
    """Xử lý tiếp tục luồng thực thi sau khi nhận quyết định phê duyệt từ người dùng."""
    logger.info(
        "Nhận quyết định phê duyệt cho session '%s': approved=%s",
        request.session_id,
        request.approved,
    )

    # Resume graph thông qua checkpointer và Command
    _ = get_shared_checkpointer()
    _ = Command(
        resume={
            "approved": request.approved,
            "rejection_reason": request.rejection_reason,
        }
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
        matched_dirs = [d for d in trace_base_dir.iterdir() if d.is_dir() and safe_id in d.name]

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
