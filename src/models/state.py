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

    @property
    def is_ambiguous(self) -> bool:
        """Alias tương thích cho needs_clarification."""
        return self.needs_clarification


class SchemaContextResult(BaseModel):
    """Kết quả trích xuất ngữ cảnh lược đồ từ Schema & Value Retriever Subagent."""

    selected_tables: list[str] = Field(
        default_factory=list,
        description="Danh sách các bảng TPC-H liên quan được chọn lọc",
    )
    join_conditions: list[str] = Field(
        default_factory=list,
        description="Các điều kiện JOIN chuẩn giữa các bảng được chọn",
    )
    categorical_filters: dict[str, str] = Field(
        default_factory=dict,
        description="Từ điển các giá trị phân loại danh mục ánh xạ từ câu hỏi (ví dụ: {'c_mktsegment': 'BUILDING'})",
    )
    metric_formulas: list[str] = Field(
        default_factory=list,
        description="Danh sách các công thức tính toán chỉ số nghiệp vụ chuẩn (dbt semantic metrics)",
    )
    context_markdown: str = Field(
        description="Chuỗi Markdown cô đọng chứa DDL, JOIN, và Categorical context đưa vào prompt cho SQL Generator"
    )


class SQLGenerationResult(BaseModel):
    """Kết quả sinh câu lệnh SQL từ SQL Generator Subagent."""

    sql: str = Field(
        description="Câu lệnh SELECT SQL thuần túy, tuyệt đối không bọc markdown ```sql ```"
    )
    dialect: Literal["duckdb", "bigquery"] = Field(
        default="duckdb",
        description="Dialect của câu lệnh SQL (mặc định: duckdb)",
    )
    explanation: str = Field(
        description="Tóm tắt ngắn gọn logic truy vấn và các bước tính toán"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Các giả định ngầm định được áp dụng (nếu có)",
    )


class DiagnosticResult(BaseModel):
    """Kết quả chẩn đoán lỗi có cấu trúc từ Error Diagnostic Agent."""

    error_category: Literal[
        "AST_VIOLATION",
        "RBAC_VIOLATION",
        "COST_EXCEEDED",
        "DB_RUNTIME_ERROR",
        "TIMEOUT",
        "HITL_REJECTED",
        "UNKNOWN_ERROR",
    ] = Field(description="Phân loại lỗi kỹ thuật chính")
    root_cause: str = Field(description="Nguyên nhân cốt lõi gây ra lỗi truy vấn SQL")
    offending_entity: str | None = Field(
        default=None,
        description="Tên cột, bảng, hoặc từ khóa cấm vi phạm (ví dụ: 'c_phone')",
    )
    suggested_fix: str = Field(
        description="Hướng dẫn sửa kỹ thuật cụ thể cho SQL Generator"
    )
    actionable_feedback: str = Field(
        description="Đoạn văn bản tóm tắt 2-3 câu nạp trực tiếp vào prompt retry của SQL Generator"
    )


class SelfCorrectionResult(BaseModel):
    """Kết quả thực thi vòng lặp tự sửa lỗi Bounded Self-Correction."""

    success: bool = Field(
        description="True nếu truy vấn SQL hợp lệ và thực thi thành công"
    )
    sql: str = Field(
        description="Câu lệnh SQL cuối cùng (thành công hoặc lần thử cuối)"
    )
    data: list[dict[str, Any]] | None = Field(
        default=None, description="Dữ liệu kết quả truy vấn"
    )
    columns: list[str] | None = Field(
        default=None, description="Danh sách các cột kết quả"
    )
    retry_count: int = Field(default=0, description="Số lần đã thử lại sửa lỗi")
    explanation: str | None = Field(
        default=None, description="Giải thích logic truy vấn"
    )
    error_message: str | None = Field(
        default=None, description="Thông báo lỗi nếu thất bại"
    )
    error_type: str | None = Field(
        default=None, description="Mã phân loại lỗi kỹ thuật"
    )
    actionable_feedback: str | None = Field(
        default=None, description="Chỉ dẫn sửa lỗi từ lần thất bại cuối"
    )
    diagnostic_result: DiagnosticResult | None = Field(
        default=None, description="Kết quả chẩn đoán lỗi chi tiết"
    )
    execution_time_ms: float = Field(default=0.0, description="Thời gian thực thi (ms)")
    bytes_scanned: int = Field(default=0, description="Dung lượng dữ liệu quét (bytes)")
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Lịch sử các lần thử và phản hồi lỗi",
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


class SynthesizerResult(BaseModel):
    """Kết quả phân tích dữ liệu, diễn giải insight và cấu hình biểu đồ từ Response Synthesizer Subagent."""

    chart_type: Literal["bar", "line", "pie", "area", "table"] = Field(
        default="table",
        description="Loại biểu đồ trực quan hóa được đề xuất",
    )
    recharts_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Cấu hình JSON chi tiết cho Recharts Frontend (x_key, y_keys, series_labels, title...)",
    )
    business_insight: str = Field(
        description="2-3 câu diễn giải số liệu nổi bật bằng tiếng Việt, nêu rõ con số cụ thể và xu hướng",
    )
    summary_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Các giá trị tổng hợp định lượng cốt lõi (ví dụ: total_revenue, top_segment, max_value, count)",
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
        "SUCCESS",
        "BLOCKED_AST",
        "BLOCKED_RBAC",
        "BLOCKED_COST",
        "BLOCKED_HITL",
        "DB_ERROR",
        "TIMEOUT",
    ]
    error_type: str | None
    error_message: str | None
    actionable_feedback: str | None
    diagnostic_result: DiagnosticResult | None
    data: list[dict[str, Any]] | None
    columns: list[str] | None
    bytes_scanned: int
    execution_time_ms: float
    hitl_required: bool | None
    hitl_reason: str | None


class ControlState(TypedDict, total=False):
    """Trạng thái nội bộ của Subgraph LangGraph Control Pipeline."""

    sql: str
    user_context: UserContext
    session_id: str
    schema_context: str | None

    # Trạng thái xử lý và phân loại lỗi
    status: Literal[
        "SUCCESS", "BLOCKED_AST", "BLOCKED_RBAC", "BLOCKED_COST", "BLOCKED_HITL", "DB_ERROR", "TIMEOUT"
    ]
    error_type: str | None
    error_message: str | None
    execution_time_ms: float

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
    hitl_reason: str | None

    # Chẩn đoán lỗi thông minh (Error Diagnostic Agent)
    actionable_feedback: str | None
    diagnostic_result: DiagnosticResult | None

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
    diagnostic_result: DiagnosticResult | None

    # Khâu Thực thi và Kiểm soát (Control Pipeline)
    query_result: ControlPipelineOutput | None
    hitl_approved: bool | None

    # Khâu Phản hồi và Trực quan hóa
    response_insight: str | None
    visualization_config: dict[str, Any] | None
