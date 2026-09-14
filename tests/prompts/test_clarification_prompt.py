"""Unit tests cho Component 4.1: Clarification Prompt Engineering."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agents.prompts.clarification_prompt import (
    CLARIFICATION_HUMAN_PROMPT,
    CLARIFICATION_PROMPT,
    CLARIFICATION_SYSTEM_PROMPT,
)


def test_clarification_prompt_structure():
    """Kiểm tra cấu trúc ChatPromptTemplate và các thành phần template của Clarification Agent."""
    assert isinstance(CLARIFICATION_PROMPT, ChatPromptTemplate)
    assert len(CLARIFICATION_PROMPT.messages) == 2

    # Kiểm tra nội dung System Prompt
    assert "chuyên gia phân tích nghiệp vụ" in CLARIFICATION_SYSTEM_PROMPT.lower()
    assert "mơ hồ" in CLARIFICATION_SYSTEM_PROMPT.lower()
    assert "rõ ràng" in CLARIFICATION_SYSTEM_PROMPT.lower()
    assert "suggested_options" in CLARIFICATION_SYSTEM_PROMPT.lower()
    assert "needs_clarification" in CLARIFICATION_SYSTEM_PROMPT

    # Kiểm tra biến đầu vào của Human Prompt
    assert "{question}" in CLARIFICATION_HUMAN_PROMPT
    assert "question" in CLARIFICATION_PROMPT.input_variables


def test_clarification_prompt_format_messages():
    """Kiểm tra việc render messages từ template khi truyền câu hỏi người dùng."""
    test_question = "Doanh thu công ty dạo này thế nào?"
    messages = CLARIFICATION_PROMPT.format_messages(question=test_question)

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert test_question in messages[1].content
