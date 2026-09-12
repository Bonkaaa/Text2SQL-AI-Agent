"""Unit tests cho Component 3.1: SQL Prompt Engineering & Dialect Adapter."""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from src.agents.prompts.sql_generator_prompt import (
    SQL_GENERATOR_HUMAN_PROMPT,
    SQL_GENERATOR_PROMPT,
    SQL_GENERATOR_RETRY_HUMAN_PROMPT,
    SQL_GENERATOR_RETRY_PROMPT,
    SQL_GENERATOR_SYSTEM_PROMPT,
    SUPPORTED_DIALECTS,
    get_dialect_rules,
    transpile_sql,
)
from src.models.state import SQLGenerationResult


def test_sql_generation_result_model():
    """Kiểm tra validation và giá trị mặc định của Pydantic model SQLGenerationResult."""
    result = SQLGenerationResult(
        sql="SELECT o_orderkey, o_totalprice FROM orders LIMIT 10;",
        explanation="Lấy 10 đơn hàng mẫu để kiểm tra dữ liệu.",
        assumptions=["Không áp dụng bộ lọc theo ngày đặt hàng"],
    )

    assert result.sql == "SELECT o_orderkey, o_totalprice FROM orders LIMIT 10;"
    assert result.dialect == "duckdb"
    assert result.explanation == "Lấy 10 đơn hàng mẫu để kiểm tra dữ liệu."
    assert result.assumptions == ["Không áp dụng bộ lọc theo ngày đặt hàng"]

    # Kiểm tra dialect bigquery hợp lệ
    bq_result = SQLGenerationResult(
        sql="SELECT c_custkey FROM customer LIMIT 5;",
        dialect="bigquery",
        explanation="Lấy khách hàng trên BigQuery.",
    )
    assert bq_result.dialect == "bigquery"
    assert bq_result.assumptions == []

    # Kiểm tra thiếu trường bắt buộc
    with pytest.raises(ValidationError):
        SQLGenerationResult(sql="SELECT 1;")  # thiếu explanation


def test_dialect_adapter_rules():
    """Kiểm tra hàm get_dialect_rules trả về đúng hướng dẫn cho từng dialect."""
    assert "duckdb" in SUPPORTED_DIALECTS
    assert "bigquery" in SUPPORTED_DIALECTS

    duckdb_rules = get_dialect_rules("duckdb")
    assert "DuckDB" in duckdb_rules
    assert "DATE" in duckdb_rules or "CAST" in duckdb_rules
    assert "INTERVAL" in duckdb_rules

    bq_rules = get_dialect_rules("bigquery")
    assert "BigQuery" in bq_rules
    assert "DATE" in bq_rules

    # Dialect không xác định -> fallback về duckdb
    fallback_rules = get_dialect_rules("unknown_warehouse")
    assert "DuckDB" in fallback_rules


def test_dialect_adapter_transpile():
    """Kiểm tra hàm transpile_sql chuyển đổi cú pháp SQL giữa các dialect qua sqlglot."""
    duckdb_sql = "SELECT CAST('1995-01-01' AS DATE) AS order_date FROM orders LIMIT 10;"
    transpiled = transpile_sql(duckdb_sql, from_dialect="duckdb", to_dialect="bigquery")

    assert isinstance(transpiled, str)
    assert "SELECT" in transpiled
    assert "LIMIT 10" in transpiled or "limit 10" in transpiled.lower()

    # Thử câu lệnh lỗi cú pháp -> trả về nguyên bản kèm giữ an toàn (fail-safe)
    invalid_sql = "SELECT FROM WHERE"
    assert (
        transpile_sql(invalid_sql, from_dialect="duckdb", to_dialect="bigquery")
        == invalid_sql
    )


def test_sql_generator_prompt_structure():
    """Kiểm tra cấu trúc ChatPromptTemplate của SQL_GENERATOR_PROMPT."""
    assert isinstance(SQL_GENERATOR_PROMPT, ChatPromptTemplate)
    assert "SQL Generator" in SQL_GENERATOR_SYSTEM_PROMPT
    assert "TPC-H" in SQL_GENERATOR_SYSTEM_PROMPT
    assert "SELECT" in SQL_GENERATOR_SYSTEM_PROMPT
    assert (
        "dbt Semantic Metrics" in SQL_GENERATOR_SYSTEM_PROMPT
        or "công thức" in SQL_GENERATOR_SYSTEM_PROMPT.lower()
    )
    assert "{question}" in SQL_GENERATOR_HUMAN_PROMPT
    assert "{schema_context}" in SQL_GENERATOR_HUMAN_PROMPT
    assert "{dialect_rules}" in SQL_GENERATOR_HUMAN_PROMPT

    expected_vars = {"question", "schema_context", "dialect_rules"}
    assert set(SQL_GENERATOR_PROMPT.input_variables) == expected_vars
    assert len(SQL_GENERATOR_PROMPT.messages) == 2


def test_sql_generator_prompt_format_messages():
    """Kiểm tra format message cho lần sinh SQL đầu tiên."""
    messages = SQL_GENERATOR_PROMPT.format_messages(
        question="Thống kê top 5 khách hàng có tổng doanh thu lớn nhất",
        schema_context="Bảng customer: c_custkey, c_name. Bảng orders: o_orderkey, o_custkey, o_totalprice.",
        dialect_rules=get_dialect_rules("duckdb"),
    )

    assert len(messages) == 2
    system_msg, human_msg = messages[0], messages[1]

    assert isinstance(system_msg, SystemMessage)
    assert "SQL Generator" in system_msg.content
    assert "QUY TẮC VÀNG" in system_msg.content or "GUARDRAILS" in system_msg.content

    assert isinstance(human_msg, HumanMessage)
    assert "Thống kê top 5 khách hàng" in human_msg.content
    assert "Bảng customer" in human_msg.content
    assert "DuckDB" in human_msg.content


