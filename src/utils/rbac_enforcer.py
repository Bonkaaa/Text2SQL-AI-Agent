from pydantic import BaseModel, Field

from src.models.rbac import UserContext, get_role_permissions


class RBACCheckResult(BaseModel):
    """Kết quả kiểm tra quyền hạn truy cập dữ liệu (RBAC)."""

    is_allowed: bool = Field(
        description="True nếu người dùng có đủ quyền truy cập toàn bộ bảng và cột"
    )
    violating_tables: list[str] = Field(
        default_factory=list,
        description="Danh sách các bảng người dùng không có quyền truy cập",
    )
    violating_columns: list[str] = Field(
        default_factory=list,
        description="Danh sách các cột dữ liệu nhạy cảm người dùng bị cấm truy cập",
    )
    error_type: str | None = Field(
        default=None, description="Mã phân loại lỗi RBAC (nếu có)"
    )
    error_message: str | None = Field(
        default=None,
        description="Thông báo lỗi chi tiết giải thích lý do bị từ chối quyền",
    )


def enforce_rbac_policy(
    tables_used: list[str],
    columns_used: list[str],
    user_context: UserContext,
) -> RBACCheckResult:
    """Đối chiếu danh sách bảng và cột trích xuất từ AST với quyền hạn của người dùng.

    Args:
        tables_used: Danh sách bảng xuất hiện trong câu query.
        columns_used: Danh sách cột xuất hiện trong câu query.
        user_context: Ngữ cảnh người dùng (chứa role, user_id, session_id).

    Returns:
        RBACCheckResult: Kết quả phê duyệt quyền hạn hoặc danh sách vi phạm.
    """
    # Sử dụng quyền hạn từ user_context (hoặc fallback role permissions)
    allowed_tables = (
        user_context.allowed_tables
        if user_context.allowed_tables
        else get_role_permissions(user_context.role)[0]
    )
    denied_columns = user_context.denied_columns

    # 1. Kiểm tra các bảng không nằm trong danh sách được phép
    violating_tables = sorted(
        [tbl for tbl in tables_used if tbl.lower() not in allowed_tables]
    )

    # 2. Kiểm tra các cột nằm trong danh sách bị cấm
    violating_columns = sorted(
        [col for col in columns_used if col.lower() in denied_columns]
    )

    # Nếu không có vi phạm nào
    if not violating_tables and not violating_columns:
        return RBACCheckResult(
            is_allowed=True,
            violating_tables=[],
            violating_columns=[],
            error_type=None,
            error_message=None,
        )

    # Nếu có vi phạm, xác định mã lỗi và thông báo chi tiết
    error_reasons: list[str] = []
    error_type = "UNAUTHORIZED_ACCESS"

    if violating_tables and violating_columns:
        error_type = "UNAUTHORIZED_ACCESS"
        error_reasons.append(
            f"Vai trò '{user_context.role.value}' không được phép truy cập bảng: {violating_tables}."
        )
        error_reasons.append(
            f"Đồng thời bị cấm truy cập các cột thông tin nhạy cảm: {violating_columns}."
        )
    elif violating_tables:
        error_type = "UNAUTHORIZED_TABLE"
        error_reasons.append(
            f"Vai trò '{user_context.role.value}' không được phép truy cập bảng: {violating_tables}."
        )
    elif violating_columns:
        error_type = "UNAUTHORIZED_COLUMN"
        error_reasons.append(
            f"Vai trò '{user_context.role.value}' không được phép truy vấn các cột thông tin nhạy cảm: {violating_columns}."
        )

    return RBACCheckResult(
        is_allowed=False,
        violating_tables=violating_tables,
        violating_columns=violating_columns,
        error_type=error_type,
        error_message=" ".join(error_reasons),
    )
