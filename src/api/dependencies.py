"""Dependency Injection Providers cho FastAPI Gateway (Component 5.1).

Quản lý:
- Phân quyền người dùng RBAC (UserContext) dựa trên JWT Bearer Token hoặc Request Headers.
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
from src.services.auth_service import decode_access_token
from src.utils.audit_logger import get_audit_logger
from src.utils.db_connector import DuckDBConnector
from src.utils.tpch_seeder import seed_tpch_data

logger = logging.getLogger(__name__)

_shared_duckdb_connector: DuckDBConnector | None = None


def get_shared_checkpointer() -> BaseCheckpointSaver:
    """Singleton getter cung cấp Checkpointer chung cho toàn bộ ứng dụng."""
    return get_default_checkpointer()


def get_duckdb_connector() -> Generator[DuckDBConnector]:
    """Cung cấp DuckDBConnector kết nối với database TPC-H (8 bảng).

    Nếu database chưa tồn tại dữ liệu, tự động khởi tạo dữ liệu mẫu TPC-H.
    """
    global _shared_duckdb_connector
    if _shared_duckdb_connector is None:
        settings = get_settings()
        # Khởi tạo kết nối DuckDB
        conn = seed_tpch_data(db_path=settings.duckdb_path, scale_factor=0.01)
        _shared_duckdb_connector = DuckDBConnector(connection=conn)

    yield _shared_duckdb_connector


def get_current_user_context(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    x_session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
    x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    x_session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
) -> UserContext:
    """Trích xuất ngữ cảnh người dùng UserContext từ JWT Bearer Token hoặc Request Headers.

    Ưu tiên:
    1. Authorization: Bearer <token> (JWT giải mã trích xuất user_id và role).
    2. Fallback sang Headers (X-User-Id, X-User-Role, X-Admin-Token).

    Returns:
        UserContext: Ngữ cảnh phân quyền RBAC và giới hạn chi phí.
    """
    settings = get_settings()
    session_id = x_session_id or "default_session"

    # 1. Kiểm tra JWT Bearer Token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        payload = decode_access_token(token)
        if payload is not None:
            jwt_user_id = payload.get("sub") or "authenticated_user"
            raw_role = str(payload.get("role") or "").strip().lower()

            if raw_role in ["admin", "administrator"]:
                role = UserRole.ADMIN
            elif raw_role in ["business_user", "business"]:
                role = UserRole.BUSINESS_USER
            else:
                role = UserRole.ANALYST

            return UserContext(
                user_id=jwt_user_id,
                session_id=session_id,
                role=role,
                session_token=x_session_token,
            )
        else:
            logger.warning("Token Bearer không hợp lệ hoặc đã hết hạn.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Xác thực thất bại: Access Token không hợp lệ hoặc đã hết hạn.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 2. Fallback sang Custom Headers (Legacy / Testing mode)
    user_id = x_user_id or "anonymous_user"
    role = UserRole.ANALYST

    if x_user_role:
        normalized_role = x_user_role.strip().lower()
        if normalized_role in ["admin", "administrator"]:
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
                role = UserRole.ADMIN
            else:
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
