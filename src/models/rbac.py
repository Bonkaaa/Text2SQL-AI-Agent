from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """Phân quyền người dùng trong hệ thống Analytics."""

    ANALYST = "Analyst"
    ADMIN = "Admin"


# Ma trận bảng được phép truy cập theo Role
DEFAULT_ALLOWED_TABLES: dict[UserRole, set[str]] = {
    UserRole.ANALYST: {
        "customer",
        "orders",
        "lineitem",
        "part",
        "partsupp",
        "supplier",
        "nation",
        "region",
    },
    UserRole.ADMIN: {
        "customer",
        "orders",
        "lineitem",
        "part",
        "partsupp",
        "supplier",
        "nation",
        "region",
        "audit_log",
    },
}

# Ma trận các cột nhạy cảm bị CẤM (PII / Tài chính cá nhân)
DEFAULT_DENIED_COLUMNS: dict[UserRole, set[str]] = {
    UserRole.ANALYST: {
        "c_phone",  # PII: Số điện thoại khách hàng
        "c_acctbal",  # Tài chính: Số dư tài khoản khách hàng
        "s_phone",  # PII: Số điện thoại nhà cung cấp
        "s_acctbal",  # Tài chính: Số dư tài khoản nhà cung cấp
    },
    UserRole.ADMIN: set(),  # Admin toàn quyền
}


def get_role_permissions(role: UserRole) -> tuple[set[str], set[str]]:
    """Lấy danh sách (bảng_cho_phép, cột_bị_cấm) tương ứng với vai trò."""
    allowed_tables = DEFAULT_ALLOWED_TABLES.get(role, set()).copy()
    denied_columns = DEFAULT_DENIED_COLUMNS.get(role, set()).copy()
    return allowed_tables, denied_columns


class UserContext(BaseModel):
    """Ngữ cảnh định danh và quyền hạn của người dùng trong phiên làm việc."""

    user_id: str = Field(description="ID người dùng")
    session_id: str = Field(description="ID phiên làm việc (thread_id)")
    role: UserRole = Field(default=UserRole.ANALYST, description="Vai trò người dùng")
    allowed_tables: set[str] = Field(
        default_factory=set,
        description="Tập hợp các bảng được phép truy cập",
    )
    denied_columns: set[str] = Field(
        default_factory=set,
        description="Tập hợp các cột bị cấm truy cập",
    )
    max_cost_bytes: int = Field(
        default=1073741824,
        gt=0,
        description="Ngưỡng dung lượng quét tối đa cho phép (mặc định 1GB)",
    )

    def model_post_init(self, context: object) -> None:
        """Tự động thiết lập quyền hạn bảng và cột mặc định theo role nếu chưa được chỉ định."""
        super().model_post_init(context)
        default_allowed, default_denied = get_role_permissions(self.role)
        if not self.allowed_tables:
            self.allowed_tables = default_allowed
        if not self.denied_columns and self.role != UserRole.ADMIN:
            self.denied_columns = default_denied
