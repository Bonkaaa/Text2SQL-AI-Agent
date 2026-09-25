"""Unit tests cho Evidence Analyzer Node (Component 2.4 - TDD).

Kiểm tra:
- Trường hợp đủ bằng chứng để trả lời câu hỏi bài toán (has_enough_evidence=True).
- Trường hợp cần thêm bằng chứng khi còn trong ngân sách (has_enough_evidence=False, next_task).
- Tối ưu Zero-Token: Khi đã chạm trần ngân sách max_tasks, ngắt ngay mà không gọi LLM.
- Chốt chặn Fail-Safe khi toàn bộ query đều lỗi.
- Cơ chế Fallback an toàn khi LLM gặp sự cố.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.analytics.evidence_analyzer import (
    EvidenceEvaluation,
    analyze_collected_evidence,
)
from src.models.artifacts import AnalysisPlan, AnalysisTask, QueryArtifact


@pytest.mark.asyncio
async def test_evidence_analyzer_enough_evidence():
    """Kiểm tra khi bằng chứng đã đủ, trả về has_enough_evidence=True và không có next_task."""
    t1 = AnalysisTask(task_id="task_1", description="Doanh thu Q3", status="COMPLETED")
    plan = AnalysisPlan(goal="Phân tích doanh thu", tasks=[t1], max_tasks=3)

    artifact = QueryArtifact(
        task_id="task_1",
        sql="SELECT sum(revenue) FROM orders",
        status="SUCCESS",
        data=[{"sum": 1000000}],
        row_count=1,
    )

    mock_eval = EvidenceEvaluation(
        has_enough_evidence=True,
        findings_summary="Doanh thu đạt 1,000,000 USD, đã đủ cơ sở trả lời.",
        next_task=None,
        reasoning="Dữ liệu đáp ứng đầy đủ yêu cầu",
    )

    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_eval)
    mock_model.with_structured_output.return_value = mock_structured

    result = await analyze_collected_evidence(
        question="Doanh thu đạt bao nhiêu?",
        plan=plan,
        artifacts=[artifact],
        model=mock_model,
    )

    assert result.has_enough_evidence is True
    assert result.next_task is None
    assert "1,000,000" in result.findings_summary
    mock_model.with_structured_output.assert_called_once()


@pytest.mark.asyncio
async def test_evidence_analyzer_needs_more_evidence_within_budget():
    """Kiểm tra khi phát hiện cần thêm số liệu và còn trong ngân sách -> sinh next_task."""
    t1 = AnalysisTask(
        task_id="task_1", description="Tổng doanh thu", status="COMPLETED"
    )
    plan = AnalysisPlan(goal="Phân tích nguyên nhân giảm", tasks=[t1], max_tasks=3)

    artifact = QueryArtifact(
        task_id="task_1",
        sql="SELECT sum(revenue) FROM orders",
        status="SUCCESS",
        data=[{"sum": 800000}],
        row_count=1,
    )

    next_task = AnalysisTask(
        task_id="task_2",
        description="Phân tích doanh thu theo từng nhóm khách hàng",
        status="PLANNED",
    )

    mock_eval = EvidenceEvaluation(
        has_enough_evidence=False,
        findings_summary="Doanh thu giảm nhưng chưa rõ nhóm khách hàng nào sụt giảm nhiều nhất.",
        next_task=next_task,
        reasoning="Cần đào sâu theo phân khúc khách hàng",
    )

    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_eval)
    mock_model.with_structured_output.return_value = mock_structured

    result = await analyze_collected_evidence(
        question="Tại sao doanh thu giảm và do nhóm khách hàng nào?",
        plan=plan,
        artifacts=[artifact],
        model=mock_model,
    )

    assert result.has_enough_evidence is False
    assert result.next_task is not None
    assert result.next_task.task_id == "task_2"


@pytest.mark.asyncio
async def test_evidence_analyzer_budget_exhausted_zero_token():
    """Kiểm tra khi đã đạt max_tasks, hệ thống lập tức ngắt mà KHÔNG gọi LLM (Zero-Token)."""
    tasks = [
        AnalysisTask(task_id="task_1", description="Task 1", status="COMPLETED"),
        AnalysisTask(task_id="task_2", description="Task 2", status="COMPLETED"),
        AnalysisTask(task_id="task_3", description="Task 3", status="COMPLETED"),
    ]
    plan = AnalysisPlan(goal="Test budget", tasks=tasks, max_tasks=3)

    mock_model = MagicMock()

    result = await analyze_collected_evidence(
        question="Câu hỏi phân tích",
        plan=plan,
        artifacts=[],
        model=mock_model,
    )

    # Đảm bảo kết quả là đã đủ (buộc ngắt)
    assert result.has_enough_evidence is True
    assert result.next_task is None
    # Đảm bảo KHÔNG gọi LLM
    mock_model.with_structured_output.assert_not_called()


@pytest.mark.asyncio
async def test_evidence_analyzer_all_failed_artifacts():
    """Kiểm tra khi toàn bộ artifacts đều thất bại, hệ thống tự động ngắt để chuyển sang graceful error."""
    t1 = AnalysisTask(task_id="task_1", description="Task lỗi", status="FAILED")
    plan = AnalysisPlan(goal="Test failure", tasks=[t1], max_tasks=3)

    failed_artifact = QueryArtifact(
        task_id="task_1",
        sql="SELECT 1",
        status="BLOCKED_AST",
        error_message="Lỗi cú pháp",
    )

    mock_model = MagicMock()

    result = await analyze_collected_evidence(
        question="Câu hỏi phân tích",
        plan=plan,
        artifacts=[failed_artifact],
        model=mock_model,
    )

    assert result.has_enough_evidence is True
    assert result.next_task is None
    assert (
        "thất bại" in result.findings_summary.lower()
        or "không thành công" in result.findings_summary.lower()
    )
    mock_model.with_structured_output.assert_not_called()


@pytest.mark.asyncio
async def test_evidence_analyzer_fallback_on_llm_exception():
    """Kiểm tra cơ chế Graceful Fallback khi LLM ném ngoại lệ."""
    t1 = AnalysisTask(task_id="task_1", description="Task 1", status="COMPLETED")
    plan = AnalysisPlan(goal="Test exception", tasks=[t1], max_tasks=3)

    artifact = QueryArtifact(
        task_id="task_1",
        sql="SELECT 1",
        status="SUCCESS",
        data=[{"1": 1}],
    )

    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=RuntimeError("LLM API Timeout"))
    mock_model.with_structured_output.return_value = mock_structured

    result = await analyze_collected_evidence(
        question="Test",
        plan=plan,
        artifacts=[artifact],
        model=mock_model,
    )

    assert result.has_enough_evidence is True
    assert result.next_task is None
