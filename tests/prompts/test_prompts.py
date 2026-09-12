"""Unit tests kiểm tra module Prompts tập trung."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agents.prompts import (
    ERROR_DIAGNOSTIC_HUMAN_PROMPT,
    ERROR_DIAGNOSTIC_PROMPT,
    ERROR_DIAGNOSTIC_SYSTEM_PROMPT,
    SCHEMA_RETRIEVER_HUMAN_PROMPT,
    SCHEMA_RETRIEVER_PROMPT,
    SCHEMA_RETRIEVER_SYSTEM_PROMPT,
)
from src.prompts import (
    ERROR_DIAGNOSTIC_PROMPT as REEXPORTED_PROMPT,
)
from src.prompts import (
    SCHEMA_RETRIEVER_PROMPT as REEXPORTED_SCHEMA_PROMPT,
)


def test_error_diagnostic_prompt_structure():
    """Kiểm tra cấu trúc và kiểu của ERROR_DIAGNOSTIC_PROMPT."""
    assert isinstance(ERROR_DIAGNOSTIC_PROMPT, ChatPromptTemplate)
    assert ERROR_DIAGNOSTIC_PROMPT is REEXPORTED_PROMPT
    assert "chuyên gia chẩn đoán lỗi SQL" in ERROR_DIAGNOSTIC_SYSTEM_PROMPT
    assert "DiagnosticResult" in ERROR_DIAGNOSTIC_SYSTEM_PROMPT
    assert "error_category" in ERROR_DIAGNOSTIC_SYSTEM_PROMPT
    assert "{sql}" in ERROR_DIAGNOSTIC_HUMAN_PROMPT

    # Kiểm tra input variables
    expected_vars = {"sql", "error_type", "error_message", "schema_context"}
    assert set(ERROR_DIAGNOSTIC_PROMPT.input_variables) == expected_vars

    # Kiểm tra có đúng 2 message templates: SystemMessage & HumanMessage
    assert len(ERROR_DIAGNOSTIC_PROMPT.messages) == 2


def test_error_diagnostic_prompt_format_messages():
    """Kiểm tra việc format message có chứa đầy đủ nội dung System và Human."""
    messages = ERROR_DIAGNOSTIC_PROMPT.format_messages(
        sql="SELECT c_phone FROM customer",
        error_type="UNAUTHORIZED_COLUMN",
        error_message="Cột c_phone bị cấm truy cập theo RBAC",
        schema_context="Bảng customer: c_custkey, c_name, c_phone (PII)",
    )

    assert len(messages) == 2
    system_msg, human_msg = messages[0], messages[1]

    # Kiểm tra SystemMessage
    assert isinstance(system_msg, SystemMessage)
    assert "chuyên gia chẩn đoán lỗi SQL" in system_msg.content
    assert "QUY TẮC PHẢN HỒI" in system_msg.content

    # Kiểm tra HumanMessage
    assert isinstance(human_msg, HumanMessage)
    assert "SELECT c_phone FROM customer" in human_msg.content
    assert "UNAUTHORIZED_COLUMN" in human_msg.content
    assert "Cột c_phone bị cấm truy cập theo RBAC" in human_msg.content
    assert "Bảng customer: c_custkey, c_name, c_phone (PII)" in human_msg.content


def test_schema_retriever_prompt_structure():
    """Kiểm tra cấu trúc và input variables của SCHEMA_RETRIEVER_PROMPT."""
    assert isinstance(SCHEMA_RETRIEVER_PROMPT, ChatPromptTemplate)
    assert SCHEMA_RETRIEVER_PROMPT is REEXPORTED_SCHEMA_PROMPT
    assert "Schema & Value Retriever" in SCHEMA_RETRIEVER_SYSTEM_PROMPT
    assert "VAI TRÒ & PHẠM VI" in SCHEMA_RETRIEVER_SYSTEM_PROMPT
    assert "QUY TẮC DÙNG TOOL" in SCHEMA_RETRIEVER_SYSTEM_PROMPT
    assert "{question}" in SCHEMA_RETRIEVER_HUMAN_PROMPT
    assert "{selected_tables}" in SCHEMA_RETRIEVER_HUMAN_PROMPT

    expected_vars = {"question", "selected_tables"}
    assert set(SCHEMA_RETRIEVER_PROMPT.input_variables) == expected_vars
    assert len(SCHEMA_RETRIEVER_PROMPT.messages) == 2


def test_schema_retriever_prompt_format_messages():
    """Kiểm tra format message cho Schema Retriever."""
    messages = SCHEMA_RETRIEVER_PROMPT.format_messages(
        question="Thống kê doanh thu ngành ô tô",
        selected_tables="['customer', 'orders', 'lineitem']",
    )

    assert len(messages) == 2
    system_msg, human_msg = messages[0], messages[1]

    assert isinstance(system_msg, SystemMessage)
    assert "Schema & Value Retriever" in system_msg.content
    assert "QUY TẮC DÙNG TOOL" in system_msg.content
    assert "OUTPUT CONTRACT" in system_msg.content

    assert isinstance(human_msg, HumanMessage)
    assert "Thống kê doanh thu ngành ô tô" in human_msg.content
    assert "['customer', 'orders', 'lineitem']" in human_msg.content


def test_agent_specific_prompt_imports():
    """Kiểm tra import trực tiếp từ các file prompt con theo từng agent."""
    from src.agents.prompts.error_diagnostic_prompt import (
        ERROR_DIAGNOSTIC_PROMPT as DIAG_PROMPT,
    )
    from src.agents.prompts.schema_retriever_prompt import (
        SCHEMA_RETRIEVER_PROMPT as RETRIEVER_PROMPT,
    )
    from src.agents.prompts.sql_generator_prompt import (
        SQL_GENERATOR_PROMPT as GEN_PROMPT,
    )

    assert DIAG_PROMPT is ERROR_DIAGNOSTIC_PROMPT
    assert RETRIEVER_PROMPT is SCHEMA_RETRIEVER_PROMPT
    assert GEN_PROMPT is not None
