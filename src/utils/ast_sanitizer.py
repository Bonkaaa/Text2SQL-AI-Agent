import sqlglot
from pydantic import BaseModel, Field
from sqlglot import exp
from sqlglot.errors import ParseError


class ASTValidationResult(BaseModel):
    """Kết quả kiểm tra cú pháp và tính an toàn của câu lệnh SQL qua AST."""

    is_valid: bool = Field(description="True nếu SQL an toàn và hợp lệ")
    sanitized_sql: str = Field(
        default="", description="Câu lệnh SQL đã được làm sạch và chuẩn hóa"
    )
    tables_used: list[str] = Field(
        default_factory=list,
        description="Danh sách các bảng cơ sở dữ liệu được sử dụng",
    )
    columns_used: list[str] = Field(
        default_factory=list, description="Danh sách các cột được tham chiếu"
    )
    error_type: str | None = Field(
        default=None, description="Mã phân loại lỗi (nếu có)"
    )
    error_message: str | None = Field(
        default=None, description="Thông báo lỗi chi tiết"
    )


# Danh sách các AST expression làm thay đổi dữ liệu hoặc cấu trúc DB (bị cấm tuyệt đối)
FORBIDDEN_EXPRESSION_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
    exp.Transaction,
)


def sanitize_and_validate_sql(
    sql: str,
    dialect: str = "duckdb",
    default_limit: int = 1000,
    enforce_limit: bool = True,
) -> ASTValidationResult:
    """Phân tích AST của câu lệnh SQL, đảm bảo chỉ cho phép SELECT, chặn injection và ép LIMIT.

    Args:
        sql: Câu lệnh SQL cần kiểm tra.
        dialect: Dialect của SQL (mặc định 'duckdb').
        default_limit: Số dòng tối đa cho phép trả về (mặc định 1000).
        enforce_limit: Tự động tiêm LIMIT nếu câu lệnh thiếu.

    Returns:
        ASTValidationResult: Kết quả phân tích và câu SQL đã làm sạch.
    """
    if not sql or not sql.strip():
        return ASTValidationResult(
            is_valid=False,
            error_type="EMPTY_QUERY",
            error_message="Câu lệnh SQL rỗng.",
        )

    # 1. Parse câu SQL thành các biểu thức AST
    try:
        parsed_expressions = sqlglot.parse(sql, read=dialect)
    except ParseError as exc:
        return ASTValidationResult(
            is_valid=False,
            error_type="SYNTAX_ERROR",
            error_message=f"Lỗi cú pháp SQL: {exc}",
        )

    # Lọc bỏ các phần tử None
    expressions = [e for e in parsed_expressions if e is not None]

    if not expressions:
        return ASTValidationResult(
            is_valid=False,
            error_type="EMPTY_QUERY",
            error_message="Không tìm thấy câu lệnh SQL hợp lệ.",
        )

    # 2. Chặn nhiều câu lệnh (Multiple statements attack)
    if len(expressions) > 1:
        return ASTValidationResult(
            is_valid=False,
            error_type="MULTIPLE_STATEMENTS",
            error_message="Phát hiện nhiều câu lệnh SQL trong cùng một yêu cầu. Chỉ cho phép thực thi 1 câu lệnh duy nhất.",
        )

    expression = expressions[0]

    # 3. Kiểm tra Root Expression và quét các lệnh cấm
    if not isinstance(expression, (exp.Select, exp.Union)):
        return ASTValidationResult(
            is_valid=False,
            error_type="FORBIDDEN_STATEMENT",
            error_message=f"Chỉ cho phép truy vấn đọc dữ liệu (SELECT), phát hiện câu lệnh bị cấm: {type(expression).__name__}.",
        )

    # Quét toàn bộ cây AST để đảm bảo không có lệnh DML/DDL nào lẩn khuất bên trong
    for forbidden_type in FORBIDDEN_EXPRESSION_TYPES:
        if expression.find(forbidden_type):
            return ASTValidationResult(
                is_valid=False,
                error_type="FORBIDDEN_STATEMENT",
                error_message=f"Phát hiện lệnh bị cấm lẩn khuất trong câu truy vấn: {forbidden_type.__name__}.",
            )

    # 4. Trích xuất tên CTE (Common Table Expressions) để loại trừ khỏi tables_used
    cte_names: set[str] = {cte.alias.lower() for cte in expression.ctes if cte.alias}

    # 5. Trích xuất Tables và Columns sử dụng
    tables_used_set: set[str] = set()
    for tbl in expression.find_all(exp.Table):
        tbl_name = tbl.name.lower()
        # Loại trừ CTE và bảng rỗng
        if tbl_name and tbl_name not in cte_names:
            tables_used_set.add(tbl_name)

    columns_used_set: set[str] = set()
    for col in expression.find_all(exp.Column):
        col_name = col.name.lower()
        if col_name and col_name != "*":
            columns_used_set.add(col_name)

    # 6. Ép mệnh đề LIMIT an toàn
    if enforce_limit:
        limit_node = expression.args.get("limit")
        if limit_node is None:
            # Chưa có LIMIT -> tự động thêm LIMIT default_limit
            expression = expression.limit(default_limit, copy=False)
        else:
            # Đã có LIMIT -> kiểm tra xem có vượt quá default_limit không
            try:
                current_limit_val = int(limit_node.expression.this)
                if current_limit_val > default_limit:
                    expression = expression.limit(default_limit, copy=False)
            except (ValueError, TypeError, AttributeError):
                expression = expression.limit(default_limit, copy=False)

    sanitized_sql = expression.sql(dialect=dialect)

    return ASTValidationResult(
        is_valid=True,
        sanitized_sql=sanitized_sql,
        tables_used=sorted(tables_used_set),
        columns_used=sorted(columns_used_set),
    )
