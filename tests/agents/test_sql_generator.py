"""Unit tests cho Component 3.2: Subagent SQL Generator."""

from unittest.mock import MagicMock

import pytest

from src.agents.prompts import SQL_GENERATOR_SYSTEM_PROMPT
from src.agents.sql_generator import (
    clean_sql_query,
    generate_sql,
    get_sql_generator_subagent,
    sql_generator_subagent,
)
from src.models.state import SQLGenerationResult


def test_subagent_dict_structure():
    """Kiểm tra cấu trúc Dictionary của SubAgent SQL Generator theo chuẩn DeepAgents."""
    assert isinstance(sql_generator_subagent, dict)
    assert sql_generator_subagent["name"] == "sql-generator"
    assert "suy luận và sinh câu lệnh SQL" in sql_generator_subagent["description"]
    assert sql_generator_subagent["system_prompt"] == SQL_GENERATOR_SYSTEM_PROMPT
    assert sql_generator_subagent["mode"] == "isolated"
    assert sql_generator_subagent["tools"] == []
    assert sql_generator_subagent["response_format"] == SQLGenerationResult
    assert isinstance(sql_generator_subagent["model"], str)
    assert len(sql_generator_subagent["model"]) > 0


def test_get_sql_generator_subagent_custom_model():
    """Kiểm tra việc ghi đè tên mô hình trong get_sql_generator_subagent."""
    custom_subagent = get_sql_generator_subagent(model="openai:gpt-4o")
    assert custom_subagent["name"] == "sql-generator"
    assert custom_subagent["model"] == "openai:gpt-4o"


def test_clean_sql_query_helper():
    """Kiểm tra helper clean_sql_query loại bỏ markdown fences và khoảng trắng."""
    # SQL bọc trong ```sql ... ```
    raw_1 = "```sql\nSELECT c_custkey, c_name FROM customer LIMIT 10;\n```"
    assert clean_sql_query(raw_1) == "SELECT c_custkey, c_name FROM customer LIMIT 10;"

    # SQL bọc trong ``` ... ```
    raw_2 = "```\nSELECT * FROM orders\n```"
    assert clean_sql_query(raw_2) == "SELECT * FROM orders"

    # SQL sạch sẵn có khoảng trắng thừa
    raw_3 = "   SELECT count(*) FROM lineitem;   \n"
    assert clean_sql_query(raw_3) == "SELECT count(*) FROM lineitem;"

    # Chuỗi rỗng
    assert clean_sql_query("") == ""
    assert clean_sql_query("   ") == ""


def test_generate_sql_first_attempt_mock_llm():
    """Kiểm tra hàm generate_sql ở lần sinh đầu tiên (first attempt) với Mock LLM."""
    mock_result = SQLGenerationResult(
        sql="SELECT c_name, c_mktsegment FROM customer WHERE c_mktsegment = 'BUILDING';",
        dialect="duckdb",
        explanation="Lấy danh sách khách hàng thuộc phân khúc BUILDING.",
        assumptions=[],
    )

    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = mock_result

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_runnable

    result = generate_sql(
        question="Lấy thông tin khách hàng phân khúc xây dựng",
        schema_context="Bảng customer: c_custkey, c_name, c_mktsegment",
        dialect="duckdb",
        llm=mock_llm,
    )

    assert isinstance(result, SQLGenerationResult)
    assert (
        result.sql
        == "SELECT c_name, c_mktsegment FROM customer WHERE c_mktsegment = 'BUILDING';"
    )
    assert result.dialect == "duckdb"
    assert result.explanation == "Lấy danh sách khách hàng thuộc phân khúc BUILDING."

    # Xác nhận LLM with_structured_output được gọi với SQLGenerationResult
    mock_llm.with_structured_output.assert_called_once_with(SQLGenerationResult)
    mock_runnable.invoke.assert_called_once()

    # Kiểm tra prompt messages được gửi vào LLM
    call_args = mock_runnable.invoke.call_args[0][0]
    assert len(call_args) == 2  # SystemMessage & HumanMessage
    human_content = call_args[1].content
    assert "Lấy thông tin khách hàng phân khúc xây dựng" in human_content
    assert "Bảng customer" in human_content
    assert "DuckDB" in human_content


def test_generate_sql_retry_flow_mock_llm():
    """Kiểm tra hàm generate_sql ở lượt retry khi có error_context và actionable_feedback."""
    mock_fixed_result = SQLGenerationResult(
        sql="SELECT c_name, c_mktsegment FROM customer WHERE c_mktsegment = 'AUTOMOBILE';",
        dialect="duckdb",
        explanation="Đã loại bỏ cột c_phone vi phạm chính sách RBAC.",
        assumptions=["Thay thế c_phone bằng c_name"],
    )

    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = mock_fixed_result

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_runnable

    error_context = {
        "failed_sql": "SELECT c_name, c_phone FROM customer WHERE c_mktsegment = 'AUTOMOBILE'",
        "error_type": "UNAUTHORIZED_COLUMN",
        "error_message": "Cột c_phone bị cấm truy cập theo RBAC",
        "actionable_feedback": "Loại bỏ cột c_phone và thay thế bằng c_name hoặc c_custkey.",
    }

    result = generate_sql(
        question="Lấy khách hàng ngành ô tô",
        schema_context="Bảng customer: c_custkey, c_name, c_phone (PII), c_mktsegment",
        dialect="duckdb",
        error_context=error_context,
        llm=mock_llm,
    )

    assert isinstance(result, SQLGenerationResult)
    assert "c_phone" not in result.sql
    assert result.explanation == "Đã loại bỏ cột c_phone vi phạm chính sách RBAC."

    # Xác nhận retry prompt messages được gửi vào LLM
    mock_runnable.invoke.assert_called_once()
    call_args = mock_runnable.invoke.call_args[0][0]
    human_content = call_args[1].content
    assert "CÂU LỆNH SQL VỪA GẶP LỖI" in human_content
    assert "SELECT c_name, c_phone FROM customer" in human_content
    assert "UNAUTHORIZED_COLUMN" in human_content
    assert (
        "Loại bỏ cột c_phone và thay thế bằng c_name hoặc c_custkey." in human_content
    )


def test_generate_sql_cleans_wrapped_markdown_sql():
    """Kiểm tra generate_sql tự động làm sạch trường sql nếu LLM vô tình bọc trong markdown."""
    mock_result_with_markdown = SQLGenerationResult(
        sql="```sql\nSELECT count(*) FROM orders;\n```",
        dialect="duckdb",
        explanation="Đếm số lượng đơn hàng.",
        assumptions=[],
    )

    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = mock_result_with_markdown

    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_runnable

    result = generate_sql(
        question="Có bao nhiêu đơn hàng?",
        schema_context="Bảng orders: o_orderkey",
        dialect="duckdb",
        llm=mock_llm,
    )

    assert result.sql == "SELECT count(*) FROM orders;"


def test_generate_sql_missing_llm_raises_error(monkeypatch):
    """Kiểm tra ném ngoại lệ rõ ràng khi không có LLM nào được cấu hình."""
    from src.agents import sql_generator

    # Mock get_chat_model trả về None
    monkeypatch.setattr(sql_generator, "get_chat_model", lambda **kwargs: None)

    with pytest.raises(RuntimeError) as exc_info:
        generate_sql(
            question="Đếm số khách hàng",
            schema_context="Bảng customer",
            llm=None,
        )

    assert "Không thể khởi tạo mô hình Chat Model Tier 1" in str(exc_info.value)
