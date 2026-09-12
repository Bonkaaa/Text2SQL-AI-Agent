"""Bounded Self-Correction Loop (Component 3.3).

Kết nối Subagent SQL Generator (Phase 3) với LangGraph Control Pipeline (Phase 1).
Quản lý vòng lặp tự sửa lỗi có chặn ngưỡng (MAX_RETRIES = 3):
- Nếu SQL hợp lệ: Trả về kết quả thực thi và dữ liệu.
- Nếu SQL lỗi và retry_count < MAX_RETRIES: Nạp Actionable Feedback từ ERROR_DIAGNOSTIC_AGENT để LLM tự sửa.
- Nếu vượt quá MAX_RETRIES: Kích hoạt Graceful Failure, không lặp vô hạn và trả về thông báo thân thiện.
"""

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from src.agents.control_pipeline import (
    build_control_pipeline_graph,
    run_control_pipeline,
)
from src.agents.sql_generator import generate_sql
from src.config import get_settings
from src.models.rbac import UserContext
from src.models.state import (
    ControlPipelineInput,
    SelfCorrectionResult,
)

logger = logging.getLogger(__name__)


def run_self_correction_loop(
    question: str,
    schema_context: str,
    user_context: UserContext,
    session_id: str,
    dialect: str = "duckdb",
    max_retries: int | None = None,
    sql_generator_llm: BaseChatModel | None = None,
    control_pipeline_graph: CompiledStateGraph | None = None,
) -> SelfCorrectionResult:
    """Điều phối vòng lặp sinh SQL và kiểm duyệt tự sửa lỗi có chặn ngưỡng <= max_retries.

    Args:
        question: Câu hỏi tự nhiên của người dùng.
        schema_context: Ngữ cảnh lược đồ Markdown do Schema Retriever cung cấp.
        user_context: Thông tin và quyền hạn của người dùng (RBAC UserContext).
        session_id: Định danh phiên truy vấn.
        dialect: Cú pháp cơ sở dữ liệu (mặc định 'duckdb').
        max_retries: Số lần thử lại tối đa (nếu None sẽ lấy settings.max_retries).
        sql_generator_llm: Model LLM cho SQL Generator (nếu có).
        control_pipeline_graph: Instance CompiledStateGraph của Control Pipeline (nếu có).

    Returns:
        SelfCorrectionResult: Kết quả thực thi cuối cùng và lịch sử các lần tự sửa lỗi.
    """
    settings = get_settings()
    limit_retries = max_retries if max_retries is not None else settings.max_retries
    graph = control_pipeline_graph or build_control_pipeline_graph()

    retry_count = 0
    error_context: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []

    last_sql = ""
    last_explanation = ""

    while retry_count <= limit_retries:
        logger.info(
            "Bắt đầu lượt chạy thứ %d/%d cho session: %s (retry_count=%d)",
            retry_count + 1,
            limit_retries + 1,
            session_id,
            retry_count,
        )

        # 1. Sinh hoặc sửa câu lệnh SQL qua Subagent SQL Generator
        sql_result = generate_sql(
            question=question,
            schema_context=schema_context,
            dialect=dialect,
            error_context=error_context,
            llm=sql_generator_llm,
        )
        last_sql = sql_result.sql
        last_explanation = sql_result.explanation

        # 2. Gửi câu SQL nháp qua LangGraph Control Pipeline
        input_data: ControlPipelineInput = {
            "sql": sql_result.sql,
            "user_context": user_context,
            "session_id": session_id,
        }
        pipeline_output = run_control_pipeline(graph, input_data)

        # 3. Ghi nhận lịch sử lần thử này
        is_valid = pipeline_output.get("is_valid", False)
        status = pipeline_output.get("status")
        error_type = pipeline_output.get("error_type")
        error_message = pipeline_output.get("error_message")
        actionable_feedback = pipeline_output.get("actionable_feedback")
        diagnostic_result = pipeline_output.get("diagnostic_result")

        history_entry: dict[str, Any] = {
            "attempt": retry_count + 1,
            "sql": sql_result.sql,
            "is_valid": is_valid,
            "status": status,
            "error_type": error_type,
            "error_message": error_message,
            "actionable_feedback": actionable_feedback,
        }
        history.append(history_entry)

        # 4. Kiểm tra điều kiện thành công
        if is_valid:
            logger.info(
                "Truy vấn SQL vượt qua kiểm soát thành công tại lần thử thứ %d (retry_count=%d)",
                retry_count + 1,
                retry_count,
            )
            return SelfCorrectionResult(
                success=True,
                sql=sql_result.sql,
                data=pipeline_output.get("data"),
                columns=pipeline_output.get("columns"),
                retry_count=retry_count,
                explanation=last_explanation,
                execution_time_ms=pipeline_output.get("execution_time_ms", 0.0),
                bytes_scanned=pipeline_output.get("bytes_scanned", 0),
                history=history,
            )

        # 5. Xử lý khi thất bại: Kiểm tra giới hạn retry
        if retry_count < limit_retries:
            retry_count += 1
            logger.warning(
                "Truy vấn bị từ chối (%s: %s). Chuẩn bị thử lại lần %d...",
                error_type,
                error_message,
                retry_count,
            )
            error_context = {
                "failed_sql": sql_result.sql,
                "error_type": error_type,
                "error_message": error_message,
                "actionable_feedback": actionable_feedback,
            }
        else:
            # Vượt quá số lần thử lại tối đa -> Graceful Failure
            logger.error(
                "Vượt quá giới hạn thử lại tối đa (%d lần). Kích hoạt dừng an toàn.",
                limit_retries,
            )
            friendly_error_message = (
                f"Hệ thống không thể thực thi truy vấn thành công sau {retry_count} lần tự động sửa lỗi. "
                f"Lý do kỹ thuật: {error_message or 'Lỗi kiểm duyệt hoặc thực thi SQL'}. "
                "Gợi ý: Vui lòng kiểm tra lại câu hỏi nghiệp vụ hoặc liên hệ quản trị viên."
            )
            return SelfCorrectionResult(
                success=False,
                sql=last_sql,
                retry_count=retry_count,
                explanation=last_explanation,
                error_message=friendly_error_message,
                error_type=error_type,
                actionable_feedback=actionable_feedback,
                diagnostic_result=diagnostic_result,
                execution_time_ms=pipeline_output.get("execution_time_ms", 0.0),
                bytes_scanned=pipeline_output.get("bytes_scanned", 0),
                history=history,
            )

    # Dự phòng an toàn (không bao giờ chạm tới)
    return SelfCorrectionResult(
        success=False,
        sql=last_sql,
        retry_count=retry_count,
        explanation=last_explanation,
        error_message="Vòng lặp tự sửa lỗi kết thúc bất thường.",
        history=history,
    )


__all__ = [
    "run_self_correction_loop",
]
