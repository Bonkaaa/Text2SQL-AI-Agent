"""Analytics LangGraph Subgraph Builder (Component 2.5).

Xây dựng và biên dịch đồ thị LangGraph điều phối quy trình phân tích dữ liệu đa nhiệm:
START -> planner -> executor -> evidence -> [should_continue?] -> presentation -> END
                                   ^                |
                                   └──── [MORE] ────┘
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.analytics.nodes import (
    evidence_node,
    executor_node,
    planner_node,
    presentation_node,
)
from src.models.state import AnalyticsState

logger = logging.getLogger(__name__)


def should_continue(state: AnalyticsState) -> Literal["executor", "presentation"]:
    """Quyết định điều hướng sau khi hoàn tất bước đánh giá bằng chứng (Evidence Evaluation).

    Returns:
        - "executor": Nếu phát hiện cần thêm dữ liệu và còn task PLANNED trong ngân sách.
        - "presentation": Nếu đã đủ bằng chứng, đã hết ngân sách hoặc truy vấn thất bại.
    """
    evaluation = state.get("current_evaluation")
    plan = state.get("plan")

    if evaluation is None or plan is None:
        logger.info("Chưa có evaluation hoặc plan -> Chuyển sang presentation.")
        return "presentation"

    # Nếu đánh giá xác định đã đủ bằng chứng
    if evaluation.has_enough_evidence:
        logger.info(
            "Evidence Analyzer xác nhận đã đủ dữ liệu -> Chuyển sang presentation."
        )
        return "presentation"

    # Nếu đánh giá xác định cần thêm bằng chứng
    pending_tasks = [t for t in plan.tasks if t.status == "PLANNED"]
    if pending_tasks:
        logger.info(
            "Phát hiện %d nhiệm vụ bổ sung cần thực thi -> Quay lại executor node.",
            len(pending_tasks),
        )
        return "executor"

    logger.info("Không còn nhiệm vụ nào có thể thực thi -> Chuyển sang presentation.")
    return "presentation"


def build_analytics_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Xây dựng và biên dịch StateGraph cho Analytics Subagent.

    Args:
        checkpointer: Đối tượng lưu trữ trạng thái phiên (MemorySaver, PostgresSaver...).

    Returns:
        Instance CompiledStateGraph sẵn sàng thực thi (ainvoke / invoke).
    """
    workflow = StateGraph(AnalyticsState)

    # 1. Khai báo các nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("evidence", evidence_node)
    workflow.add_node("presentation", presentation_node)

    # 2. Khai báo các cạnh chuyển trạng thái (Edges)
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "evidence")

    # 3. Cạnh điều kiện từ evidence_node
    workflow.add_conditional_edges(
        "evidence",
        should_continue,
        {
            "executor": "executor",
            "presentation": "presentation",
        },
    )

    workflow.add_edge("presentation", END)

    # 4. Biên dịch đồ thị
    return workflow.compile(checkpointer=checkpointer)
