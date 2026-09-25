"""Unit tests cho các prompt templates mới thuộc Analytics Engine v4.0.

Kiểm tra:
- ANALYTICS_PLANNER_PROMPT (ChatPromptTemplate, system + human, format_messages)
- EVIDENCE_ANALYZER_PROMPT (ChatPromptTemplate, system + human, format_messages)
- ANALYTICS_PRESENTATION_PROMPT (ChatPromptTemplate, system + human, format_messages)
- Tái xuất khẩu (re-export) đầy đủ qua src.agents.prompts và src.prompts
"""

from langchain_core.prompts import ChatPromptTemplate

import src.prompts as prompts_shortcut
from src.agents.prompts import (
    ANALYTICS_PLANNER_HUMAN_PROMPT,
    ANALYTICS_PLANNER_PROMPT,
    ANALYTICS_PLANNER_SYSTEM_PROMPT,
    ANALYTICS_PRESENTATION_HUMAN_PROMPT,
    ANALYTICS_PRESENTATION_PROMPT,
    ANALYTICS_PRESENTATION_SYSTEM_PROMPT,
    EVIDENCE_ANALYZER_HUMAN_PROMPT,
    EVIDENCE_ANALYZER_PROMPT,
    EVIDENCE_ANALYZER_SYSTEM_PROMPT,
)


def test_analytics_planner_prompt_structure_and_formatting():
    """Kiểm tra cấu trúc và khả năng định dạng của ANALYTICS_PLANNER_PROMPT."""
    assert isinstance(ANALYTICS_PLANNER_PROMPT, ChatPromptTemplate)
    assert len(ANALYTICS_PLANNER_PROMPT.messages) == 2
    assert "TPC-H" in ANALYTICS_PLANNER_SYSTEM_PROMPT
    assert "{max_tasks}" in ANALYTICS_PLANNER_HUMAN_PROMPT

    messages = ANALYTICS_PLANNER_PROMPT.format_messages(
        max_tasks=3,
        question="Tại sao doanh số Q3 giảm?",
        schema_context="Bảng orders, lineitem",
    )
    assert len(messages) == 2
    assert messages[0].type == "system"
    assert messages[1].type == "human"
    assert "Tại sao doanh số Q3 giảm?" in messages[1].content
    assert "Bảng orders, lineitem" in messages[1].content


def test_evidence_analyzer_prompt_structure_and_formatting():
    """Kiểm tra cấu trúc và khả năng định dạng của EVIDENCE_ANALYZER_PROMPT."""
    assert isinstance(EVIDENCE_ANALYZER_PROMPT, ChatPromptTemplate)
    assert len(EVIDENCE_ANALYZER_PROMPT.messages) == 2
    assert "has_enough_evidence" in EVIDENCE_ANALYZER_SYSTEM_PROMPT
    assert "{remaining_budget}" in EVIDENCE_ANALYZER_HUMAN_PROMPT

    messages = EVIDENCE_ANALYZER_PROMPT.format_messages(
        question="Doanh số khu vực Châu Á?",
        goal="Tính doanh số Châu Á",
        remaining_budget=2,
        artifacts_context="- Task task_1: [SUCCESS] SQL: SELECT 1",
    )
    assert len(messages) == 2
    assert messages[0].type == "system"
    assert messages[1].type == "human"
    assert "Doanh số khu vực Châu Á?" in messages[1].content
    assert "ngân sách nhiệm vụ còn lại:\n2" in messages[1].content.lower()


def test_analytics_presentation_prompt_structure_and_formatting():
    """Kiểm tra cấu trúc và khả năng định dạng của ANALYTICS_PRESENTATION_PROMPT."""
    assert isinstance(ANALYTICS_PRESENTATION_PROMPT, ChatPromptTemplate)
    assert len(ANALYTICS_PRESENTATION_PROMPT.messages) == 2
    assert "Business Intelligence" in ANALYTICS_PRESENTATION_SYSTEM_PROMPT
    assert "{findings_summary}" in ANALYTICS_PRESENTATION_HUMAN_PROMPT

    messages = ANALYTICS_PRESENTATION_PROMPT.format_messages(
        question="Top khách hàng chi tiêu lớn nhất?",
        goal="Tìm top khách hàng",
        findings_summary="Khách hàng CUST#001 đứng đầu với 500k USD",
        artifacts_context="- Task task_1: [SUCCESS] SELECT c_name FROM customer",
    )
    assert len(messages) == 2
    assert messages[0].type == "system"
    assert messages[1].type == "human"
    assert "CUST#001" in messages[1].content


def test_prompts_shortcut_reexports():
    """Kiểm tra module src.prompts tái xuất khẩu chuẩn xác các prompt templates."""
    assert hasattr(prompts_shortcut, "ANALYTICS_PLANNER_PROMPT")
    assert hasattr(prompts_shortcut, "EVIDENCE_ANALYZER_PROMPT")
    assert hasattr(prompts_shortcut, "ANALYTICS_PRESENTATION_PROMPT")
    assert hasattr(prompts_shortcut, "SUPERVISOR_SYSTEM_PROMPT")
    assert hasattr(prompts_shortcut, "SQL_GENERATOR_PROMPT")
