"""Subagent & DeepAgent: SQL Generator (Component 3.2).

Đóng gói SQL Generator dưới dạng một DeepAgent hoàn chỉnh chạy trên nền LangGraph runtime:
- Đồ thị CompiledStateGraph khởi tạo qua `create_deep_agent`.
- Tự động nạp kỹ năng nghiệp vụ:
  * `skills/duckdb-sql`: Cú pháp tối ưu DuckDB, DATE literals, khoảng thời gian INTERVAL, ILIKE, GROUP BY ALL, Window functions.
  * `skills/tpch-analytics`: Định nghĩa chỉ số dbt Semantic Metrics và ngữ nghĩa 8 bảng TPC-H.
- Gắn trực tiếp 4 Active Metadata Tools:
  * `search_tables_and_columns`: Tra cứu DDL bảng và cột theo từ khóa.
  * `get_column_samples_and_values`: Tra cứu giá trị thực tế của các cột phân loại (categorical values).
  * `find_join_path`: Tìm đường nối khóa ngoại ngắn nhất và bảng cầu nối qua thuật toán BFS.
  * `search_business_definition`: Tra cứu công thức tính dbt Semantic Metrics chuẩn hóa.
- Structured Output: Tích hợp `response_format=SQLGenerationResult` thu về kết quả Pydantic chuẩn trong 1 luồng.
- Hỗ trợ cả Synchronous (`generate_sql`) và Asynchronous (`agenerate_sql`) runners.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Final

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from src.agents.prompts import (
    SQL_GENERATOR_PROMPT,
    SQL_GENERATOR_RETRY_PROMPT,
    SQL_GENERATOR_SYSTEM_PROMPT,
    get_dialect_rules,
)
from src.agents.tools.metadata_tools import SQL_GENERATOR_TOOLS
from src.config import get_settings
from src.models.state import SQLGenerationResult
from src.services import get_chat_model

logger = logging.getLogger(__name__)

# Danh sách kỹ năng nghiệp vụ mặc định nạp cho SQL Generator DeepAgent
DEFAULT_SQL_GENERATOR_SKILLS: Final[list[str]] = [
    "skills/duckdb-sql",
    "skills/tpcds-analytics",
    "skills/tpch-analytics",
]


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
        "tools": SQL_GENERATOR_TOOLS,
        "model": active_model,
        "response_format": SQLGenerationResult,
    }


# Instance mặc định dùng sẵn
sql_generator_subagent: Final[dict[str, Any]] = get_sql_generator_subagent()


# ==============================================================================
# 3. FACTORY FUNCTION: TẠO DEEPAGENT CHO SQL GENERATOR
# ==============================================================================


def create_sql_generator_agent(
    model: str | BaseChatModel | None = None,
    tools: list[Any] | None = None,
    skills: list[str] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    system_prompt: str = SQL_GENERATOR_SYSTEM_PROMPT,
    name: str = "sql-generator-agent",
    **kwargs: Any,
) -> CompiledStateGraph:
    """Khởi tạo SQL Generator dưới dạng DeepAgent chuẩn với Tools, Skills và response_format.

    Args:
        model: Chat model instance hoặc tên model (mặc định lấy Tier 1 từ Settings).
        tools: Danh sách công cụ tra cứu siêu dữ liệu (mặc định SQL_GENERATOR_TOOLS).
        skills: Danh sách kỹ năng nạp vào agent (mặc định duckdb-sql và tpch-analytics).
        checkpointer: Checkpointer quản lý trạng thái phiên (nếu có).
        system_prompt: Lời nhắc hệ thống định hướng chuyên gia SQL.
        name: Định danh tên agent trong hệ thống LangGraph.
        **kwargs: Tham số bổ sung chuyển tiếp cho deepagents.create_deep_agent.

    Returns:
        CompiledStateGraph: Đồ thị DeepAgent sẵn sàng invoke hoặc ainvoke.
    """
    settings = get_settings()
    active_model = model or get_chat_model(tier="tier1") or settings.tier1_model
    active_tools = tools if tools is not None else list(SQL_GENERATOR_TOOLS)
    active_skills = skills if skills is not None else list(DEFAULT_SQL_GENERATOR_SKILLS)

    return create_deep_agent(
        model=active_model,
        tools=active_tools,
        skills=active_skills if active_skills else None,
        response_format=SQLGenerationResult,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        name=name,
        **kwargs,
    )


# ==============================================================================
# 4. HELPERS XỬ LÝ PROMPT VÀ TRÍCH XUẤT OUTPUT
# ==============================================================================


def _build_prompt_messages(
    question: str,
    schema_context: str = "",
    dialect: str = "duckdb",
    error_context: dict[str, Any] | None = None,
) -> list[Any]:
    """Tạo danh sách tin nhắn gửi vào DeepAgent dựa trên trạng thái câu hỏi và lỗi."""
    dialect_rules = get_dialect_rules(dialect)
    if error_context:
        failed_sql = error_context.get("failed_sql", "")
        error_type = error_context.get("error_type", "UNKNOWN_ERROR")
        error_message = error_context.get("error_message", "Không có chi tiết lỗi.")
        actionable_feedback = error_context.get(
            "actionable_feedback",
            "Hãy rà soát lại tên cột, bảng và cú pháp SQL theo đúng Schema Context.",
        )

        return list(
            SQL_GENERATOR_RETRY_PROMPT.format_messages(
                question=question,
                schema_context=schema_context,
                dialect_rules=dialect_rules,
                failed_sql=failed_sql,
                error_type=error_type,
                error_message=error_message,
                actionable_feedback=actionable_feedback,
            )
        )

    return list(
        SQL_GENERATOR_PROMPT.format_messages(
            question=question,
            schema_context=schema_context,
            dialect_rules=dialect_rules,
        )
    )


def _extract_sql_result_from_output(
    output: dict[str, Any], dialect: str = "duckdb"
) -> SQLGenerationResult:
    """Trích xuất và chuẩn hóa kết quả SQLGenerationResult từ đầu ra của DeepAgent."""
    structured = output.get("structured_response")
    if isinstance(structured, SQLGenerationResult):
        result = structured
    elif isinstance(structured, dict):
        result = SQLGenerationResult(**structured)
    else:
        # Fallback: kiểm tra tin nhắn cuối cùng nếu model không gọi tool structured_response
        messages = output.get("messages", [])
        last_msg = messages[-1] if messages else None
        if last_msg and hasattr(last_msg, "content") and last_msg.content:
            try:
                data = json.loads(last_msg.content)
                if isinstance(data, dict):
                    result = SQLGenerationResult(**data)
                else:
                    result = SQLGenerationResult(
                        sql=clean_sql_query(str(last_msg.content)),
                        dialect=dialect,
                    )
            except (json.JSONDecodeError, ValueError, KeyError):
                result = SQLGenerationResult(
                    sql=clean_sql_query(str(last_msg.content)),
                    dialect=dialect,
                )
        else:
            result = SQLGenerationResult(sql="", dialect=dialect)

    result.sql = clean_sql_query(result.sql)
    if not result.dialect:
        result.dialect = dialect
    return result


# ==============================================================================
# 5. RUNNERS: SYNCHRONOUS & ASYNCHRONOUS
# ==============================================================================


def generate_sql(
    question: str,
    schema_context: str = "",
    dialect: str = "duckdb",
    error_context: dict[str, Any] | None = None,
    llm: BaseChatModel | None = None,
    tools: list[Any] | None = None,
    skills: list[str] | None = None,
    agent: CompiledStateGraph | None = None,
    max_tool_iterations: int = 5,
) -> SQLGenerationResult:
    """Sinh câu lệnh SQL chuẩn từ câu hỏi nghiệp vụ và ngữ cảnh lược đồ qua DeepAgent.

    Args:
        question: Câu hỏi tự nhiên của người dùng.
        schema_context: Ngữ cảnh lược đồ Markdown do Schema Retriever cung cấp.
        dialect: Dialect mục tiêu ('duckdb' hoặc 'bigquery').
        error_context: Lịch sử lỗi từ Control Pipeline ở chu kỳ retry trước (nếu có).
        llm: Instance Chat Model (nếu None sẽ tự khởi tạo Tier 1 qua get_chat_model).
        tools: Danh sách tools cung cấp cho agent (mặc định SQL_GENERATOR_TOOLS).
        skills: Danh sách skills nạp vào agent (mặc định duckdb-sql và tpch-analytics).
        agent: DeepAgent StateGraph đã biên dịch (nếu None sẽ tự khởi tạo).
        max_tool_iterations: Tham số tương thích ngược.

    Returns:
        SQLGenerationResult: Kết quả sinh câu lệnh SQL có cấu trúc.

    Raises:
        RuntimeError: Khi không có LLM nào được cấu hình.
    """
    active_llm = llm or get_chat_model(tier="tier1")
    if active_llm is None and agent is None:
        raise RuntimeError(
            "Không thể khởi tạo mô hình Chat Model Tier 1 cho SQL Generator. "
            "Vui lòng kiểm tra cấu hình API Key trong .env."
        )

    prompt_messages = _build_prompt_messages(
        question=question,
        schema_context=schema_context,
        dialect=dialect,
        error_context=error_context,
    )

    active_agent = agent or create_sql_generator_agent(
        model=active_llm,
        tools=tools,
        skills=skills,
    )

    output = active_agent.invoke({"messages": list(prompt_messages)})
    return _extract_sql_result_from_output(output, dialect=dialect)


async def agenerate_sql(
    question: str,
    schema_context: str = "",
    dialect: str = "duckdb",
    error_context: dict[str, Any] | None = None,
    llm: BaseChatModel | None = None,
    tools: list[Any] | None = None,
    skills: list[str] | None = None,
    agent: CompiledStateGraph | None = None,
    max_tool_iterations: int = 5,
) -> SQLGenerationResult:
    """Sinh câu lệnh SQL chuẩn bất đồng bộ từ câu hỏi nghiệp vụ và ngữ cảnh lược đồ qua DeepAgent.

    Args:
        question: Câu hỏi tự nhiên của người dùng.
        schema_context: Ngữ cảnh lược đồ Markdown do Schema Retriever cung cấp.
        dialect: Dialect mục tiêu ('duckdb' hoặc 'bigquery').
        error_context: Lịch sử lỗi từ Control Pipeline ở chu kỳ retry trước (nếu có).
        llm: Instance Chat Model (nếu None sẽ tự khởi tạo Tier 1 qua get_chat_model).
        tools: Danh sách tools cung cấp cho agent (mặc định SQL_GENERATOR_TOOLS).
        skills: Danh sách skills nạp vào agent (mặc định duckdb-sql và tpch-analytics).
        agent: DeepAgent StateGraph đã biên dịch (nếu None sẽ tự khởi tạo).
        max_tool_iterations: Tham số tương thích ngược.

    Returns:
        SQLGenerationResult: Kết quả sinh câu lệnh SQL có cấu trúc.

    Raises:
        RuntimeError: Khi không có LLM nào được cấu hình.
    """
    active_llm = llm or get_chat_model(tier="tier1")
    if active_llm is None and agent is None:
        raise RuntimeError(
            "Không thể khởi tạo mô hình Chat Model Tier 1 cho SQL Generator. "
            "Vui lòng kiểm tra cấu hình API Key trong .env."
        )

    prompt_messages = _build_prompt_messages(
        question=question,
        schema_context=schema_context,
        dialect=dialect,
        error_context=error_context,
    )

    active_agent = agent or create_sql_generator_agent(
        model=active_llm,
        tools=tools,
        skills=skills,
    )

    output = await active_agent.ainvoke({"messages": list(prompt_messages)})
    return _extract_sql_result_from_output(output, dialect=dialect)


__all__ = [
    "DEFAULT_SQL_GENERATOR_SKILLS",
    "agenerate_sql",
    "clean_sql_query",
    "create_sql_generator_agent",
    "generate_sql",
    "get_sql_generator_subagent",
    "sql_generator_subagent",
]
