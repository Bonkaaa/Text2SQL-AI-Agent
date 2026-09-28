"""Dependency Injection Providers cho FastAPI Gateway (Component 5.1).

Quản lý:
- Phân quyền người dùng RBAC (UserContext) dựa trên Request Headers và Body.
- Kiểm tra vai trò quản trị viên (Admin Guard) bảo vệ các endpoints nhạy cảm.
- Cung cấp singleton DuckDBConnector, AuditLogger và Checkpointer dùng chung.
"""

import logging
import secrets
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.agents.supervisor import get_default_checkpointer
from src.config import get_settings
from src.models.rbac import UserContext, UserRole
from src.utils.audit_logger import get_audit_logger
from src.utils.db_connector import DuckDBConnector
from src.utils.tpcds_seeder import seed_tpcds_data

logger = logging.getLogger(__name__)

_shared_duckdb_connector: DuckDBConnector | None = None


def get_shared_checkpointer() -> BaseCheckpointSaver:
    """Singleton getter cung cấp Checkpointer chung cho toàn bộ ứng dụng."""
    return get_default_checkpointer()


def get_duckdb_connector() -> Generator[DuckDBConnector]:
    """Cung cấp DuckDBConnector kết nối với database TPC-DS (24 bảng).

    Nếu database chưa tồn tại dữ liệu, tự động khởi tạo dữ liệu mẫu TPC-DS.
    """
    global _shared_duckdb_connector
    if _shared_duckdb_connector is None:
        settings = get_settings()
        # Khởi tạo kết nối DuckDB
        conn = seed_tpcds_data(db_path=settings.duckdb_path, scale_factor=0.01)
        _shared_duckdb_connector = DuckDBConnector(connection=conn)

    yield _shared_duckdb_connector


def get_current_user_context(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    x_session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    x_session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> UserContext:
    """Trích xuất ngữ cảnh người dùng UserContext từ Request Headers với bảo vệ Admin Token và Session Token.

    Headers được hỗ trợ:
    - X-User-Id: Định danh người dùng (mặc định: 'anonymous_user').
    - X-User-Role: Vai trò ('Analyst' hoặc 'Admin', mặc định: 'Analyst').
    - X-Session-Id: Định danh phiên làm việc (mặc định: 'default_session').
    - X-Admin-Token: Mã bí mật xác thực quyền Admin nếu được cấu hình server-side.
    - X-Session-Token: Mã bí mật xác thực quyền sở hữu phiên làm việc.

    Returns:
        UserContext: Ngữ cảnh phân quyền RBAC và giới hạn chi phí.
    """
    settings = get_settings()
    user_id = x_user_id or "anonymous_user"
    session_id = x_session_id or "default_session"

    role = UserRole.ANALYST
    if x_user_role:
        normalized_role = x_user_role.strip().lower()
        if normalized_role in ["admin", "administrator"]:
            # Nếu server đã cấu hình admin_api_key, yêu cầu token bí mật để ngăn giả mạo header
            if settings.admin_api_key:
                if x_admin_token and secrets.compare_digest(
                    x_admin_token, settings.admin_api_key
                ):
                    role = UserRole.ADMIN
                else:
                    logger.warning(
                        "Từ chối quyền ADMIN cho user '%s': X-Admin-Token không hợp lệ hoặc thiếu.",
                        user_id,
                    )
                    role = UserRole.ANALYST
            elif settings.app_env != "production":
                # Chế độ dev/testing khi chưa cấu hình admin_api_key
                logger.debug(
                    "Cấp quyền ADMIN trong dev/testing cho user '%s' vì chưa set admin_api_key.",
                    user_id,
                )
                role = UserRole.ADMIN
            else:
                # Tuyệt đối fail-closed trên production khi không có secret
                logger.warning(
                    "Từ chối quyền ADMIN trên production do thiếu admin_api_key.",
                )
                role = UserRole.ANALYST
        elif normalized_role in ["analyst", "data_analyst"]:
            role = UserRole.ANALYST
        elif normalized_role in ["business_user", "business"]:
            role = UserRole.BUSINESS_USER

    return UserContext(
        user_id=user_id,
        session_id=session_id,
        role=role,
        session_token=x_session_token,
    )


def require_admin_role(
    user_context: Annotated[UserContext, Depends(get_current_user_context)],
) -> UserContext:
    """Security Guard: Bắt buộc người dùng phải có vai trò ADMIN đã xác thực.

    Nếu người dùng không phải ADMIN, ném ngoại lệ HTTP 403 Forbidden.
    Tuyệt đối không tự động tạo user admin mặc định nếu context không hợp lệ.
    """
    if user_context.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập bị từ chối. Endpoint này chỉ dành cho vai trò ADMIN đã được xác thực.",
        )

    return user_context


__all__ = [
    "get_audit_logger",
    "get_current_user_context",
    "get_duckdb_connector",
    "get_shared_checkpointer",
    "require_admin_role",
]
