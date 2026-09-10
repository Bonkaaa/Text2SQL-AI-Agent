from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

from src.models.rbac import UserContext


class ClarificationResult(BaseModel):
    """Kết quả phân tích độ rõ ràng của câu hỏi người dùng."""

    needs_clarification: bool = Field(
        description="True nếu câu hỏi thiếu điều kiện lọc cốt lõi"
    )
    reason: str | None = Field(
        default=None, description="Lý do câu hỏi bị đánh giá là mơ hồ"
    )
    clarification_question: str | None = Field(
        default=None, description="Câu hỏi làm rõ gợi ý cho người dùng"
    )
    suggested_options: list[str] = Field(
        default_factory=list,
        description="Danh sách các tùy chọn gợi ý (A, B, C...)",
    )


class RechartsConfig(BaseModel):
    """Cấu hình render biểu đồ Recharts trả về cho Frontend UI."""

    chart_type: Literal["bar", "line", "area", "pie", "table"] = Field(
        description="Loại biểu đồ trực quan hóa"
    )
    title: str = Field(description="Tiêu đề biểu đồ")
    x_axis: str = Field(description="Tên trường dữ liệu cho trục hoành (X)")
    y_axis: list[str] | str = Field(
        description="Tên trường (hoặc danh sách trường) dữ liệu cho trục tung (Y)"
    )
    description: str | None = Field(
        default=None, description="Mô tả ngắn gọn về biểu đồ"
    )


class ControlPipelineInput(TypedDict):
    """Input đầu vào cho LangGraph Control Pipeline."""

    sql: str
    user_context: UserContext
    session_id: str


class ControlPipelineOutput(TypedDict):
    """Kết quả đầu ra từ LangGraph Control Pipeline."""

    is_valid: bool
    status: Literal[
        "SUCCESS", "BLOCKED_AST", "BLOCKED_RBAC", "BLOCKED_COST", "DB_ERROR", "TIMEOUT"
    ]
    error_type: str | None
    error_message: str | None
    actionable_feedback: str | None
    data: list[dict[str, Any]] | None
    columns: list[str] | None
    bytes_scanned: int
    execution_time_ms: float


class ControlState(TypedDict, total=False):
    """Trạng thái nội bộ của Subgraph LangGraph Control Pipeline."""

    sql: str
    user_context: UserContext
    session_id: str
    schema_context: str | None

    # Kết quả kiểm duyệt AST
    ast_valid: bool
    tables_used: list[str]
    columns_used: list[str]

    # Kết quả kiểm duyệt RBAC
    rbac_valid: bool

    # Kết quả kiểm duyệt Chi phí (Cost Guard)
    cost_valid: bool
    estimated_bytes: int

    # Phê duyệt người dùng (HITL interrupt)
    hitl_required: bool
    hitl_approved: bool | None

    # Chẩn đoán lỗi thông minh (Error Diagnostic Agent)
    actionable_feedback: str | None

    # Kết quả thực thi
    execution_result: ControlPipelineOutput | None



class AgentState(TypedDict, total=False):
    """Trạng thái tổng thể của Master Supervisor Agent Graph."""

    session_id: str
    user_context: UserContext
    question: str

    # Khâu Clarification
    needs_clarification: bool
    clarification_question: str | None
    clarification_options: list[str] | None

    # Khâu Schema Retrieval
    schema_context: str | None

    # Khâu SQL Generation & Self-correction
    draft_sql: str | None
    retry_count: int
    error_context: str | None

    # Khâu Thực thi và Kiểm soát (Control Pipeline)
    query_result: ControlPipelineOutput | None
    hitl_approved: bool | None

    # Khâu Phản hồi và Trực quan hóa
    response_insight: str | None
    visualization_config: dict[str, Any] | None
