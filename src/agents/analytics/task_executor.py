"""Task Executor Node (Component 2.3).

Thực thi một AnalysisTask đơn lẻ qua toàn bộ chu trình Text-to-SQL:
Schema Retriever -> SQL Generator -> Control Pipeline -> QueryArtifact.
Hỗ trợ cơ chế Self-Correction tối đa 3 lần retry theo kiến trúc v4.0.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from src.agents.control_pipeline import run_control_pipeline
from src.agents.schema_retriever import retrieve_schema_context
from src.agents.sql_generator import generate_sql
from src.models.artifacts import AnalysisTask, QueryArtifact
from src.models.rbac import UserContext
from src.models.state import ControlPipelineOutput, SQLGenerationResult

logger = logging.getLogger(__name__)

MAX_TASK_RETRIES = 3


def _build_task_prompt(
    task: AnalysisTask,
    prior_artifacts: list[QueryArtifact] | None = None,
) -> str:
    """Tạo câu hỏi phân tích có nhúng ngữ cảnh từ các tasks đã chạy trước đó."""
    prompt = f"Mục tiêu phân tích: {task.description}"
    if prior_artifacts:
        summaries = []
        for a in prior_artifacts:
            sample_preview = str(a.data[:2]) if a.data else "[]"
            summaries.append(
                f"- Task {a.task_id} [{a.status}]: SQL: {a.sql} | Rows: {a.row_count} | Dữ liệu mẫu: {sample_preview}"
            )
        prompt += "\n\nNgữ cảnh số liệu từ các bước trước:\n" + "\n".join(summaries)
    return prompt


def _map_pipeline_status(output: ControlPipelineOutput) -> str:
    """Ánh xạ trạng thái từ ControlPipelineOutput sang trạng thái của QueryArtifact."""
    if output.get("is_valid"):
        return "SUCCESS"

    if output.get("hitl_required") and output.get("hitl_approved") is False:
        return "BLOCKED_HITL"

    actionable = output.get("actionable_feedback", "")
    if "AST" in actionable or "không an toàn" in actionable:
        return "BLOCKED_AST"
    if "RBAC" in actionable or "quyền" in actionable:
        return "BLOCKED_RBAC"
    if "chi phí" in actionable.lower() or "cost" in actionable.lower():
        return "BLOCKED_COST"
    if "timeout" in actionable.lower():
        return "TIMEOUT"

    return "DB_ERROR"


async def aexecute_analysis_task(
    task: AnalysisTask,
    user_context: UserContext,
    prior_artifacts: list[QueryArtifact] | None = None,
    max_retries: int = MAX_TASK_RETRIES,
) -> QueryArtifact:
    """Thực thi một AnalysisTask bất đồng bộ với vòng lặp Self-Correction tối đa max_retries.

    Args:
        task: Đối tượng AnalysisTask cần thực thi.
        user_context: Ngữ cảnh phân quyền người dùng (UserContext).
        prior_artifacts: Danh sách kết quả từ các task trước để tạo bối cảnh chuỗi.
        max_retries: Số lần tự sửa lỗi tối đa (mặc định 3).

    Returns:
        QueryArtifact chứa kết quả dữ liệu hoặc thông tin lỗi.
    """
    task.status = "EXECUTING"

    # 0. Kiểm tra nếu task này đã được phê duyệt HITL trước đó (Resume từ Persistent Store)
    from src.agents.control_pipeline.pending_store import (
        consume_pending_approval,
        get_pending_approval,
    )

    q_hash = hashlib.sha256(task.description.encode()).hexdigest()[:16]
    approved_pending = get_pending_approval(
        session_id=user_context.session_id,
        task_id=task.task_id,
        plan_id=task.plan_id,
        question_hash=q_hash,
        status="APPROVED",
        consumed=False,
    )
    # Fallback kiểm tra nếu approval không có plan_id (từ request đơn lẻ hoặc test)
    if not approved_pending and not task.plan_id:
        approved_pending = get_pending_approval(
            session_id=user_context.session_id,
            task_id=task.task_id,
            status="APPROVED",
            consumed=False,
        )

    if (
        approved_pending
        and approved_pending.execution_result
        and consume_pending_approval(approved_pending.approval_id)
    ):
        logger.info(
            "Task %s (plan %s) đã được phê duyệt HITL trước đó. Nạp lại kết quả thực thi bền vững và đánh dấu consumed.",
            task.task_id,
            task.plan_id,
        )
        exec_res = approved_pending.execution_result
        task.status = "SUCCESS" if exec_res.get("success", True) else "FAILED"
        return QueryArtifact(
            task_id=task.task_id,
            sql=approved_pending.sql,
            dialect="duckdb",
            explanation="Kết quả thực thi từ phê duyệt Quản trị viên (HITL Approved).",
            tables_used=approved_pending.tables_used,
            columns_used=[],
            status=task.status,
            data=exec_res.get("data", []),
            columns=exec_res.get("columns", []),
            row_count=exec_res.get("row_count", len(exec_res.get("data", []))),
            execution_time_ms=exec_res.get("execution_time_ms", 0.0),
            error_message=exec_res.get("error_message"),
        )

    question = _build_task_prompt(task, prior_artifacts)

    # 1. Trích xuất ngữ cảnh lược đồ TPC-H và Entity/Categorical Linking cho riêng task này
    schema_res = retrieve_schema_context(task.description)
    schema_context = schema_res.context_markdown

    error_context: dict[str, Any] | None = None
    last_sql = ""
    last_pipeline_output: ControlPipelineOutput | None = None

    # Guardrail MAX_RETRIES = 3 (ISSUE-07): Clamp chặt chẽ trong khoảng [0, MAX_TASK_RETRIES]
    effective_max_retries = min(max(0, max_retries), MAX_TASK_RETRIES)

    for attempt in range(effective_max_retries + 1):
        task.retry_count = attempt
        logger.info(
            "Thực thi task %s (Attempt %d/%d): %s",
            task.task_id,
            attempt,
            effective_max_retries,
            task.description,
        )

        # 2. Sinh câu lệnh SQL bất đồng bộ không chặn event loop (ISSUE-06)
        sql_result: SQLGenerationResult = await asyncio.to_thread(
            generate_sql,
            question=question,
            schema_context=schema_context,
            error_context=error_context,
        )
        last_sql = sql_result.sql

        # 3. Chạy qua Control Pipeline bất đồng bộ (ISSUE-06 & ISSUE-08)
        pipeline_output: ControlPipelineOutput = await asyncio.to_thread(
            run_control_pipeline,
            sql=sql_result.sql,
            user_context=user_context,
            session_id=user_context.session_id,
            question=task.description,
        )
        last_pipeline_output = pipeline_output

        # 4. Kiểm tra thành công
        if pipeline_output.get("is_valid"):
            logger.info(
                "Task %s thực thi THÀNH CÔNG tại attempt %d", task.task_id, attempt
            )
            task.status = "COMPLETED"
            artifact = QueryArtifact(
                task_id=task.task_id,
                sql=last_sql,
                dialect=sql_result.dialect,
                explanation=sql_result.explanation,
                tables_used=pipeline_output.get("tables_used", []),
                columns_used=pipeline_output.get("columns_used", []),
                status="SUCCESS",
                data=pipeline_output.get("data", []) or [],
                columns=pipeline_output.get("columns", []) or [],
                row_count=pipeline_output.get("row_count", 0),
                execution_time_ms=pipeline_output.get("execution_time_ms", 0.0),
                error_message=None,
            )
            task.query_artifact = artifact
            return artifact

        # 4b. Kiểm tra nếu câu lệnh bị tạm dừng chờ duyệt HITL (ISSUE-03)
        if pipeline_output.get("status") == "BLOCKED_HITL":
            logger.info(
                "Task %s tạm dừng chờ phê duyệt HITL: %s",
                task.task_id,
                pipeline_output.get("hitl_reason"),
            )
            from src.agents.control_pipeline.pending_store import save_pending_approval

            q_hash = hashlib.sha256(task.description.encode()).hexdigest()[:16]
            save_pending_approval(
                session_id=user_context.session_id,
                sql=last_sql,
                reason=pipeline_output.get("hitl_reason"),
                estimated_bytes=pipeline_output.get("bytes_scanned", 0),
                tables_used=pipeline_output.get("tables_used", []),
                task_id=task.task_id,
                plan_id=task.plan_id,
                question_hash=q_hash,
                user_context=user_context,
            )
            task.status = "BLOCKED_HITL"
            artifact = QueryArtifact(
                task_id=task.task_id,
                sql=last_sql,
                dialect=sql_result.dialect,
                explanation=sql_result.explanation,
                tables_used=pipeline_output.get("tables_used", []),
                columns_used=pipeline_output.get("columns_used", []),
                status="BLOCKED_HITL",
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=pipeline_output.get("execution_time_ms", 0.0),
                error_message=pipeline_output.get("error_message")
                or "Truy vấn chờ phê duyệt HITL.",
            )
            task.query_artifact = artifact
            return artifact

        # 5. Truy vấn không hợp lệ -> Chuẩn bị error_context có cấu trúc cho lần thử tiếp theo
        actionable_feedback = (
            pipeline_output.get("actionable_feedback") or "Truy vấn không hợp lệ."
        )
        diagnostic = pipeline_output.get("diagnostic_result")
        diag_msg = diagnostic.suggested_fix if diagnostic else ""
        error_context = {
            "failed_sql": last_sql,
            "error_type": pipeline_output.get("error_type")
            or "VALIDATION_OR_EXECUTION_ERROR",
            "error_message": pipeline_output.get("error_message")
            or actionable_feedback,
            "actionable_feedback": f"{actionable_feedback} {diag_msg}".strip(),
        }
        logger.warning(
            "Task %s thất bại tại attempt %d: %s",
            task.task_id,
            attempt,
            actionable_feedback,
        )

    # 5. Nếu vượt quá số lần retry mà vẫn thất bại
    logger.error(
        "Task %s THẤT BẠI sau %d lần thử", task.task_id, effective_max_retries + 1
    )
    task.status = "FAILED"
    status_str = _map_pipeline_status(last_pipeline_output or {})

    error_msg = (
        last_pipeline_output.get("actionable_feedback")
        if last_pipeline_output
        else "Vượt quá số lần thử tự sửa lỗi (Max retries exceeded)."
    )

    artifact = QueryArtifact(
        task_id=task.task_id,
        sql=last_sql,
        status=status_str,
        data=[],
        columns=[],
        row_count=0,
        execution_time_ms=last_pipeline_output.get("execution_time_ms", 0.0)
        if last_pipeline_output
        else 0.0,
        error_message=error_msg,
    )
    task.query_artifact = artifact
    return artifact


def execute_analysis_task(
    task: AnalysisTask,
    user_context: UserContext,
    prior_artifacts: list[QueryArtifact] | None = None,
    max_retries: int = MAX_TASK_RETRIES,
) -> QueryArtifact:
    """Wrapper đồng bộ cho aexecute_analysis_task."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Nếu đang trong event loop, tạo task
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(
            aexecute_analysis_task(task, user_context, prior_artifacts, max_retries)
        )
    return asyncio.run(
        aexecute_analysis_task(task, user_context, prior_artifacts, max_retries)
    )
