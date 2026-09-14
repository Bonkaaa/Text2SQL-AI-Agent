"""Router kiểm tra và truy xuất nhật ký kiểm toán hệ thống (/api/v1/audit).

Bảo vệ nghiêm ngặt bằng RBAC: Chỉ vai trò ADMIN mới được phép truy cập.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_audit_logger, require_admin_role
from src.models.api_schemas import AuditLogsResponse
from src.models.rbac import UserContext
from src.utils.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get(
    "/logs",
    response_model=AuditLogsResponse,
    summary="Truy xuất nhật ký kiểm toán hệ thống (Yêu cầu quyền ADMIN)",
    description=(
        "Đọc danh sách các sự kiện kiểm toán JSONL từ AuditLogger. "
        "Bắt buộc người dùng phải có header X-User-Role: Admin, nếu không sẽ bị trả về mã 403 Forbidden."
    ),
)
async def get_audit_logs(
    _: Annotated[UserContext, Depends(require_admin_role)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
    limit: int = Query(default=50, ge=1, le=500, description="Số lượng bản ghi tối đa"),
    offset: int = Query(default=0, ge=0, description="Vị trí bắt đầu"),
    session_id: str | None = Query(default=None, description="Lọc theo mã phiên làm việc"),
) -> AuditLogsResponse:
    """Truy xuất danh sách nhật ký kiểm toán có phân trang."""
    events = audit_logger.get_logs(session_id=session_id, limit=limit + offset)

    # Phân trang
    paged_events = events[offset : offset + limit]
    logs_data = [event.model_dump(mode="json") for event in paged_events]

    return AuditLogsResponse(
        total=len(events),
        limit=limit,
        offset=offset,
        logs=logs_data,
    )
