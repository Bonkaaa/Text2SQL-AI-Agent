"""Định nghĩa các Models và Hợp đồng Dữ liệu Định kiểu (Typed Artifact Contracts) cho Kiến trúc v4.0.

Loại bỏ hoàn toàn việc bóc tách Regex trên chuỗi text Markdown.
Tất cả các thành phần (Control Pipeline, Analysis Subagent, Synthesizer, API Routes)
giao tiếp thông qua các Pydantic v2 Models này.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class QueryArtifact(BaseModel):
    """Bằng chứng dữ liệu định kiểu sinh ra từ một lần thực thi truy vấn SQL qua Control Pipeline."""

    artifact_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Định danh duy nhất của artifact",
    )
    task_id: str = Field(
        default="task_1",
        description="Liên kết với AnalysisTask tương ứng trong AnalysisPlan",
    )

    # Chi tiết truy vấn
    sql: str = Field(description="Câu truy vấn SQL đã chạy")
    dialect: Literal["duckdb", "bigquery"] = Field(
        default="duckdb",
        description="Dialect SQL của câu lệnh",
    )
    explanation: str = Field(
        default="",
        description="Mục tiêu hoặc lời giải thích ngắn gọn về câu truy vấn",
    )

    # Lineage lược đồ
    tables_used: list[str] = Field(
        default_factory=list,
        description="Danh sách các bảng TPC-H được sử dụng trong truy vấn",
    )
    columns_used: list[str] = Field(
        default_factory=list,
        description="Danh sách các cột được sử dụng trong truy vấn",
    )

    # Kết quả thực thi
    status: Literal[
        "SUCCESS",
        "BLOCKED_AST",
        "BLOCKED_RBAC",
        "BLOCKED_COST",
        "BLOCKED_HITL",
        "DB_ERROR",
        "TIMEOUT",
    ] = Field(
        default="SUCCESS",
        description="Trạng thái thực thi truy vấn qua Control Pipeline",
    )
    data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Dữ liệu kết quả thực thi dạng danh sách bản ghi dict",
    )
    columns: list[str] = Field(
        default_factory=list,
        description="Danh sách các cột trả về trong kết quả",
    )
    row_count: int = Field(
        default=0,
        description="Số lượng dòng kết quả",
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Thời gian thực thi truy vấn (ms)",
    )
    error_message: str | None = Field(
        default=None,
        description="Thông báo lỗi chi tiết nếu truy vấn bị chặn hoặc thất bại",
    )


class AnalysisTask(BaseModel):
    """Một nhiệm vụ truy vấn phân tích đơn lẻ trong kế hoạch tổng thể."""

    task_id: str = Field(description="Mã định danh nhiệm vụ (task_1, task_2,...)")
    description: str = Field(
        description="Câu hỏi nghiệp vụ cụ thể cần trả lời bằng SQL"
    )
    status: Literal[
        "PLANNED",
        "RETRIEVING_CONTEXT",
        "GENERATING_QUERY",
        "VALIDATING",
        "EXECUTING",
        "COMPLETED",
        "FAILED",
    ] = Field(
        default="PLANNED",
        description="Trạng thái thực hiện của nhiệm vụ",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Danh sách các task_id phụ thuộc (nếu có)",
    )
    query_artifact: QueryArtifact | None = Field(
        default=None,
        description="Bằng chứng truy vấn sinh ra sau khi thực thi hoàn tất",
    )
    retry_count: int = Field(
        default=0,
        description="Số lần tự sửa lỗi đã thử cho nhiệm vụ này",
    )


class AnalysisPlan(BaseModel):
    """Kế hoạch phân tích dữ liệu đa bước (Multi-Query Plan) do Planner khởi tạo."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Định danh duy nhất của kế hoạch",
    )
    goal: str = Field(description="Mục tiêu phân tích tổng thể từ câu hỏi người dùng")
    hypotheses: list[str] = Field(
        default_factory=list,
        description="Các giả thuyết nghiệp vụ cần kiểm chứng",
    )
    tasks: list[AnalysisTask] = Field(
        description="Danh sách các nhiệm vụ phân tích con",
    )
    max_tasks: int = Field(
        default=3,
        description="Trần số lượng nhiệm vụ tối đa cho phép trong phiên",
    )
    current_task_index: int = Field(
        default=0,
        description="Chỉ số của nhiệm vụ đang thực hiện trong tasks",
    )
    evidence_summary: str | None = Field(
        default=None,
        description="Tóm tắt các bằng chứng và phát hiện thu thập được",
    )
    needs_more_evidence: bool = Field(
        default=False,
        description="True nếu cần sinh thêm nhiệm vụ sau khi phân tích bằng chứng",
    )

    @model_validator(mode="after")
    def validate_budget_ceiling(self) -> AnalysisPlan:
        """Đảm bảo số lượng nhiệm vụ không bao giờ vượt quá trần max_tasks."""
        if len(self.tasks) > self.max_tasks:
            raise ValueError(
                f"Số lượng tasks ({len(self.tasks)}) vượt quá trần cho phép ({self.max_tasks})"
            )
        return self

    @property
    def current_task(self) -> AnalysisTask | None:
        """Lấy nhiệm vụ hiện tại cần thực thi."""
        if 0 <= self.current_task_index < len(self.tasks):
            return self.tasks[self.current_task_index]
        return None

    @property
    def is_completed(self) -> bool:
        """Kiểm tra xem toàn bộ các tasks đã được xử lý xong chưa."""
        return all(t.status in ("COMPLETED", "FAILED") for t in self.tasks)

    def advance(self) -> None:
        """Chuyển sang nhiệm vụ tiếp theo."""
        if self.current_task_index < len(self.tasks):
            self.current_task_index += 1

    def complete_current_task(
        self,
        artifact: QueryArtifact,
        summary_update: str | None = None,
    ) -> None:
        """Đánh dấu task hiện tại đã hoàn tất với QueryArtifact tương ứng."""
        task = self.current_task
        if task is not None:
            task.status = "COMPLETED"
            task.query_artifact = artifact
        if summary_update is not None:
            self.evidence_summary = summary_update

    def fail_current_task(self, error_message: str | None = None) -> None:
        """Đánh dấu task hiện tại bị thất bại."""
        task = self.current_task
        if task is not None:
            task.status = "FAILED"
            task.retry_count += 1