def test_sql_generator_retry_prompt_structure():
    """Kiểm tra cấu trúc và input variables của SQL_GENERATOR_RETRY_PROMPT."""
    assert isinstance(SQL_GENERATOR_RETRY_PROMPT, ChatPromptTemplate)
    assert "{question}" in SQL_GENERATOR_RETRY_HUMAN_PROMPT
    assert "{schema_context}" in SQL_GENERATOR_RETRY_HUMAN_PROMPT
    assert "{dialect_rules}" in SQL_GENERATOR_RETRY_HUMAN_PROMPT
    assert "{failed_sql}" in SQL_GENERATOR_RETRY_HUMAN_PROMPT
    assert "{error_type}" in SQL_GENERATOR_RETRY_HUMAN_PROMPT
    assert "{error_message}" in SQL_GENERATOR_RETRY_HUMAN_PROMPT
    assert "{actionable_feedback}" in SQL_GENERATOR_RETRY_HUMAN_PROMPT

    expected_vars = {
        "question",
        "schema_context",
        "dialect_rules",
        "failed_sql",
        "error_type",
        "error_message",
        "actionable_feedback",
    }
    assert set(SQL_GENERATOR_RETRY_PROMPT.input_variables) == expected_vars
    assert len(SQL_GENERATOR_RETRY_PROMPT.messages) == 2


def test_sql_generator_retry_prompt_format_messages():
    """Kiểm tra format message cho lần thử lại sửa lỗi (Retry Loop với Actionable Feedback)."""
    messages = SQL_GENERATOR_RETRY_PROMPT.format_messages(
        question="Lấy số điện thoại và tên khách hàng ngành ô tô",
        schema_context="Bảng customer: c_custkey, c_name, c_phone (PII cấm truy cập theo RBAC), c_mktsegment",
        dialect_rules=get_dialect_rules("duckdb"),
        failed_sql="SELECT c_name, c_phone FROM customer WHERE c_mktsegment = 'AUTOMOBILE'",
        error_type="UNAUTHORIZED_COLUMN",
        error_message="Cột 'c_phone' bị từ chối truy cập cho vai trò Analyst theo RBAC Policy",
        actionable_feedback="Loại bỏ cột 'c_phone' khỏi SELECT và thay thế bằng 'c_custkey' hoặc 'c_name'.",
    )

    assert len(messages) == 2
    system_msg, human_msg = messages[0], messages[1]

    assert isinstance(system_msg, SystemMessage)
    assert isinstance(human_msg, HumanMessage)
    assert "CÂU LỆNH SQL VỪA GẶP LỖI" in human_msg.content
    assert "SELECT c_name, c_phone FROM customer" in human_msg.content
    assert "UNAUTHORIZED_COLUMN" in human_msg.content
    assert (
        "CHỈ DẪN SỬA LỖI TỪ HỆ THỐNG KIỂM SOÁT (ACTIONABLE FEEDBACK):"
        in human_msg.content
    )
    assert "Loại bỏ cột 'c_phone'" in human_msg.content


def test_prompts_reexports():
    """Kiểm tra các biến prompt được re-export chính xác qua __init__.py và src/prompts.py."""
    from src.agents.prompts import (
        SQL_GENERATOR_HUMAN_PROMPT as RE_HUMAN,
    )
    from src.agents.prompts import (
        SQL_GENERATOR_PROMPT as RE_PROMPT,
    )
    from src.agents.prompts import (
        SQL_GENERATOR_RETRY_HUMAN_PROMPT as RE_RETRY_HUMAN,
    )
    from src.agents.prompts import (
        SQL_GENERATOR_RETRY_PROMPT as RE_RETRY_PROMPT,
    )
    from src.agents.prompts import (
        SQL_GENERATOR_SYSTEM_PROMPT as RE_SYSTEM,
    )
    from src.agents.prompts import (
        get_dialect_rules as RE_GET_RULES,
    )
    from src.agents.prompts import (
        transpile_sql as RE_TRANSPILE,
    )
    from src.prompts import (
        SQL_GENERATOR_PROMPT as SHORTCUT_PROMPT,
    )
    from src.prompts import (
        SQL_GENERATOR_RETRY_PROMPT as SHORTCUT_RETRY_PROMPT,
    )

    assert RE_PROMPT is SQL_GENERATOR_PROMPT
    assert RE_RETRY_PROMPT is SQL_GENERATOR_RETRY_PROMPT
    assert RE_SYSTEM is SQL_GENERATOR_SYSTEM_PROMPT
    assert RE_HUMAN is SQL_GENERATOR_HUMAN_PROMPT
    assert RE_RETRY_HUMAN is SQL_GENERATOR_RETRY_HUMAN_PROMPT
    assert RE_GET_RULES is get_dialect_rules
    assert RE_TRANSPILE is transpile_sql
    assert SHORTCUT_PROMPT is SQL_GENERATOR_PROMPT
    assert SHORTCUT_RETRY_PROMPT is SQL_GENERATOR_RETRY_PROMPT
