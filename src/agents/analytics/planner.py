"""Analytics Planner Node (Component 2.2).

Tiếp nhận câu hỏi người dùng và ngữ cảnh lược đồ TPC-H để sinh ra AnalysisPlan
phân rã thành 1-3 tasks tuần tự có mục tiêu rõ ràng.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import ANALYTICS_PLANNER_PROMPT
from src.config import get_settings
from src.models.artifacts import AnalysisPlan, AnalysisTask
from src.services import get_chat_model

logger = logging.getLogger(__name__)


def _create_fallback_plan(question: str, max_tasks: int = 3) -> AnalysisPlan:
    """Tạo kế hoạch phân tích dự phòng với 1 task đơn mục tiêu khi LLM gặp sự cố."""
    logger.warning(
        "Kích hoạt kế hoạch dự phòng (Fallback AnalysisPlan) cho câu hỏi: %s", question
    )
    return AnalysisPlan(
        goal=question,
        hypotheses=[],
        tasks=[
            AnalysisTask(
                task_id="task_1",
                description=f"Truy vấn số liệu phục vụ trả lời: {question}",
                status="PLANNED",
            )
        ],
        max_tasks=max_tasks,
    )


async def generate_analysis_plan(
    question: str,
    schema_context: str | None = None,
    model: BaseChatModel | None = None,
    max_tasks: int | None = None,
) -> AnalysisPlan:
    """Sinh kế hoạch phân tích có cấu trúc AnalysisPlan từ câu hỏi người dùng.

    Args:
        question: Câu hỏi phân tích của người dùng.
        schema_context: Ngữ cảnh DDL và bảng/cột TPC-H liên quan (nếu có).
        model: LLM ChatModel chỉ định (mặc định Tier 2).
        max_tasks: Giới hạn số lượng task tối đa (mặc định lấy từ cấu hình).

    Returns:
        Instance AnalysisPlan hợp lệ.
    """
    settings = get_settings()
    configured_max_tasks = (
        max_tasks
        if max_tasks is not None
        else getattr(settings, "max_analysis_tasks", 3)
    )
    active_model = model or get_chat_model(settings.tier2_model)

    messages = ANALYTICS_PLANNER_PROMPT.format_messages(
        max_tasks=configured_max_tasks,
        question=question,
        schema_context=schema_context or "Không có (sử dụng 8 bảng TPC-H mặc định)",
    )

    try:
        structured_llm = active_model.with_structured_output(AnalysisPlan)
        plan: Any = await structured_llm.ainvoke(messages)

        if not isinstance(plan, AnalysisPlan) or not plan.tasks:
            logger.warning(
                "LLM không trả về AnalysisPlan hợp lệ. Dùng kế hoạch fallback."
            )
            return _create_fallback_plan(question, max_tasks=configured_max_tasks)

        # Đảm bảo không vượt quá trần max_tasks đã yêu cầu
        if len(plan.tasks) > configured_max_tasks:
            logger.info(
                "Cắt giảm số lượng tasks từ %d xuống trần %d",
                len(plan.tasks),
                configured_max_tasks,
            )
            plan.tasks = plan.tasks[:configured_max_tasks]

        plan.max_tasks = configured_max_tasks

        # Chuẩn hóa task_id nếu cần
        for idx, task in enumerate(plan.tasks):
            if not task.task_id or not task.task_id.startswith("task_"):
                task.task_id = f"task_{idx + 1}"

        return plan

    except Exception:
        logger.exception("Lỗi khi gọi LLM sinh AnalysisPlan")
        return _create_fallback_plan(question, max_tasks=configured_max_tasks)