class AnalyticsResult(BaseModel):
    """Kết quả hoàn chỉnh của toàn bộ quy trình phân tích dữ liệu đa truy vấn."""

    plan: AnalysisPlan = Field(description="Kế hoạch phân tích đã thực hiện")
    artifacts: list[QueryArtifact] = Field(
        default_factory=list,
        description="Danh sách các bằng chứng QueryArtifact thu thập được",
    )
    insight: str | None = Field(
        default=None,
        description="Nhận định phân tích nghiệp vụ tổng thể",
    )
    visualization: dict[str, Any] | None = Field(
        default=None,
        description="Cấu hình trực quan hóa hoặc đồ thị biểu diễn kết quả",
    )
    status: Literal["COMPLETED", "PARTIAL", "FAILED"] = Field(
        default="COMPLETED",
        description="Trạng thái hoàn thành của toàn bộ phiên phân tích",
    )


class EvidenceEvaluation(BaseModel):
    """Mô hình Pydantic đánh giá tính đầy đủ của dữ liệu/bằng chứng thu thập."""

    has_enough_evidence: bool = Field(
        ...,
        description="True nếu đã có đủ dữ liệu/bằng chứng để tổng hợp câu trả lời; False nếu cần truy vấn thêm.",
    )
    findings_summary: str = Field(
        ...,
        description="Tóm tắt ngắn gọn các phát hiện rút ra từ bằng chứng hiện có.",
    )
    next_task: AnalysisTask | None = Field(
        default=None,
        description="Task tiếp theo cần thực thi nếu has_enough_evidence=False và còn ngân sách.",
    )
    reasoning: str = Field(
        default="",
        description="Lập luận logic cho việc dừng hoặc cần thêm dữ liệu.",
    )


