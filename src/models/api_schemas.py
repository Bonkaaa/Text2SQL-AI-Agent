"""Pydantic V2 Schemas cho FastAPI Gateway Endpoints (Component 5.1).

Bao gồm các cấu trúc dữ liệu Request / Response cho:
- /api/v1/query/ask: Nhận câu hỏi, trả về kết quả hoặc trạng thái cần làm rõ / chờ phê duyệt.
- /api/v1/query/approve: Nhận quyết định phê duyệt con người (HITL).
- /api/v1/query/history: Xem lịch sử truy vấn và vết artifacts của phiên.
- /api/v1/audit/logs: Xem nhật ký audit trail của hệ thống (chỉ dành cho Admin).
- /health: Trạng thái kết nối dịch vụ.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.models.artifacts import ArtifactBundle, QueryArtifact
from src.models.rbac import UserRole

# ==============================================================================
# 1. SCHEMAS CHO /api/v1/query/ask
# ==============================================================================


class AskQueryRequest(BaseModel):
    """Schema yêu cầu gửi câu hỏi phân tích dữ liệu."""

    question: str = Field(
        ...,
        min_length=1,
        description="Câu hỏi ngôn ngữ tự nhiên về dữ liệu kinh doanh / TPC-H",
        examples=["Top 5 khách hàng có tổng chi tiêu cao nhất năm 1995"],
    )
    session_id: str | None = Field(
        default=None,
        description="Mã định danh phiên làm việc (nếu để trống hệ thống sẽ tự sinh)",
        examples=["sess_analytics_001"],
    )
    user_id: str = Field(
        default="default_user",
        description="Định danh tài khoản người dùng gửi truy vấn",
        examples=["analyst_alex"],
    )
    role: UserRole = Field(
        default=UserRole.ANALYST,
        description="Vai trò người dùng trong hệ thống (ANALYST / ADMIN / BUSINESS_USER)",
        examples=[UserRole.ANALYST],
    )
    session_token: str | None = Field(
        default=None,
        description="Mã bí mật xác thực quyền sở hữu phiên làm việc (Session Secret Token)",
        examples=["k9e3_abc123..."],
    )


class QueryResponse(BaseModel):
    """Schema phản hồi kết quả truy vấn phân tích (Kiến trúc v4.0 Evolution)."""

    session_id: str = Field(description="Mã phiên làm việc")
    status: Literal[
        "COMPLETED",
        "SUCCESS",
        "CLARIFICATION_REQUIRED",
        "SECURITY_BLOCKED",
        "PENDING_APPROVAL",
        "ERROR",
    ] = Field(description="Trạng thái kết quả xử lý")
    question: str = Field(description="Câu hỏi gốc của người dùng")
    final_answer: str | None = Field(
        default=None,
        description="Câu trả lời tóm tắt cuối cùng từ Agent",
    )
    sql: str | None = Field(
        default=None,
        description="Câu lệnh SELECT SQL đã được sinh và kiểm duyệt",
    )
    data: list[dict[str, Any]] | None = Field(
        default=None,
        description="Dữ liệu kết quả truy vấn trả về từ Data Warehouse",
    )
    columns: list[str] | None = Field(
        default=None,
        description="Danh sách tên các cột dữ liệu trả về",
    )
    recharts_config: dict[str, Any] | None = Field(
        default=None,
        description="Cấu hình biểu đồ Recharts JSON để vẽ chart ở frontend",
    )

    # Pre-Flight Security & Clarification Fields (v4 - Phase 2.5)
    is_safe: bool = Field(
        default=True,
        description="Đánh dấu câu hỏi an toàn (True) hay vi phạm an ninh/ngoài miền (False)",
    )
    safety_category: str | None = Field(
        default=None,
        description="Phân loại an toàn nếu bị chặn (UNSAFE_PROMPT_INJECTION, UNSUPPORTED_OUT_OF_DOMAIN,...)",
    )
    refusal_reason: str | None = Field(
        default=None,
        description="Lý do từ chối cứng theo tiêu chuẩn Hardcoded Refusal",
    )
    is_ambiguous: bool = Field(
        default=False,
        description="Đánh dấu câu hỏi có bị mơ hồ hay không",
    )
    clarification_question: str | None = Field(
        default=None,
        description="Câu hỏi làm rõ nếu status là CLARIFICATION_REQUIRED",
    )
    suggested_options: list[str] = Field(
        default_factory=list,
        description="Danh sách các phương án gợi ý A, B, C khi câu hỏi mơ hồ",
    )

    # Analytics & Multi-Query Fields (v4 - Phase 2 & 3)
    intent: Literal["CONVERSATION", "ANALYTICS"] | None = Field(
        default=None,
        description="Phân luồng ý định người dùng (CONVERSATION / METADATA vs ANALYTICS)",
    )
    tasks: list[dict[str, Any]] | None = Field(
        default=None,
        description="Danh sách tóm tắt các tác vụ trong AnalysisPlan",
    )
    artifacts: list[dict[str, Any]] | list[QueryArtifact] | None = Field(
        default=None,
        description="Danh sách bằng chứng truy vấn đã thực thi (QueryArtifacts)",
    )
    response_package: dict[str, Any] | None = Field(
        default=None,
        description="Gói phản hồi đa chiều hoàn chỉnh (ResponsePackage Phase 3)",
    )
    output_artifacts: list[dict[str, Any]] | None = Field(
        default=None,
        description="Danh sách các ArtifactItem (KPI, Chart, Table, Callout) cho Frontend Component Registry",
    )
    insight: dict[str, Any] | str | None = Field(
        default=None,
        description="Tóm tắt insight phân tích kinh doanh",
    )
    visualization: dict[str, Any] | None = Field(
        default=None,
        description="Cấu hình trực quan hóa chính (Primary chart)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Thông tin metadata thực thi (query_count, execution_time_ms,...)",
    )
    artifact_bundle: ArtifactBundle | None = Field(
        default=None,
        description="Gói kết quả tương thích ngược",
    )

    # Runtime & Governance Fields
    requires_hitl: bool = Field(
        default=False,
        description="Đánh dấu câu truy vấn có đang dừng chờ phê duyệt HITL hay không",
    )
    estimated_cost_bytes: int | None = Field(
        default=None,
        description="Ước tính dung lượng quét dữ liệu nếu cần duyệt chi phí",
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Tổng thời gian xử lý toàn trình (mili-giây)",
    )
    error: str | None = Field(
        default=None,
        description="Thông báo lỗi chi tiết nếu status là ERROR",
    )
    session_token: str | None = Field(
        default=None,
        description="Token bí mật xác thực phiên làm việc (dùng cho các request tiếp theo)",
    )


# ==============================================================================
# 2. SCHEMAS CHO /api/v1/query/approve
# ==============================================================================


class ApprovalRequest(BaseModel):
    """Schema yêu cầu phê duyệt hoặc từ chối câu truy vấn chờ HITL."""

    session_id: str = Field(
        ...,
        description="Mã phiên đang tạm dừng tại chốt chặn interrupt()",
    )
    task_id: str | None = Field(
        default=None,
        description="Mã nhiệm vụ phân tích cụ thể (tùy chọn)",
    )
    approval_id: str | None = Field(
        default=None,
        description="Mã phê duyệt duy nhất (tùy chọn)",
    )
    session_token: str | None = Field(
        default=None,
        description="Token bí mật xác thực phiên làm việc (tùy chọn nếu đã dùng header)",
    )
    approved: bool = Field(
        ...,
        description="Quyết định phê duyệt: True (Đồng ý thực thi) hoặc False (Từ chối)",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Lý do từ chối nếu approved=False",
    )


class ApprovalResponse(BaseModel):
    """Schema phản hồi kết quả sau khi gửi quyết định duyệt."""

    session_id: str = Field(description="Mã phiên làm việc")
    approval_id: str | None = Field(default=None, description="Mã phê duyệt duy nhất")
    approved: bool = Field(description="Quyết định đã được tiếp nhận")
    status: str = Field(description="Trạng thái thực thi sau phê duyệt")
    message: str = Field(description="Thông báo chi tiết")
    session_token: str | None = Field(
        default=None,
        description="Token bí mật xác thực phiên làm việc",
    )
    data: list[dict[str, Any]] | None = Field(
        default=None,
        description="Dữ liệu truy vấn trả về nếu được duyệt thành công",
    )
    columns: list[str] | None = Field(
        default=None,
        description="Danh sách cột dữ liệu trả về",
    )


# ==============================================================================
# 3. SCHEMAS CHO /api/v1/query/history
# ==============================================================================


class QueryHistoryItem(BaseModel):
    """Chi tiết một mục lịch sử truy vấn trong phiên."""

    session_id: str = Field(description="Mã phiên")
    timestamp: str | None = Field(
        default=None, description="Thời gian thực hiện (ISO 8601)"
    )
    status: str | None = Field(default=None, description="Trạng thái hoàn thành")
    question: str | None = Field(default=None, description="Câu hỏi người dùng")
    artifacts: list[str] = Field(
        default_factory=list,
        description="Danh sách tên các tệp artifacts đã ghi nhận",
    )


class QueryHistoryResponse(BaseModel):
    """Schema phản hồi danh sách lịch sử truy vấn."""

    session_id: str = Field(description="Mã phiên làm việc")
    history: list[QueryHistoryItem] = Field(
        default_factory=list,
        description="Danh sách các phiên truy vấn đã thực hiện",
    )


# ==============================================================================
# 4. SCHEMAS CHO /api/v1/audit/logs
# ==============================================================================


class AuditLogsResponse(BaseModel):
    """Schema phản hồi nhật ký kiểm toán hệ thống (Audit Trail)."""

    total: int = Field(description="Tổng số bản ghi thỏa mãn điều kiện lọc")
    limit: int = Field(description="Số lượng bản ghi tối đa trả về")
    offset: int = Field(description="Vị trí bắt đầu đọc bản ghi")
    logs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách các bản ghi nhật ký audit log",
    )


# ==============================================================================
# 5. SCHEMAS CHO /health
# ==============================================================================


class HealthResponse(BaseModel):
    """Schema kiểm tra tình trạng hoạt động của hệ thống."""

    status: str = Field(default="healthy", description="Trạng thái hệ thống")
    database: str = Field(default="connected", description="Trạng thái kết nối DuckDB")
    version: str = Field(default="1.0.0", description="Phiên bản API Gateway")
