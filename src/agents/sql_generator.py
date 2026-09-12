"""Subagent: SQL Generator (Component 3.2).

Đóng gói theo chuẩn DeepAgents SubAgent dictionary (name="sql-generator"):
- Chế độ mode: "isolated" (Context Quarantine: cô lập hoàn toàn context suy luận SQL).
- Mô hình Tier 1 (gpt-4o / claude-3-5-sonnet) tối đa hóa Execution Accuracy (EX).
- Công cụ tools: [] (Zero-tool agent: tránh phân tâm gọi tool ngoài lề).
- Đầu ra có cấu trúc: SQLGenerationResult (Pydantic Model).
- Hỗ trợ 2 luồng gọi: Lượt sinh SQL đầu tiên và Lượt tự sửa lỗi (Self-Correction) với Actionable Feedback.
"""

import logging
import re
from typing import Any, Final

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import (
    SQL_GENERATOR_PROMPT,
    SQL_GENERATOR_RETRY_PROMPT,
    SQL_GENERATOR_SYSTEM_PROMPT,
    get_dialect_rules,
)
from src.config import get_settings
from src.models.state import SQLGenerationResult
from src.services import get_chat_model

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. HELPER LÀM SẠCH CÂU LỆNH SQL
# ==============================================================================


def clean_sql_query(raw_sql: str) -> str:
    """Làm sạch chuỗi SQL, bóc tách các khối markdown ```sql nếu mô hình vô tình sinh ra.

    Args:
        raw_sql: Chuỗi SQL thô từ mô hình.

    Returns:
        Chuỗi SQL thuần túy, sạch sẽ, không bọc markdown fence.
    """
    if not raw_sql or not raw_sql.strip():
        return ""

    cleaned = raw_sql.strip()

    # Bóc tách code block ```sql ... ``` hoặc ``` ... ```
    pattern = r"^```(?:sql)?\s*([\s\S]*?)\s*```$"
    match = re.match(pattern, cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()

    return cleaned


# ==============================================================================
# 2. KHAI BÁO SUBAGENT DICTIONARY CHUẨN DEEPAGENTS
# ==============================================================================


def get_sql_generator_subagent(model: str | None = None) -> dict[str, Any]:
    """Tạo cấu hình SubAgent Dictionary cho SQL Generator theo đặc tả DeepAgents.

    Args:
        model: Tùy chọn chỉ định model name (mặc định lấy tier1_model từ Settings).

    Returns:
        Dictionary theo đúng đặc tả DeepAgents SubAgent.
    """
    settings = get_settings()
    active_model = model or settings.tier1_model

    return {
        "name": "sql-generator",
        "description": (
            "Chuyên gia suy luận và sinh câu lệnh SQL phân tích dữ liệu chuẩn dialect "
            "(DuckDB / BigQuery) từ câu hỏi nghiệp vụ, schema context và lịch sử chẩn đoán lỗi."
        ),
        "system_prompt": SQL_GENERATOR_SYSTEM_PROMPT,
        "mode": "isolated",
        "tools": [],
        "model": active_model,
        "response_format": SQLGenerationResult,
    }


# Instance mặc định dùng sẵn
sql_generator_subagent: Final[dict[str, Any]] = get_sql_generator_subagent()


# ==============================================================================
# 3. HÀM ĐIỀU PHỐI THỰC THI (RUNNER FUNCTION)
# ==============================================================================


def generate_sql(
    question: str,
    schema_context: str,
    dialect: str = "duckdb",
    error_context: dict[str, Any] | None = None,
    llm: BaseChatModel | None = None,
) -> SQLGenerationResult:
    """Sinh câu lệnh SQL chuẩn từ câu hỏi nghiệp vụ và ngữ cảnh lược đồ.

    Hỗ trợ 2 luồng:
    - First Attempt: Dùng SQL_GENERATOR_PROMPT (lần đầu tiên).
    - Retry Flow: Dùng SQL_GENERATOR_RETRY_PROMPT nạp actionable_feedback từ error_context.

    Args:
        question: Câu hỏi tự nhiên của người dùng.
        schema_context: Ngữ cảnh lược đồ Markdown do Schema Retriever cung cấp.
        dialect: Dialect mục tiêu ('duckdb' hoặc 'bigquery').
        error_context: Lịch sử lỗi từ Control Pipeline ở chu kỳ retry trước (nếu có).
        llm: Instance Chat Model (nếu None sẽ tự khởi tạo Tier 1 qua get_chat_model).

    Returns:
        SQLGenerationResult: Kết quả sinh câu lệnh SQL có cấu trúc.

    Raises:
        RuntimeError: Khi không có LLM nào được cấu hình.
    """
    dialect_rules = get_dialect_rules(dialect)
    active_llm = llm or get_chat_model(tier="tier1")

    if active_llm is None:
        raise RuntimeError(
            "Không thể khởi tạo mô hình Chat Model Tier 1 cho SQL Generator. "
            "Vui lòng kiểm tra cấu hình API Key trong .env."
        )

    # Lựa chọn Prompt Template dựa trên việc có error_context hay không
    if error_context:
        failed_sql = error_context.get("failed_sql", "")
        error_type = error_context.get("error_type", "UNKNOWN_ERROR")
        error_message = error_context.get("error_message", "Không có chi tiết lỗi.")
        actionable_feedback = error_context.get(
            "actionable_feedback",
            "Hãy rà soát lại tên cột, bảng và cú pháp SQL theo đúng Schema Context.",
        )

        prompt_messages = SQL_GENERATOR_RETRY_PROMPT.format_messages(
            question=question,
            schema_context=schema_context,
            dialect_rules=dialect_rules,
            failed_sql=failed_sql,
            error_type=error_type,
            error_message=error_message,
            actionable_feedback=actionable_feedback,
        )
    else:
        prompt_messages = SQL_GENERATOR_PROMPT.format_messages(
            question=question,
            schema_context=schema_context,
            dialect_rules=dialect_rules,
        )

    structured_llm = active_llm.with_structured_output(SQLGenerationResult)
    result = structured_llm.invoke(prompt_messages)

    # Đảm bảo kết quả là instance SQLGenerationResult
    if isinstance(result, dict):
        result = SQLGenerationResult(**result)

    # Làm sạch câu SQL đề phòng LLM vô tình sinh bọc markdown code fences
    result.sql = clean_sql_query(result.sql)

    return result


__all__ = [
    "clean_sql_query",
    "generate_sql",
    "get_sql_generator_subagent",
    "sql_generator_subagent",
]