class EvidenceStore(BaseModel):
    """Kho lưu trữ bằng chứng tích lũy qua các vòng lặp truy vấn."""

    evidences: list[QueryArtifact] = Field(
        default_factory=list,
        description="Danh sách các QueryArtifact thu thập được qua các tasks",
    )
    accumulated_findings: list[str] = Field(
        default_factory=list,
        description="Các phát hiện phân tích sơ bộ tích lũy được qua từng bước",
    )


class ChartSpec(BaseModel):
    """Đặc tả biểu đồ trực quan hóa Recharts cho Frontend."""

    chart_type: Literal["bar", "line", "area", "pie", "composed", "table"] = Field(
        description="Loại biểu đồ Recharts"
    )
    title: str = Field(description="Tiêu đề biểu đồ")
    x_axis_key: str = Field(description="Tên trường dữ liệu cho trục X")
    y_axis_keys: list[str] = Field(
        description="Danh sách tên các trường dữ liệu cho trục Y"
    )
    series_labels: dict[str, str] = Field(
        default_factory=dict,
        description="Nhãn hiển thị tiếng Việt cho các chuỗi dữ liệu (ví dụ: {'revenue': 'Doanh thu (USD)'})",
    )
    color_palette: list[str] = Field(
        default_factory=list,
        description="Bảng màu hiển thị cho biểu đồ",
    )
    recommended_layout: str = Field(
        default="horizontal",
        description="Bố cục đề xuất: 'horizontal' hoặc 'vertical'",
    )


class TableSpec(BaseModel):
    """Đặc tả bảng số liệu hiển thị trên Frontend."""

    title: str = Field(description="Tiêu đề bảng số liệu")
    columns: list[str] = Field(description="Danh sách tên các cột hiển thị")
    column_formats: dict[str, str] = Field(
        default_factory=dict,
        description="Định dạng cho từng cột (ví dụ: {'revenue': 'currency', 'share': 'percentage'})",
    )
    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Dữ liệu các dòng hiển thị",
    )


class ArtifactBundle(BaseModel):
    """Gói kết quả hoàn chỉnh xuất xưởng từ Analytics Subagent chuyển tiếp về API và UI."""

    session_id: str = Field(description="Mã phiên làm việc (thread_id)")
    analysis_goal: str = Field(description="Mục tiêu phân tích ban đầu")
    executive_summary: str = Field(
        description="Tóm tắt điều hành 2-3 câu bằng tiếng Việt tự nhiên chuẩn mực",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Các luận điểm phân tích cốt lõi kèm dẫn chứng số liệu định lượng",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Khuyến nghị hành động kinh doanh hoặc bước đào sâu tiếp theo",
    )
    charts: list[ChartSpec] = Field(
        default_factory=list,
        description="Danh sách biểu đồ trực quan hóa Recharts được đề xuất",
    )
    tables: list[TableSpec] = Field(
        default_factory=list,
        description="Danh sách bảng dữ liệu chuẩn",
    )
    executed_artifacts: list[QueryArtifact] = Field(
        default_factory=list,
        description="Toàn bộ danh sách QueryArtifact đã thực thi trong phiên",
    )
    total_execution_time_ms: float = Field(
        default=0.0,
        description="Tổng thời gian thực thi toàn bộ quy trình (ms)",
    )


# ==============================================================================
# PRE-FLIGHT GUARDRAILS & CLARIFICATION MODELS (Component 2.5.2)
# ==============================================================================


