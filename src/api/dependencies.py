"""Dependency Injection Providers cho FastAPI Gateway (Component 5.1).

Quản lý:
- Phân quyền người dùng RBAC (UserContext) dựa trên Request Headers và Body.
- Kiểm tra vai trò quản trị viên (Admin Guard) bảo vệ các endpoints nhạy cảm.
- Cung cấp singleton DuckDBConnector, AuditLogger và Checkpointer dùng chung.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Header, HTTPException, status
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from src.config import get_settings
from src.models.rbac import UserContext, UserRole
from src.utils.audit_logger import get_audit_logger
from src.utils.db_connector import DuckDBConnector
from src.utils.tpch_seeder import seed_tpch_data

# Singleton checkpointer lưu trạng thái đồ thị và interrupt qua các lượt request
_shared_checkpointer: MemorySaver = MemorySaver()
_shared_duckdb_connector: DuckDBConnector | None = None


def get_shared_checkpointer() -> BaseCheckpointSaver:
    """Singleton getter cung cấp Checkpointer chung cho toàn bộ ứng dụng."""
    return _shared_checkpointer


def get_duckdb_connector() -> Generator[DuckDBConnector]:
    """Cung cấp DuckDBConnector kết nối với database TPC-H.

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
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    x_session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
) -> UserContext:
    """Trích xuất ngữ cảnh người dùng UserContext từ Request Headers.

    Headers được hỗ trợ:
    - X-User-Id: Định danh người dùng (mặc định: 'anonymous_user').
    - X-User-Role: Vai trò ('Analyst' hoặc 'Admin', mặc định: 'Analyst').
    - X-Session-Id: Định danh phiên làm việc (mặc định: 'default_session').

    Returns:
        UserContext: Ngữ cảnh phân quyền RBAC và giới hạn chi phí.
    """
    user_id = x_user_id or "anonymous_user"
    session_id = x_session_id or "default_session"

    role = UserRole.ANALYST
    if x_user_role:
        normalized_role = x_user_role.strip().lower()
        if normalized_role in ["admin", "administrator"]:
            role = UserRole.ADMIN
        elif normalized_role in ["analyst", "data_analyst"]:
            role = UserRole.ANALYST
        elif normalized_role in ["business_user", "business"]:
            role = UserRole.BUSINESS_USER

    return UserContext(
        user_id=user_id,
        session_id=session_id,
        role=role,
    )


def require_admin_role(
    user_context: Annotated[UserContext, Header()] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> UserContext:
    """Security Guard: Bắt buộc người dùng phải có vai trò ADMIN.

    Nếu người dùng không phải ADMIN, ném ngoại lệ HTTP 403 Forbidden.
    """
    # Ưu tiên kiểm tra trực tiếp qua header X-User-Role
    role_str = (x_user_role or (user_context.role.value if user_context else "")).strip().lower()
    if role_str not in ["admin", "administrator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập bị từ chối. Endpoint này chỉ dành cho vai trò ADMIN.",
        )

    if user_context is not None:
        user_context.role = UserRole.ADMIN
        return user_context

    return UserContext(
        user_id="admin_user",
        session_id="admin_session",
        role=UserRole.ADMIN,
    )


__all__ = [
    "get_audit_logger",
    "get_current_user_context",
    "get_duckdb_connector",
    "get_shared_checkpointer",
    "require_admin_role",
]
