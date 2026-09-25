"""Unit tests cho Consultation SubAgent (consultation-agent)."""

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.agents.consultation import get_consultation_subagent
from src.agents.prompts.consultation_prompt import CONSULTATION_SYSTEM_PROMPT


def test_get_consultation_subagent_structure():
    """Kiểm tra cấu trúc SubAgent specification của consultation-agent."""
    subagent = get_consultation_subagent()

    assert isinstance(subagent, dict)
    assert subagent["name"] == "consultation-agent"
    assert "description" in subagent
    assert len(subagent["description"]) > 20
    assert subagent["system_prompt"] == CONSULTATION_SYSTEM_PROMPT

    # Kiểm tra danh sách 3 tools
    tools = subagent.get("tools", [])
    assert len(tools) == 3
    tool_names = [getattr(t, "name", str(t)) for t in tools]
    assert "search_tables_and_columns" in tool_names
    assert "get_column_samples_and_values" in tool_names
    assert "search_business_definition" in tool_names


def test_get_consultation_subagent_custom_model():
    """Kiểm tra chỉ định custom model cho consultation-agent."""
    fake_model = FakeListChatModel(responses=["Xin chào!"])
    subagent = get_consultation_subagent(model=fake_model)

    assert subagent["model"] == fake_model