class SafetyCategory(str, Enum):
    """Phân loại mức độ an toàn của câu hỏi đầu vào."""

    SAFE = "SAFE"
    UNSAFE_PROMPT_INJECTION = "UNSAFE_PROMPT_INJECTION"
    UNSAFE_DATA_MUTATION = "UNSAFE_DATA_MUTATION"
    UNSUPPORTED_OUT_OF_DOMAIN = "UNSUPPORTED_OUT_OF_DOMAIN"


class InputPreflightEvaluation(BaseModel):
    """Structured Output từ Tier 2 LLM đánh giá an toàn và độ rõ ràng của câu hỏi."""

    # 1. Guardrails Section
    is_safe: bool = Field(
        description="True nếu câu hỏi an toàn và nằm trong phạm vi nghiệp vụ phân tích dữ liệu TPC-H; False nếu vi phạm bảo mật hoặc hoàn toàn lạc đề."
    )
    safety_category: SafetyCategory = Field(
        default=SafetyCategory.SAFE,
        description="Phân loại mức độ an toàn của câu hỏi."
    )
    safety_reason: str | None = Field(
        default=None,
        description="Giải thích ngắn gọn lý do kỹ thuật nếu phát hiện câu hỏi không an toàn hoặc ngoài miền."
    )

    # 2. Clarification Section
    needs_clarification: bool = Field(
        description="True nếu câu hỏi an toàn nhưng mơ hồ, thiếu chiều lọc quan trọng (thời gian, khu vực, đối tượng) để sinh SQL chính xác."
    )
    clarification_reason: str | None = Field(
        default=None,
        description="Lý do cần làm rõ (ví dụ: 'Chưa có mốc thời gian', 'Thiếu đối tượng phân tích cụ thể')."
    )
    clarification_question: str | None = Field(
        default=None,
        description="Câu hỏi tiếng Việt lịch sự, định hướng nghiệp vụ để hỏi lại người dùng."
    )
    suggested_options: list[str] = Field(
        default_factory=list,
        description="Danh sách từ 2-4 tùy chọn gợi ý cụ thể A, B, C... dựa trên ngữ cảnh TPC-H."
    )


class PreflightDecisionType(str, Enum):
    """Loại quyết định phân luồng từ Pre-flight Gatekeeper."""

    ALLOWED = "ALLOWED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"


class PreflightDecision(BaseModel):
    """Kết quả tổng hợp từ toàn bộ vành đai Pre-flight Gatekeeper (Tier 1 + Tier 2)."""

    decision: PreflightDecisionType = Field(
        description="Quyết định cuối cùng của Gatekeeper"
    )
    is_safe: bool = Field(
        description="True nếu an toàn, False nếu bị chặn an ninh"
    )
    safety_category: str | None = Field(
        default=None,
        description="Phân loại an toàn hoặc vi phạm"
    )
    refusal_message: str | None = Field(
        default=None,
        description="Thông báo từ chối tĩnh chuẩn hóa nếu bị chặn"
    )
    needs_clarification: bool = Field(
        default=False,
        description="True nếu cần hỏi lại người dùng"
    )
    clarification_question: str | None = Field(
        default=None,
        description="Câu hỏi làm rõ cho người dùng"
    )
    suggested_options: list[str] = Field(
        default_factory=list,
        description="Danh sách tùy chọn gợi ý A, B, C..."
    )
    evaluation: InputPreflightEvaluation | None = Field(
        default=None,
        description="Chi tiết structured evaluation từ Tier 2 LLM nếu có"
    )
    tier: Literal["tier1_regex", "tier2_llm", "fallback"] = Field(
        default="tier1_regex",
        description="Tầng kiểm duyệt đã đưa ra quyết định này"
    )


__all__ = [
    "AnalysisPlan",
    "AnalysisTask",
    "AnalyticsResult",
    "ArtifactBundle",
    "ChartSpec",
    "EvidenceEvaluation",
    "EvidenceStore",
    "InputPreflightEvaluation",
    "PreflightDecision",
    "PreflightDecisionType",
    "QueryArtifact",
    "SafetyCategory",
    "TableSpec",
]
