"""Evidence Analyzer Node (Component 2.4).

Đánh giá tính đầy đủ của các bằng chứng (QueryArtifact) thu thập được so với
câu hỏi người dùng và mục tiêu kế hoạch (AnalysisPlan). Quyết định xem đã đủ dữ liệu
để tổng hợp câu trả lời hay cần sinh thêm nhiệm vụ điều tra sâu hơn (drill-down).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import EVIDENCE_ANALYZER_PROMPT
from src.config import get_settings
from src.models.artifacts import (
    AnalysisPlan,
    EvidenceEvaluation,
    QueryArtifact,
)
from src.services import get_chat_model

logger = logging.getLogger(__name__)

__all__ = ["EvidenceEvaluation", "analyze_collected_evidence"]


async def analyze_collected_evidence(
    question: str,
    plan: AnalysisPlan,
    artifacts: list[QueryArtifact],
    model: BaseChatModel | None = None,
) -> EvidenceEvaluation:
    """Đánh giá tính đầy đủ của bằng chứng thu thập được so với câu hỏi và mục tiêu kế hoạch.

    Args:
        question: Câu hỏi phân tích ban đầu của người dùng.
        plan: Kế hoạch phân tích hiện tại (AnalysisPlan).
        artifacts: Danh sách kết quả truy vấn đã thực thi (QueryArtifact).
        model: LLM ChatModel chỉ định (mặc định Tier 2).

    Returns:
        Instance EvidenceEvaluation.
    """
    # 1. Fast path 1 (Zero-Token): Khi đã đạt hoặc vượt ngưỡng ngân sách max_tasks
    if len(plan.tasks) >= plan.max_tasks:
        logger.info(
            "Đã chạm trần ngân sách phân tích (%d/%d tasks). Dừng thu thập bằng chứng (Zero-Token).",
            len(plan.tasks),
            plan.max_tasks,
        )
        return EvidenceEvaluation(
            has_enough_evidence=True,
            findings_summary="Đã đạt trần ngân sách câu hỏi (max_tasks). Tiến hành tổng hợp kết quả hiện có.",
            next_task=None,
            reasoning="Budget limit reached.",
        )

    # 2. Fast path 2: Toàn bộ artifacts đều thất bại
    if artifacts and all(a.status != "SUCCESS" for a in artifacts):
        logger.warning(
            "Toàn bộ truy vấn thu thập dữ liệu đều thất bại. Kích hoạt graceful termination."
        )
        return EvidenceEvaluation(
            has_enough_evidence=True,
            findings_summary="Toàn bộ truy vấn thu thập dữ liệu đều thất bại. Không thể thu thập thêm dữ liệu.",
            next_task=None,
            reasoning="All query attempts failed.",
        )

    # 3. Chuẩn bị gọi LLM để đánh giá dữ liệu
    settings = get_settings()
    active_model = model or get_chat_model(settings.tier2_model)

    artifacts_context_parts = []
    for art in artifacts:
        sample_data_preview = ""
        if art.data:
            sample_data_preview = f" (Sample: {art.data[:3]})"
        artifacts_context_parts.append(
            f"- Task {art.task_id} [{art.status}]: SQL: {art.sql} | Rows: {art.row_count}{sample_data_preview}"
            + (f" | Error: {art.error_message}" if art.error_message else "")
        )
    artifacts_context = (
        "\n".join(artifacts_context_parts)
        if artifacts_context_parts
        else "Chưa có kết quả truy vấn nào."
    )

    remaining_budget = max(0, plan.max_tasks - len(plan.tasks))
    messages = EVIDENCE_ANALYZER_PROMPT.format_messages(
        question=question,
        goal=plan.goal,
        remaining_budget=remaining_budget,
        artifacts_context=artifacts_context,
    )

    try:
        structured_llm = active_model.with_structured_output(EvidenceEvaluation)
        eval_result: Any = await structured_llm.ainvoke(messages)

        if not isinstance(eval_result, EvidenceEvaluation):
            logger.warning(
                "LLM không trả về EvidenceEvaluation hợp lệ. Fallback kết thúc thu thập."
            )
            return EvidenceEvaluation(
                has_enough_evidence=True,
                findings_summary="Hoàn thành thu thập bằng chứng.",
                next_task=None,
                reasoning="Invalid structured output from LLM.",
            )

        # Chặn nếu LLM yêu cầu thêm task nhưng ngân sách đã hết
        if not eval_result.has_enough_evidence and eval_result.next_task:
            if len(plan.tasks) >= plan.max_tasks:
                logger.info(
                    "LLM đề xuất task mới nhưng đã hết ngân sách. Buộc kết thúc."
                )
                eval_result.has_enough_evidence = True
                eval_result.next_task = None
            else:
                if (
                    not eval_result.next_task.task_id
                    or not eval_result.next_task.task_id.startswith("task_")
                ):
                    eval_result.next_task.task_id = f"task_{len(plan.tasks) + 1}"

        return eval_result

    except Exception as e:
        logger.exception("Lỗi khi đánh giá bằng chứng qua LLM")
        return EvidenceEvaluation(
            has_enough_evidence=True,
            findings_summary="Không thể đánh giá thêm bằng chứng do lỗi hệ thống. Tiến hành tổng hợp dữ liệu sẵn có.",
            next_task=None,
            reasoning=f"Fallback due to error: {e}",
        )
