"""One-Shot Response Synthesizer & Data Hydrator (Phase 3 / Component 3.2).

Tiếp nhận câu hỏi, mục tiêu phân tích và các QueryArtifacts để sinh ra ResponsePackage
hoàn chỉnh thông qua cơ chế 2 nhịp:
1. Nhịp 1: Gọi Tier 2 LLM sinh SynthesisDecision (direct_answer, detailed_insight, selected_artifacts specs).
2. Nhịp 2: Deterministic Data Hydration rót trực tiếp mảng dữ liệu thật 100% vào các specs.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import ANALYTICS_PRESENTATION_PROMPT
from src.config import get_settings
from src.models.artifacts import (
    ArtifactItem,
    ArtifactSpec,
    CalloutArtifact,
    ChartArtifact,
    KpiArtifact,
    QueryArtifact,
    ResponsePackage,
    SynthesisDecision,
    TableArtifact,
)
from src.services import get_chat_model

logger = logging.getLogger(__name__)


class ResponseSynthesizer:
    """Bộ tổng hợp phản hồi phân tích linh hoạt với cơ chế Composable ResponsePackage."""

    def __init__(self, model: BaseChatModel | None = None) -> None:
        """Khởi tạo ResponseSynthesizer.

        Args:
            model: ChatModel chỉ định (mặc định lấy Tier 2 từ cấu hình hệ thống).
        """
        self._model = model

    def _get_model(self) -> BaseChatModel:
        """Lấy instance ChatModel đang kích hoạt."""
        if self._model is not None:
            return self._model
        settings = get_settings()
        return get_chat_model(settings.tier2_model)

    def _format_artifacts_context(self, artifacts: list[QueryArtifact]) -> str:
        """Định dạng context tóm tắt các QueryArtifact để nạp vào prompt cho LLM."""
        sections = []
        for art in artifacts:
            sample_data = art.data[:5] if art.data else []
            section = (
                f"- Task ID: {art.task_id}\n"
                f"  SQL: {art.sql}\n"
                f"  Trạng thái: {art.status}\n"
                f"  Số dòng kết quả: {art.row_count}\n"
                f"  Danh sách cột: {art.columns}\n"
                f"  Mẫu dữ liệu (tối đa 5 dòng): {json.dumps(sample_data, ensure_ascii=False)}"
            )
            sections.append(section)
        return "\n\n".join(sections)

    def _hydrate_artifacts(
        self,
        specs: list[ArtifactSpec],
        artifacts: list[QueryArtifact],
    ) -> list[ArtifactItem]:
        """Bơm (hydrate) mảng dữ liệu thực thi chính xác 100% từ QueryArtifact vào các specs."""
        task_map = {a.task_id: a for a in artifacts if a.status == "SUCCESS"}
        successful_artifacts = [
            a for a in artifacts if a.status == "SUCCESS" and a.data
        ]
        default_artifact = successful_artifacts[0] if successful_artifacts else None

        hydrated_items: list[ArtifactItem] = []

        for spec in specs:
            source = task_map.get(spec.target_task_id, default_artifact)
            if source is None or not source.data:
                continue

            if spec.artifact_type == "kpi":
                # Trích xuất giá trị chỉ số từ dòng đầu tiên
                first_row = source.data[0]
                metric_col = spec.kpi_metric_column
                val: Any = None

                if metric_col and metric_col in first_row:
                    val = first_row[metric_col]
                else:
                    # Lấy giá trị số đầu tiên tìm thấy trong dòng
                    for v in first_row.values():
                        if isinstance(v, (int, float)):
                            val = v
                            break
                    if val is None and first_row:
                        val = next(iter(first_row.values()))

                if val is not None:
                    hydrated_items.append(
                        KpiArtifact(
                            title=spec.kpi_title or "Chỉ số quan trọng",
                            value=val,
                            unit=spec.kpi_unit,
                        )
                    )

            elif spec.artifact_type == "chart":
                cols = source.columns or list(source.data[0].keys())
                x_key = spec.x_axis_column or (cols[0] if cols else "x")
                y_keys = spec.y_axis_columns or (
                    [cols[1]] if len(cols) > 1 else [cols[0]]
                )

                hydrated_items.append(
                    ChartArtifact(
                        chart_type=spec.chart_type or "bar",
                        title=spec.chart_title or "Biểu đồ phân tích số liệu",
                        x_key=x_key,
                        y_keys=y_keys,
                        series_labels=spec.series_labels or {},
                        data=source.data,
                    )
                )

            elif spec.artifact_type == "table":
                cols = (
                    spec.display_columns
                    or source.columns
                    or list(source.data[0].keys())
                )
                hydrated_items.append(
                    TableArtifact(
                        title=spec.table_title or "Bảng dữ liệu chi tiết",
                        columns=cols,
                        rows=source.data,
                        total_row_count=len(source.data),
                    )
                )

            elif spec.artifact_type == "callout":
                hydrated_items.append(
                    CalloutArtifact(
                        variant=spec.callout_variant or "info",
                        message=spec.callout_message or "",
                    )
                )

        return hydrated_items

    def _determine_layout(self, items: list[ArtifactItem]) -> str:
        """Xác định bố cục hiển thị đề xuất cho Frontend dựa trên danh sách artifacts."""
        if len(items) >= 3:
            return "dashboard_grid"
        if len(items) == 1 and isinstance(items[0], KpiArtifact):
            return "focus"
        return "stacked"

    def _create_fallback_package(
        self,
        question: str,
        artifacts: list[QueryArtifact],
        session_id: str,
        error_reason: str | None = None,
    ) -> ResponsePackage:
        """Tạo gói phản hồi dự phòng an toàn (Fail-Safe Fallback) khi LLM gặp sự cố."""
        logger.warning(
            "Kích hoạt gói phản hồi dự phòng (Fallback ResponsePackage) cho câu hỏi: %s",
            question,
        )
        successful_artifacts = [
            a for a in artifacts if a.status == "SUCCESS" and a.data
        ]
        items: list[ArtifactItem] = []

        if successful_artifacts:
            art = successful_artifacts[0]
            items.append(
                TableArtifact(
                    title=f"Kết quả truy vấn: {question}",
                    columns=art.columns or list(art.data[0].keys()),
                    rows=art.data,
                    total_row_count=len(art.data),
                )
            )
            direct_answer = f"Đã hoàn thành truy vấn dữ liệu cho câu hỏi '{question}' với {len(art.data)} bản ghi."
        else:
            items.append(
                CalloutArtifact(
                    variant="error",
                    message=error_reason or "Không thể truy vấn hoặc tổng hợp dữ liệu.",
                )
            )
            direct_answer = (
                f"Rất tiếc, quá trình xử lý câu hỏi '{question}' không thành công."
            )

        return ResponsePackage(
            session_id=session_id,
            direct_answer=direct_answer,
            detailed_insight=[],
            layout="stacked",
            artifacts=items,
            executed_queries=[{"task_id": a.task_id, "sql": a.sql} for a in artifacts],
            total_execution_time_ms=sum(a.execution_time_ms for a in artifacts),
        )

    async def synthesize(
        self,
        question: str,
        artifacts: list[QueryArtifact],
        analysis_goal: str | None = None,
        session_id: str = "default",
    ) -> ResponsePackage:
        """Thực hiện tổng hợp phản hồi nghiệp vụ hoàn chỉnh theo mô hình Composable Output Package.

        Args:
            question: Câu hỏi gốc của người dùng.
            artifacts: Danh sách QueryArtifact thu thập được qua các tasks.
            analysis_goal: Mục tiêu kế hoạch phân tích ban đầu.
            session_id: Mã phiên làm việc.

        Returns:
            ResponsePackage hoàn chỉnh sẵn sàng cho API và Web UI.
        """
        # ======================================================================
        # 1. FAST-PATH VALIDATION (Zero LLM token & Zero Latency)
        # ======================================================================
        if not artifacts:
            return ResponsePackage(
                session_id=session_id,
                direct_answer="Không tìm thấy dữ liệu phù hợp trong cơ sở dữ liệu để trả lời câu hỏi.",
                detailed_insight=[],
                layout="focus",
                artifacts=[
                    CalloutArtifact(
                        variant="no_data",
                        message="Không tìm thấy bản ghi nào trong cơ sở dữ liệu.",
                    )
                ],
                executed_queries=[],
                total_execution_time_ms=0.0,
            )

        successful_artifacts = [
            a for a in artifacts if a.status == "SUCCESS" and a.data
        ]
        if not successful_artifacts:
            error_details = [
                f"- Task {a.task_id}: {a.error_message}"
                for a in artifacts
                if a.error_message
            ]
            error_summary = (
                "\n".join(error_details)
                if error_details
                else "Các truy vấn cơ sở dữ liệu đều không trả về kết quả hợp lệ."
            )
            return ResponsePackage(
                session_id=session_id,
                direct_answer=f"Quá trình phân tích cho câu hỏi '{question}' thất bại do các truy vấn dữ liệu đều không thành công.",
                detailed_insight=[],
                layout="focus",
                artifacts=[
                    CalloutArtifact(
                        variant="error",
                        message=error_summary,
                    )
                ],
                executed_queries=[
                    {"task_id": a.task_id, "sql": a.sql} for a in artifacts
                ],
                total_execution_time_ms=sum(a.execution_time_ms for a in artifacts),
            )

        # ======================================================================
        # 2. NHỊP 1: LLM SPEC DECISION (Single Hop ~1s)
        # ======================================================================
        artifacts_context = self._format_artifacts_context(artifacts)
        messages = ANALYTICS_PRESENTATION_PROMPT.format_messages(
            question=question,
            goal=analysis_goal or question,
            findings_summary=f"Có {len(successful_artifacts)} truy vấn thành công.",
            artifacts_context=artifacts_context,
        )

        model = self._get_model()
        structured_llm = model.with_structured_output(SynthesisDecision)

        try:
            decision: SynthesisDecision = await structured_llm.ainvoke(messages)
        except Exception as exc:
            logger.exception(
                "Lỗi khi gọi LLM cho ResponseSynthesizer. Kích hoạt fallback dự phòng."
            )
            return self._create_fallback_package(
                question, artifacts, session_id, error_reason=str(exc)
            )

        # ======================================================================
        # 3. NHỊP 2: DETERMINISTIC DATA HYDRATION (Code thuần < 2ms)
        # ======================================================================
        hydrated_items = self._hydrate_artifacts(decision.selected_artifacts, artifacts)

        # Nếu LLM không chọn artifact nào nhưng có dữ liệu, tự động bổ sung Table làm mặc định
        if not hydrated_items and successful_artifacts:
            art = successful_artifacts[0]
            hydrated_items.append(
                TableArtifact(
                    title="Bảng số liệu chi tiết",
                    columns=art.columns or list(art.data[0].keys()),
                    rows=art.data,
                    total_row_count=len(art.data),
                )
            )

        layout = self._determine_layout(hydrated_items)

        return ResponsePackage(
            session_id=session_id,
            direct_answer=decision.direct_answer,
            detailed_insight=decision.detailed_insight,
            layout=layout,  # type: ignore[arg-type]
            artifacts=hydrated_items,
            executed_queries=[{"task_id": a.task_id, "sql": a.sql} for a in artifacts],
            total_execution_time_ms=sum(a.execution_time_ms for a in artifacts),
        )


__all__ = ["ResponseSynthesizer"]
