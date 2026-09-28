"""Analytics LangGraph Subgraph Builder (Component 2.5).

Xây dựng và biên dịch đồ thị LangGraph điều phối quy trình phân tích dữ liệu đa nhiệm:
START -> planner -> executor -> evidence -> [should_continue?] -> presentation -> END
                                   ^                |
                                   └──── [MORE] ────┘
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any, Literal

from deepagents import CompiledSubAgent
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.analytics.nodes import (
    evidence_node,
    executor_node,
    planner_node,
    presentation_node,
)
from src.models.rbac import UserContext, UserRole
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


def create_analytics_subagent_runnable(
    graph: CompiledStateGraph | None = None,
) -> RunnableLambda:
    """Tạo RunnableLambda bọc LangGraph Analytics Subgraph.

    deepagents yêu cầu SubAgent trả về state có chứa trường 'messages' để trích xuất nội dung
    gửi ngược lại cho parent agent dưới dạng ToolMessage.
    """
    active_graph = graph or build_analytics_graph()

    async def _async_runner(state: dict[str, Any]) -> dict[str, Any]:
        # 1. Trích xuất câu hỏi từ state hoặc từ messages
        question = state.get("question")
        if not question:
            messages = state.get("messages", [])
            for msg in reversed(messages):
                content = getattr(msg, "content", "")
                if content:
                    question = str(content)
                    break
        if not question:
            question = state.get("description", "")

        user_context = state.get("user_context")
        session_id = state.get("session_id", "default_session")

        if not user_context:
            user_context = UserContext(
                user_id="default_analyst",
                session_id=session_id,
                role=UserRole.ANALYST,
            )

        input_data = {
            "question": question or "",
            "user_context": user_context,
            "session_id": session_id,
            "artifacts": [],
        }

        output = await active_graph.ainvoke(input_data)

        # 2. Định dạng thông điệp tóm tắt gửi về cho Supervisor
        response_package = output.get("response_package")
        insight = output.get("insight")
        if response_package and getattr(response_package, "direct_answer", None):
            summary = response_package.direct_answer
        elif insight:
            summary = str(insight)
        else:
            summary = "Hoàn tất phân tích dữ liệu chuyên sâu."

        # 3. Trích xuất primary SQL và data cho backward compatibility
        artifacts = output.get("artifacts", []) or []
        primary_sql = None
        primary_data = None
        primary_columns = None
        for a in artifacts:
            if getattr(a, "status", "") == "SUCCESS":
                primary_sql = getattr(a, "sql", None)
                primary_data = getattr(a, "data", None)
                primary_columns = getattr(a, "columns", None)
                break

        output_artifacts_dump: list[dict[str, Any]] = []
        if response_package and hasattr(response_package, "artifacts"):
            for item in response_package.artifacts:
                if hasattr(item, "model_dump"):
                    output_artifacts_dump.append(item.model_dump())
                elif isinstance(item, dict):
                    output_artifacts_dump.append(item)

        return {
            **state,
            "messages": [AIMessage(content=summary)],
            "response_package": response_package.model_dump()
            if response_package and hasattr(response_package, "model_dump")
            else response_package,
            "output_artifacts": output_artifacts_dump,
            "artifacts": artifacts,
            "plan": output.get("plan"),
            "insight": summary,
            "visualization": output.get("visualization"),
            "sql": primary_sql,
            "data": primary_data,
            "columns": primary_columns,
            "status": output.get("status", "COMPLETED"),
        }

    def _sync_runner(state: dict[str, Any]) -> dict[str, Any]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(_async_runner(state))).result()
        else:
            return asyncio.run(_async_runner(state))

    return RunnableLambda(func=_sync_runner, afunc=_async_runner)


def get_analytics_subagent(
    graph: CompiledStateGraph | None = None,
) -> CompiledSubAgent:
    """Tạo cấu hình CompiledSubAgent cho Analytics Subgraph theo chuẩn deepagents.

    Đóng gói StateGraph phân tích v4 (Phase 2 & 3) thành một CompiledSubAgent mà
    Deep Agent Master Supervisor có thể gọi qua công cụ task('analytics-subagent', ...).
    """
    runnable = create_analytics_subagent_runnable(graph=graph)
    return {
        "name": "analytics-subagent",
        "description": (
            "Subagent phân tích dữ liệu thông minh toàn trình (CompiledSubAgent bọc LangGraph Analytics Subgraph), "
            "tự động lập kế hoạch phân tích (AnalysisPlan), điều phối các truy vấn SQL qua chốt chặn an toàn, "
            "đánh giá tính đầy đủ của dữ liệu (Evidence Analyzer) và tổng hợp trực quan hóa đa chiều (ResponsePackage)."
        ),
        "runnable": runnable,
        "mode": "isolated",
    }
