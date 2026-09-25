"""Unit tests cho AnalysisPlan, AnalysisTask, EvidenceEvaluation và AnalyticsResult (Component 2.1 - TDD)."""

import pytest
from pydantic import ValidationError

from src.models.artifacts import (
    AnalysisPlan,
    AnalysisTask,
    AnalyticsResult,
    EvidenceEvaluation,
    QueryArtifact,
)


def test_analysis_task_lifecycle():
    """Kiểm tra khởi tạo AnalysisTask, các trạng thái hợp lệ và gán QueryArtifact."""
    task = AnalysisTask(
        task_id="t1",
        description="Tính doanh thu Châu Âu năm 1995 vs 1996",
    )
    assert task.task_id == "t1"
    assert task.status == "PLANNED"
    assert task.depends_on == []
    assert task.query_artifact is None
    assert task.retry_count == 0

    # Chuyển trạng thái
    task.status = "EXECUTING"
    assert task.status == "EXECUTING"

    # Gán QueryArtifact khi hoàn tất
    artifact = QueryArtifact(
        task_id="t1",
        sql="SELECT sum(l_extendedprice) FROM lineitem",
        status="SUCCESS",
        data=[{"sum": 500000}],
        columns=["sum"],
        row_count=1,
    )
    task.query_artifact = artifact
    task.status = "COMPLETED"
    assert task.status == "COMPLETED"
    assert task.query_artifact.row_count == 1


def test_analysis_plan_budget_ceiling():
    """Kiểm tra ràng buộc trần ngân sách max_tasks (mặc định 3)."""
    tasks_valid = [
        AnalysisTask(task_id="t1", description="Task 1"),
        AnalysisTask(task_id="t2", description="Task 2"),
        AnalysisTask(task_id="t3", description="Task 3"),
    ]

    # Hợp lệ với 3 tasks
    plan = AnalysisPlan(
        goal="Phân tích tăng trưởng",
        tasks=tasks_valid,
        max_tasks=3,
    )
    assert len(plan.tasks) == 3

    # Vượt quá trần ngân sách (4 tasks) phải raise ValidationError
    tasks_invalid = tasks_valid + [AnalysisTask(task_id="t4", description="Task 4")]
    with pytest.raises(ValidationError) as exc_info:
        AnalysisPlan(
            goal="Phân tích quá ngân sách",
            tasks=tasks_invalid,
            max_tasks=3,
        )
    assert "vượt quá trần cho phép" in str(exc_info.value)


def test_analysis_plan_navigation_and_progress():
    """Kiểm tra điều hướng task hiện tại và kiểm tra hoàn thành kế hoạch."""
    t1 = AnalysisTask(task_id="t1", description="Task 1")
    t2 = AnalysisTask(task_id="t2", description="Task 2")
    plan = AnalysisPlan(goal="Test Navigation", tasks=[t1, t2])

    assert plan.current_task.task_id == "t1"
    assert not plan.is_completed

    # Advance sang task 2
    plan.advance()
    assert plan.current_task.task_id == "t2"

    # Advance vượt quá số tasks
    plan.advance()
    assert plan.current_task is None


def test_analysis_plan_complete_and_fail_task():
    """Kiểm tra hàm helper complete_current_task và fail_current_task."""
    t1 = AnalysisTask(task_id="t1", description="Task 1")
    plan = AnalysisPlan(goal="Test Helpers", tasks=[t1])

    art = QueryArtifact(task_id="t1", sql="SELECT 1", status="SUCCESS")
    plan.complete_current_task(artifact=art, summary_update="Tìm thấy dữ liệu cơ bản")

    assert t1.status == "COMPLETED"
    assert t1.query_artifact == art
    assert plan.evidence_summary == "Tìm thấy dữ liệu cơ bản"
    assert plan.is_completed

    # Test fail_current_task trên task mới
    t2 = AnalysisTask(task_id="t2", description="Task 2")
    plan2 = AnalysisPlan(goal="Test Fail", tasks=[t2])
    plan2.fail_current_task(error_message="Lỗi AST")

    assert t2.status == "FAILED"
    assert t2.retry_count == 1
    assert plan2.is_completed


def test_analytics_result_contract():
    """Kiểm tra hợp đồng kết quả AnalyticsResult xuất xưởng."""
    t1 = AnalysisTask(task_id="t1", description="Task 1", status="COMPLETED")
    plan = AnalysisPlan(goal="Test Result", tasks=[t1])
    artifact = QueryArtifact(task_id="t1", sql="SELECT 1", status="SUCCESS")

    result = AnalyticsResult(
        plan=plan,
        artifacts=[artifact],
        insight="Tổng quan doanh thu ổn định",
        status="COMPLETED",
    )

    assert result.status == "COMPLETED"
    assert len(result.artifacts) == 1
    assert result.insight == "Tổng quan doanh thu ổn định"
    assert result.visualization is None

    # Test serialization
    dump = result.model_dump()
    assert dump["status"] == "COMPLETED"
    assert dump["plan"]["goal"] == "Test Result"


def test_evidence_evaluation_contract():
    """Kiểm tra khởi tạo và validation của EvidenceEvaluation."""
    eval_model = EvidenceEvaluation(
        has_enough_evidence=True,
        findings_summary="Đã đủ dữ liệu",
        reasoning="All data retrieved",
    )
    assert eval_model.has_enough_evidence is True
    assert eval_model.next_task is None

    eval_with_task = EvidenceEvaluation(
        has_enough_evidence=False,
        findings_summary="Thiếu phân khúc",
        next_task=AnalysisTask(task_id="t2", description="Query segment"),
    )
    assert eval_with_task.has_enough_evidence is False
    assert eval_with_task.next_task is not None
    assert eval_with_task.next_task.task_id == "t2"
