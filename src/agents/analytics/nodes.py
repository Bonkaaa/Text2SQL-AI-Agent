"""Các Node thực thi cho Analytics LangGraph Subgraph (Component 2.5).

Tách biệt các node chức năng:
- planner_node: Lập kế hoạch phân tích AnalysisPlan từ câu hỏi người dùng.
- executor_node: Thực thi tuần tự các AnalysisTask chưa chạy qua Control Pipeline.
- evidence_node: Đánh giá tính đầy đủ của dữ liệu thu thập qua Evidence Analyzer.
- presentation_node: Tổng hợp insight kinh doanh và đóng gói kết quả đầu ra.
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.analytics.evidence_analyzer import analyze_collected_evidence
from src.agents.analytics.planner import generate_analysis_plan
from src.agents.analytics.response_synthesizer import ResponseSynthesizer
from src.agents.analytics.task_executor import aexecute_analysis_task
from src.models.artifacts import (
    AnalysisPlan,
    ChartArtifact,
    QueryArtifact,
)
from src.models.state import AnalyticsState

logger = logging.getLogger(__name__)


async def planner_node(state: AnalyticsState) -> dict[str, Any]:
    """Node lập kế hoạch phân tích ban đầu (Component 2.2)."""
    question = state.get("question", "")
    existing_plan = state.get("plan")

    if existing_plan is not None:
        return {}

    logger.info("Khởi chạy Planner Node cho câu hỏi: %s", question)
    plan = await generate_analysis_plan(question=question)
    return {
        "plan": plan,
        "artifacts": state.get("artifacts", []) or [],
    }


async def executor_node(state: AnalyticsState) -> dict[str, Any]:
    """Node thực thi tuần tự các AnalysisTask đang ở trạng thái PLANNED (Component 2.3)."""
    plan: AnalysisPlan | None = state.get("plan")
    user_context = state.get("user_context")
    current_artifacts: list[QueryArtifact] = list(state.get("artifacts", []) or [])

    if plan is None or user_context is None:
        logger.error("Thiếu plan hoặc user_context trong AnalyticsState")
        return {"artifacts": current_artifacts}

    # Tìm các tasks cần thực thi
    pending_tasks = [t for t in plan.tasks if t.status == "PLANNED"]
    logger.info(
        "Executor Node: Tìm thấy %d nhiệm vụ đang chờ thực thi.", len(pending_tasks)
    )

    for task in pending_tasks:
        logger.info(
            "Bắt đầu thực thi nhiệm vụ: %s (%s)", task.task_id, task.description
        )
        artifact = await aexecute_analysis_task(
            task=task,
            user_context=user_context,
            prior_artifacts=current_artifacts,
        )
        current_artifacts.append(artifact)
        task.query_artifact = artifact
        task.status = "COMPLETED" if artifact.status == "SUCCESS" else "FAILED"

    return {
        "plan": plan,
        "artifacts": current_artifacts,
    }


async def evidence_node(state: AnalyticsState) -> dict[str, Any]:
    """Node đánh giá mức độ đầy đủ của dữ liệu thu thập (Component 2.4)."""
    question = state.get("question", "")
    plan = state.get("plan")
    artifacts = state.get("artifacts", []) or []

    if plan is None:
        logger.warning("Không tìm thấy AnalysisPlan trong state")
        return {}

    logger.info(
        "Evidence Node: Đang đánh giá %d artifacts thu thập được cho kế hoạch '%s'",
        len(artifacts),
        plan.goal,
    )

    evaluation = await analyze_collected_evidence(
        question=question,
        plan=plan,
        artifacts=artifacts,
    )

    # Nếu đánh giá cần thêm nhiệm vụ và còn ngân sách, cập nhật vào plan
    if not evaluation.has_enough_evidence and evaluation.next_task is not None:
        if len(plan.tasks) < plan.max_tasks:
            logger.info(
                "Đề xuất thêm nhiệm vụ mới: %s - %s",
                evaluation.next_task.task_id,
                evaluation.next_task.description,
            )
            plan.tasks.append(evaluation.next_task)
        else:
            logger.info(
                "Đã chạm trần ngân sách max_tasks (%d). Buộc dừng thu thập.",
                plan.max_tasks,
            )
            evaluation.has_enough_evidence = True
            evaluation.next_task = None

    return {
        "current_evaluation": evaluation,
        "plan": plan,
    }


async def presentation_node(state: AnalyticsState) -> dict[str, Any]:
    """Node tổng hợp phản hồi phân tích kinh doanh cuối cùng (Response Synthesizer - Phase 3)."""
    artifacts = state.get("artifacts", []) or []
    question = state.get("question", "")
    session_id = state.get("session_id", "default")
    plan = state.get("plan")
    analysis_goal = plan.goal if plan else question

    logger.info("Khởi chạy Presentation Node (ResponseSynthesizer) cho: %s", question)
    synthesizer = ResponseSynthesizer()
    response_package = await synthesizer.synthesize(
        question=question,
        artifacts=artifacts,
        analysis_goal=analysis_goal,
        session_id=session_id,
    )

    # Trích xuất primary chart nếu có để giữ tương thích ngược với state.get("visualization")
    primary_viz = None
    for art in response_package.artifacts:
        if isinstance(art, ChartArtifact):
            primary_viz = {
                "chart_type": art.chart_type,
                "title": art.title,
                "x_key": art.x_key,
                "y_keys": art.y_keys,
                "series_labels": art.series_labels,
                "data": art.data,
            }
            break

    has_success = any(a.status == "SUCCESS" for a in artifacts)
    status = "COMPLETED" if has_success else "FAILED"

    return {
        "status": status,
        "insight": response_package.direct_answer,
        "visualization": primary_viz or state.get("visualization"),
        "response_package": response_package,
        "error_message": None if has_success else response_package.direct_answer,
    }
