"""Unit tests cho Analytics LangGraph Subgraph (Component 2.5 - TDD).

Kiểm tra:
- Luồng truy vấn đơn lẻ (Single query flow): Planner -> Executor -> Evidence Analyzer -> Presentation.
- Luồng lặp đa nhiệm (Multi-query loop): Phát hiện thiếu số liệu -> Loop lại thực thi task bổ sung -> Kết thúc.
- Chặn trần ngân sách (Budget ceiling termination): Ngắt vòng lặp khi chạm ngưỡng max_tasks.
- Xử lý lỗi graceful (All tasks failed): Thoát an toàn và gán status='FAILED'.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.analytics.graph import build_analytics_graph
from src.models.artifacts import (
    AnalysisPlan,
    AnalysisTask,
    EvidenceEvaluation,
    QueryArtifact,
)
from src.models.rbac import UserContext, UserRole
from src.models.state import AnalyticsState


@pytest.fixture
def mock_user_context() -> UserContext:
    return UserContext(
        user_id="analyst_test",
        session_id="session_graph_test",
        role=UserRole.ANALYST,
    )


@pytest.mark.asyncio
async def test_analytics_graph_single_query_flow(mock_user_context):
    """Kiểm tra câu hỏi đơn: Planner sinh 1 task -> Thực thi -> Đủ bằng chứng -> Presentation."""
    task_1 = AnalysisTask(
        task_id="task_1", description="Tính tổng doanh thu", status="PLANNED"
    )
    initial_plan = AnalysisPlan(goal="Tổng doanh thu", tasks=[task_1], max_tasks=3)

    mock_artifact = QueryArtifact(
        task_id="task_1",
        sql="SELECT sum(revenue) FROM orders",
        status="SUCCESS",
        data=[{"sum": 1000000}],
        row_count=1,
    )

    mock_eval = EvidenceEvaluation(
        has_enough_evidence=True,
        findings_summary="Doanh thu đạt 1,000,000 USD",
        next_task=None,
        reasoning="Đã đủ số liệu",
    )

    with (
        patch(
            "src.agents.analytics.nodes.generate_analysis_plan", new_callable=AsyncMock
        ) as mock_planner,
        patch(
            "src.agents.analytics.nodes.aexecute_analysis_task", new_callable=AsyncMock
        ) as mock_executor,
        patch(
            "src.agents.analytics.nodes.analyze_collected_evidence",
            new_callable=AsyncMock,
        ) as mock_analyzer,
    ):
        mock_planner.return_value = initial_plan
        mock_executor.return_value = mock_artifact
        mock_analyzer.return_value = mock_eval

        graph = build_analytics_graph()
        initial_state: AnalyticsState = {
            "question": "Tổng doanh thu là bao nhiêu?",
            "user_context": mock_user_context,
            "session_id": mock_user_context.session_id,
            "plan": None,
            "artifacts": [],
            "current_evaluation": None,
            "insight": None,
            "visualization": None,
            "status": "COMPLETED",
            "error_message": None,
        }

        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == "COMPLETED"
        assert len(final_state["artifacts"]) == 1
        assert final_state["artifacts"][0].status == "SUCCESS"
        assert final_state["insight"] is not None
        assert mock_planner.await_count == 1
        assert mock_executor.await_count == 1
        assert mock_analyzer.await_count == 1


@pytest.mark.asyncio
async def test_analytics_graph_multi_query_loop(mock_user_context):
    """Kiểm tra luồng lặp đa nhiệm: Task 1 -> Chưa đủ -> Sinh Task 2 -> Thực thi -> Đủ bằng chứng."""
    task_1 = AnalysisTask(
        task_id="task_1", description="Doanh thu Q3", status="PLANNED"
    )
    initial_plan = AnalysisPlan(goal="Phân tích sụt giảm", tasks=[task_1], max_tasks=3)

    art_1 = QueryArtifact(
        task_id="task_1",
        sql="SELECT sum(revenue) FROM orders WHERE q3",
        status="SUCCESS",
        data=[{"sum": 800000}],
        row_count=1,
    )
    art_2 = QueryArtifact(
        task_id="task_2",
        sql="SELECT c_mktsegment, sum(revenue) FROM orders JOIN customer GROUP BY 1",
        status="SUCCESS",
        data=[{"c_mktsegment": "BUILDING", "sum": 300000}],
        row_count=1,
    )

    task_2 = AnalysisTask(
        task_id="task_2", description="Phân bổ theo ngành", status="PLANNED"
    )

    eval_1 = EvidenceEvaluation(
        has_enough_evidence=False,
        findings_summary="Doanh thu sụt giảm, cần phân tích theo nhóm khách hàng.",
        next_task=task_2,
        reasoning="Cần đào sâu phân khúc",
    )
    eval_2 = EvidenceEvaluation(
        has_enough_evidence=True,
        findings_summary="Nhóm BUILDING sụt giảm mạnh nhất.",
        next_task=None,
        reasoning="Đã tìm ra nguyên nhân",
    )

    with (
        patch(
            "src.agents.analytics.nodes.generate_analysis_plan", new_callable=AsyncMock
        ) as mock_planner,
        patch(
            "src.agents.analytics.nodes.aexecute_analysis_task", new_callable=AsyncMock
        ) as mock_executor,
        patch(
            "src.agents.analytics.nodes.analyze_collected_evidence",
            new_callable=AsyncMock,
        ) as mock_analyzer,
    ):
        mock_planner.return_value = initial_plan
        mock_executor.side_effect = [art_1, art_2]
        mock_analyzer.side_effect = [eval_1, eval_2]

        graph = build_analytics_graph()
        initial_state: AnalyticsState = {
            "question": "Tại sao doanh số Q3 sụt giảm?",
            "user_context": mock_user_context,
            "session_id": mock_user_context.session_id,
            "plan": None,
            "artifacts": [],
            "current_evaluation": None,
            "insight": None,
            "visualization": None,
            "status": "COMPLETED",
            "error_message": None,
        }

        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == "COMPLETED"
        assert len(final_state["artifacts"]) == 2
        assert mock_executor.await_count == 2
        assert mock_analyzer.await_count == 2


@pytest.mark.asyncio
async def test_analytics_graph_budget_ceiling_termination(mock_user_context):
    """Kiểm tra khi chạm ngưỡng trần max_tasks, đồ thị phải ngắt vòng lặp và chuyển sang presentation."""
    t1 = AnalysisTask(task_id="task_1", description="Task 1", status="PLANNED")
    t2 = AnalysisTask(task_id="task_2", description="Task 2", status="PLANNED")
    plan = AnalysisPlan(goal="Test budget ceiling", tasks=[t1, t2], max_tasks=2)

    art1 = QueryArtifact(task_id="task_1", sql="SELECT 1", status="SUCCESS")
    art2 = QueryArtifact(task_id="task_2", sql="SELECT 2", status="SUCCESS")

    eval_result = EvidenceEvaluation(
        has_enough_evidence=True,
        findings_summary="Đã chạm trần 2 tasks",
        next_task=None,
    )

    with (
        patch(
            "src.agents.analytics.nodes.generate_analysis_plan", new_callable=AsyncMock
        ) as mock_planner,
        patch(
            "src.agents.analytics.nodes.aexecute_analysis_task", new_callable=AsyncMock
        ) as mock_executor,
        patch(
            "src.agents.analytics.nodes.analyze_collected_evidence",
            new_callable=AsyncMock,
        ) as mock_analyzer,
    ):
        mock_planner.return_value = plan
        mock_executor.side_effect = [art1, art2]
        mock_analyzer.return_value = eval_result

        graph = build_analytics_graph()
        initial_state: AnalyticsState = {
            "question": "Câu hỏi test trần",
            "user_context": mock_user_context,
            "session_id": mock_user_context.session_id,
            "plan": None,
            "artifacts": [],
            "current_evaluation": None,
            "insight": None,
            "visualization": None,
            "status": "COMPLETED",
            "error_message": None,
        }

        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == "COMPLETED"
        assert len(final_state["artifacts"]) == 2
        assert mock_executor.await_count == 2


@pytest.mark.asyncio
async def test_analytics_graph_all_tasks_failed_graceful(mock_user_context):
    """Kiểm tra khi toàn bộ query đều thất bại, đồ thị gán status='FAILED' và thoát graceful."""
    t1 = AnalysisTask(task_id="task_1", description="Task lỗi", status="PLANNED")
    plan = AnalysisPlan(goal="Test failure", tasks=[t1], max_tasks=3)

    art_fail = QueryArtifact(
        task_id="task_1",
        sql="SELECT * FROM table_khong_ton_tai",
        status="DB_ERROR",
        error_message="Table not found",
    )

    eval_fail = EvidenceEvaluation(
        has_enough_evidence=True,
        findings_summary="Toàn bộ truy vấn thất bại",
        next_task=None,
    )

    with (
        patch(
            "src.agents.analytics.nodes.generate_analysis_plan", new_callable=AsyncMock
        ) as mock_planner,
        patch(
            "src.agents.analytics.nodes.aexecute_analysis_task", new_callable=AsyncMock
        ) as mock_executor,
        patch(
            "src.agents.analytics.nodes.analyze_collected_evidence",
            new_callable=AsyncMock,
        ) as mock_analyzer,
    ):
        mock_planner.return_value = plan
        mock_executor.return_value = art_fail
        mock_analyzer.return_value = eval_fail

        graph = build_analytics_graph()
        initial_state: AnalyticsState = {
            "question": "Câu hỏi lỗi",
            "user_context": mock_user_context,
            "session_id": mock_user_context.session_id,
            "plan": None,
            "artifacts": [],
            "current_evaluation": None,
            "insight": None,
            "visualization": None,
            "status": "COMPLETED",
            "error_message": None,
        }

        final_state = await graph.ainvoke(initial_state)

        assert final_state["status"] == "FAILED"
        assert len(final_state["artifacts"]) == 1
        assert final_state["artifacts"][0].status == "DB_ERROR"
        assert (
            "thất bại" in final_state["insight"].lower()
            or "không thành công" in final_state["insight"].lower()
        )
