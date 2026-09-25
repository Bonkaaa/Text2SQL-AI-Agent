"""Unit tests cho Task Executor Node (Component 2.3 - TDD).

Kiểm tra:
- Thực thi thành công một task qua Schema Retriever -> SQL Generator -> Control Pipeline.
- Cơ chế Self-Correction tự động retry khi gặp lỗi cú pháp / DB.
- Ràng buộc MAX_RETRIES = 3, sau 3 lần retry thì đánh dấu task FAILED và không lặp vô tận.
- Tích hợp kết quả từ các tasks trước (prior_artifacts) vào context câu hỏi.
- Wrapper thực thi đồng bộ.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.analytics.task_executor import (
    aexecute_analysis_task,
    execute_analysis_task,
)
from src.models.artifacts import AnalysisTask, QueryArtifact
from src.models.rbac import UserContext, UserRole
from src.models.state import (
    ControlPipelineOutput,
    DiagnosticResult,
    SQLGenerationResult,
)


@pytest.fixture
def sample_user_context() -> UserContext:
    return UserContext(
        user_id="test_analyst",
        session_id="test_session_task_executor",
        role=UserRole.ANALYST,
    )


@pytest.mark.asyncio
async def test_execute_task_success(sample_user_context):
    """Kiểm tra thực thi 1 task thành công ngay lượt đầu (không cần retry)."""
    task = AnalysisTask(
        task_id="task_1",
        description="Tính tổng doanh thu năm 1995",
        status="PLANNED",
    )

    mock_sql_result = SQLGenerationResult(
        sql="SELECT sum(l_extendedprice) as revenue FROM lineitem WHERE extract(year from l_shipdate) = 1995",
        dialect="duckdb",
        explanation="Tính tổng doanh thu theo năm",
        tables=["lineitem"],
        columns=["l_extendedprice", "l_shipdate"],
    )

    mock_pipeline_output: ControlPipelineOutput = {
        "is_valid": True,
        "ast_valid": True,
        "rbac_valid": True,
        "cost_valid": True,
        "hitl_required": False,
        "data": [{"revenue": 54321000.0}],
        "columns": ["revenue"],
        "row_count": 1,
        "execution_time_ms": 12.5,
        "tables_used": ["lineitem"],
        "columns_used": ["l_extendedprice", "l_shipdate"],
    }

    with (
        patch(
            "src.agents.analytics.task_executor.generate_sql",
            return_value=mock_sql_result,
        ),
        patch(
            "src.agents.analytics.task_executor.run_control_pipeline",
            return_value=mock_pipeline_output,
        ),
    ):
        artifact = await aexecute_analysis_task(
            task=task,
            user_context=sample_user_context,
        )

        assert artifact is not None
        assert artifact.status == "SUCCESS"
        assert artifact.task_id == "task_1"
        assert artifact.row_count == 1
        assert artifact.data == [{"revenue": 54321000.0}]
        assert task.status == "COMPLETED"
        assert task.retry_count == 0
        assert task.query_artifact == artifact


@pytest.mark.asyncio
async def test_execute_task_self_correction_retry(sample_user_context):
    """Kiểm tra cơ chế tự sửa lỗi: lượt 1 bị lỗi DB -> sửa lại ở lượt 2 và thành công."""
    task = AnalysisTask(
        task_id="task_1",
        description="Tính doanh thu theo khách hàng",
        status="PLANNED",
    )

    # Lượt 1: Sai tên cột -> DB_ERROR
    sql_fail = SQLGenerationResult(
        sql="SELECT c_name, sum(total) FROM customer GROUP BY 1",
        dialect="duckdb",
        explanation="Query sai",
    )
    fail_output: ControlPipelineOutput = {
        "is_valid": False,
        "ast_valid": True,
        "rbac_valid": True,
        "cost_valid": True,
        "hitl_required": False,
        "error_type": "DATABASE_EXECUTION_ERROR",
        "error_message": "Column 'total' does not exist",
        "actionable_feedback": "Cột 'total' không tồn tại, cần dùng c_acctbal hoặc join orders",
        "diagnostic_result": DiagnosticResult(
            error_type="DATABASE_EXECUTION_ERROR",
            error_category="DB_RUNTIME_ERROR",
            root_cause="Sai tên cột",
            explanation="Cột total không có trong customer",
            suggested_fix="Sửa thành c_acctbal",
            actionable_feedback="Sửa thành c_acctbal",
        ),
    }

    # Lượt 2: Đã sửa đúng -> SUCCESS
    sql_success = SQLGenerationResult(
        sql="SELECT c_name, c_acctbal FROM customer",
        dialect="duckdb",
        explanation="Query đúng",
    )
    success_output: ControlPipelineOutput = {
        "is_valid": True,
        "ast_valid": True,
        "rbac_valid": True,
        "cost_valid": True,
        "hitl_required": False,
        "data": [{"c_name": "Customer#001", "c_acctbal": 100.0}],
        "columns": ["c_name", "c_acctbal"],
        "row_count": 1,
        "execution_time_ms": 10.0,
    }

    with (
        patch(
            "src.agents.analytics.task_executor.generate_sql",
            side_effect=[sql_fail, sql_success],
        ),
        patch(
            "src.agents.analytics.task_executor.run_control_pipeline",
            side_effect=[fail_output, success_output],
        ),
    ):
        artifact = await aexecute_analysis_task(
            task=task,
            user_context=sample_user_context,
        )

        assert artifact.status == "SUCCESS"
        assert task.status == "COMPLETED"
        assert task.retry_count == 1  # Đã qua 1 lần retry thành công


@pytest.mark.asyncio
async def test_execute_task_failure_after_max_retries(sample_user_context):
    """Kiểm tra khi retry quá số lần cho phép (MAX_RETRIES), dừng lại và đánh dấu FAILED."""
    task = AnalysisTask(
        task_id="task_fail",
        description="Task cố tình gây lỗi",
        status="PLANNED",
    )

    sql_fail = SQLGenerationResult(
        sql="SELECT * FROM invalid_table",
        dialect="duckdb",
        explanation="Query invalid table",
    )
    fail_output: ControlPipelineOutput = {
        "is_valid": False,
        "actionable_feedback": "Table invalid_table does not exist",
    }

    # Giả sử max_retries = 1 (chạy tổng cộng 2 lượt: 1 ban đầu + 1 retry)
    with (
        patch("src.agents.analytics.task_executor.generate_sql", return_value=sql_fail),
        patch(
            "src.agents.analytics.task_executor.run_control_pipeline",
            return_value=fail_output,
        ),
    ):
        artifact = await aexecute_analysis_task(
            task=task,
            user_context=sample_user_context,
            max_retries=1,
        )

        assert artifact.status == "DB_ERROR"
        assert task.status == "FAILED"
        assert task.retry_count == 1
        assert "invalid_table" in artifact.error_message


@pytest.mark.asyncio
async def test_execute_task_with_prior_evidences(sample_user_context):
    """Kiểm tra khi có prior_artifacts, context từ các task trước được nhúng vào prompt cho SQL generator."""
    task = AnalysisTask(
        task_id="task_2",
        description="Tìm các nhà cung cấp tại quốc gia vừa tìm được",
        status="PLANNED",
    )

    prior_art = QueryArtifact(
        task_id="task_1",
        sql="SELECT n_name FROM nation WHERE n_nationkey = 1",
        status="SUCCESS",
        data=[{"n_name": "GERMANY"}],
        columns=["n_name"],
        row_count=1,
    )

    mock_generate = MagicMock(
        return_value=SQLGenerationResult(
            sql="SELECT s_name FROM supplier",
            dialect="duckdb",
            explanation="Query supplier",
        )
    )

    success_output: ControlPipelineOutput = {
        "is_valid": True,
        "data": [{"s_name": "Supplier#001"}],
        "columns": ["s_name"],
        "row_count": 1,
    }

    with (
        patch("src.agents.analytics.task_executor.generate_sql", mock_generate),
        patch(
            "src.agents.analytics.task_executor.run_control_pipeline",
            return_value=success_output,
        ),
    ):
        await aexecute_analysis_task(
            task=task,
            user_context=sample_user_context,
            prior_artifacts=[prior_art],
        )

    # Đảm bảo generate_sql được gọi với question có chứa bối cảnh task_1
    call_args = mock_generate.call_args[1]
    assert (
        "task_1" in call_args["question"]
        or "GERMANY" in call_args["question"]
        or "Nhà cung cấp" in call_args["question"]
    )


def test_sync_execute_task_wrapper(sample_user_context):
    """Kiểm tra hàm đồng bộ execute_analysis_task hoạt động chính xác."""
    task = AnalysisTask(task_id="task_sync", description="Test sync wrapper")
    mock_artifact = QueryArtifact(
        task_id="task_sync",
        sql="SELECT 1",
        status="SUCCESS",
    )

    with patch(
        "src.agents.analytics.task_executor.aexecute_analysis_task",
        new_callable=AsyncMock,
    ) as mock_async:
        mock_async.return_value = mock_artifact
        artifact = execute_analysis_task(
            task=task,
            user_context=sample_user_context,
        )

        assert artifact.status == "SUCCESS"
        mock_async.assert_called_once()


@pytest.mark.asyncio
async def test_execute_task_wires_schema_retriever(sample_user_context):
    """Kiểm tra retrieve_schema_context được gọi để lấy DDL truyền cho generate_sql."""
    from src.models.state import SchemaContextResult

    task = AnalysisTask(
        task_id="task_schema_test",
        description="Tìm các đơn hàng năm 1995",
        status="PLANNED",
    )

    mock_schema = SchemaContextResult(
        selected_tables=["orders"],
        join_conditions=[],
        categorical_filters={},
        metric_formulas=[],
        context_markdown="### Schema Context Orders",
    )

    mock_sql = SQLGenerationResult(
        sql="SELECT * FROM orders WHERE extract(year from o_orderdate) = 1995",
        dialect="duckdb",
        explanation="Query orders",
    )

    mock_pipe: ControlPipelineOutput = {
        "is_valid": True,
        "data": [{"o_orderkey": 1}],
        "columns": ["o_orderkey"],
        "row_count": 1,
    }

    with (
        patch(
            "src.agents.analytics.task_executor.retrieve_schema_context",
            return_value=mock_schema,
        ) as mock_retrieve,
        patch(
            "src.agents.analytics.task_executor.generate_sql",
            return_value=mock_sql,
        ) as mock_gen,
        patch(
            "src.agents.analytics.task_executor.run_control_pipeline",
            return_value=mock_pipe,
        ),
    ):
        await aexecute_analysis_task(task=task, user_context=sample_user_context)

        mock_retrieve.assert_called_once_with(task.description)
        assert mock_gen.call_args[1]["schema_context"] == "### Schema Context Orders"

