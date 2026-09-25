"""Unit tests cho Analytics Planner Node (Component 2.2 - TDD).

Kiểm tra:
- Phân rã câu hỏi phân tích phức tạp thành 2-3 tasks tuần tự.
- Xử lý câu hỏi đơn mục tiêu chỉ sinh 1 task.
- Ràng buộc trần ngân sách max_tasks.
- Cơ chế Fallback an toàn khi LLM gặp sự cố API/mạng.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.analytics.planner import generate_analysis_plan
from src.models.artifacts import AnalysisPlan, AnalysisTask


@pytest.mark.asyncio
async def test_planner_complex_question_multi_tasks():
    """Kiểm tra câu hỏi phức tạp phân tích nguyên nhân -> phân rã thành nhiều sub-tasks."""
    question = "Tại sao doanh số ở Châu Âu giảm trong năm 1996 và do quốc gia nào?"

    mock_plan = AnalysisPlan(
        goal="Điều tra sự sụt giảm doanh thu Châu Âu năm 1996",
        hypotheses=["Doanh số giảm ở các quốc gia lớn như Đức hoặc Pháp"],
        tasks=[
            AnalysisTask(
                task_id="task_1",
                description="Tính tổng doanh thu Châu Âu năm 1995 so với 1996",
            ),
            AnalysisTask(
                task_id="task_2",
                description="Phân rã doanh thu theo từng quốc gia tại Châu Âu năm 1995 và 1996",
            ),
            AnalysisTask(
                task_id="task_3",
                description="Xác định nhóm mặt hàng có sản lượng bán giảm mạnh nhất tại quốc gia suy giảm",
            ),
        ],
        max_tasks=3,
    )

    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_plan)
    mock_model.with_structured_output.return_value = mock_structured

    plan = await generate_analysis_plan(
        question=question,
        model=mock_model,
        max_tasks=3,
    )

    assert plan is not None
    assert len(plan.tasks) == 3
    assert plan.tasks[0].task_id == "task_1"
    assert "Châu Âu" in plan.goal
    mock_model.with_structured_output.assert_called_once_with(AnalysisPlan)


@pytest.mark.asyncio
async def test_planner_simple_question_single_task():
    """Kiểm tra câu hỏi đơn giản chỉ hỏi 1 chỉ số -> sinh đúng 1 task duy nhất."""
    question = "Tổng số lượng khách hàng tại thị trường Việt Nam là bao nhiêu?"

    mock_plan = AnalysisPlan(
        goal="Đếm số khách hàng tại Việt Nam",
        tasks=[
            AnalysisTask(
                task_id="task_1",
                description="Truy vấn số lượng khách hàng tại quốc gia VIETNAM",
            )
        ],
        max_tasks=3,
    )

    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_plan)
    mock_model.with_structured_output.return_value = mock_structured

    plan = await generate_analysis_plan(
        question=question,
        model=mock_model,
        max_tasks=3,
    )

    assert len(plan.tasks) == 1
    assert plan.tasks[0].task_id == "task_1"


@pytest.mark.asyncio
async def test_planner_respects_max_tasks_ceiling():
    """Kiểm tra planner cắt giảm số task nếu LLM trả về vượt quá trần max_tasks cho phép."""
    question = "Phân tích biến động chi phí vận chuyển toàn cầu"

    mock_plan = AnalysisPlan(
        goal="Phân tích chi phí",
        tasks=[
            AnalysisTask(task_id="task_1", description="Task 1"),
            AnalysisTask(task_id="task_2", description="Task 2"),
            AnalysisTask(task_id="task_3", description="Task 3"),
            AnalysisTask(task_id="task_4", description="Task 4"),
        ],
        max_tasks=4,  # Mô phỏng LLM sinh 4 tasks
    )

    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_plan)
    mock_model.with_structured_output.return_value = mock_structured

    plan = await generate_analysis_plan(
        question=question,
        model=mock_model,
        max_tasks=2,  # Trần nghiêm ngặt là 2
    )

    assert len(plan.tasks) == 2
    assert plan.max_tasks == 2


@pytest.mark.asyncio
async def test_planner_fallback_on_llm_exception():
    """Kiểm tra cơ chế Graceful Fallback: Khi LLM ném ngoại lệ, tạo plan dự phòng 1 task."""
    question = "Doanh thu quý vừa rồi thế nào?"

    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=RuntimeError("LLM API Timeout"))
    mock_model.with_structured_output.return_value = mock_structured

    plan = await generate_analysis_plan(
        question=question,
        model=mock_model,
        max_tasks=3,
    )

    assert plan is not None
    assert len(plan.tasks) == 1
    assert plan.tasks[0].task_id == "task_1"
    assert plan.goal == question
