"""Unit tests kiểm tra cơ chế lưu trữ ngữ cảnh hội thoại đa lượt (Multi-turn Context)
và Context Window Guardrail qua LangGraph Checkpointer.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.agents.supervisor import (
    create_text2sql_supervisor,
    get_default_checkpointer,
    reset_default_checkpointer,
    run_supervisor,
)
from src.models.rbac import UserContext, UserRole
from src.models.state import ClarificationResult


@pytest.fixture(autouse=True)
def clean_checkpointer():
    """Tự động reset checkpointer trước và sau mỗi bài test."""
    reset_default_checkpointer()
    yield
    reset_default_checkpointer()


@pytest.fixture
def analyst_user():
    return UserContext(
        user_id="test_analyst",
        session_id="multi_turn_test_session",
        role=UserRole.ANALYST,
    )


def test_checkpointer_singleton_instance():
    """Kiểm tra get_default_checkpointer luôn trả về instance MemorySaver singleton."""
    cp1 = get_default_checkpointer()
    cp2 = get_default_checkpointer()
    assert cp1 is cp2
    assert isinstance(cp1, MemorySaver)


def test_reset_default_checkpointer():
    """Kiểm tra reset_default_checkpointer tạo instance mới sạch sẽ."""
    cp1 = get_default_checkpointer()
    reset_default_checkpointer()
    cp2 = get_default_checkpointer()
    assert cp1 is not cp2


class ToolAwareFakeChatModel(FakeListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def test_multi_turn_context_retention_in_checkpointer(analyst_user):
    """Kiểm tra 2 lượt gọi liên tiếp trên cùng thread_id tích lũy ngữ cảnh lịch sử."""
    fake_model = ToolAwareFakeChatModel(
        responses=[
            "Trả lời lượt 1: Tôi chưa tìm thấy khách hàng ABC.",
            "Trả lời lượt 2: Đã tìm thấy khách hàng Customer#001 dựa trên thông tin bổ sung.",
        ]
    )

    custom_cp = MemorySaver()
    agent = create_text2sql_supervisor(model=fake_model, checkpointer=custom_cp)

    config = {"configurable": {"thread_id": analyst_user.session_id}}

    # Turn 1
    state_turn1 = agent.invoke(
        {"messages": [HumanMessage(content="Lượt 1: Doanh thu của ABC?")]},
        config=config,
        context=analyst_user,
    )
    assert len(state_turn1["messages"]) >= 2
    assert "Lượt 1: Doanh thu của ABC?" in state_turn1["messages"][0].content

    # Turn 2: Cung cấp bổ sung thông tin trên cùng thread_id
    state_turn2 = agent.invoke(
        {"messages": [HumanMessage(content="Lượt 2: ABC là Customer#001.")]},
        config=config,
        context=analyst_user,
    )

    # State của Turn 2 phải tích lũy tin nhắn của cả Turn 1 và Turn 2
    msg_contents = [m.content for m in state_turn2["messages"]]
    assert any("Lượt 1" in c for c in msg_contents)
    assert any("Lượt 2" in c for c in msg_contents)


def test_run_supervisor_uses_shared_checkpointer(analyst_user):
    """Kiểm tra run_supervisor lưu và chia sẻ trạng thái giữa các lần gọi cùng session_id."""
    clarification_mock = ClarificationResult(needs_clarification=False)

    mock_agent = MagicMock()
    mock_agent.invoke.side_effect = [
        {"messages": [HumanMessage(content="Câu 1"), AIMessage(content="Đáp án 1")]},
        {"messages": [HumanMessage(content="Câu 1"), AIMessage(content="Đáp án 1"), HumanMessage(content="Câu 2"), AIMessage(content="Đáp án 2")]},
    ]

    with (
        patch("src.agents.supervisor.check_clarification_needed", return_value=clarification_mock),
        patch("src.agents.supervisor.create_text2sql_supervisor", return_value=mock_agent),
    ):
        res1 = run_supervisor(
            question="Câu 1",
            user_context=analyst_user,
            session_id=analyst_user.session_id,
            skip_clarification=True,
        )
        assert res1["status"] == "COMPLETED"

        res2 = run_supervisor(
            question="Câu 2",
            user_context=analyst_user,
            session_id=analyst_user.session_id,
            skip_clarification=True,
        )
        assert res2["status"] == "COMPLETED"
        assert len(res2["messages"]) == 4


def test_summarization_middleware_integration():
    """Kiểm tra middleware stack có SummarizationMiddleware khi enable_context_summarization=True."""

    fake_model = FakeListChatModel(responses=["ok"])

    with patch("src.agents.supervisor.get_chat_model", return_value=fake_model):
        agent = create_text2sql_supervisor(model=fake_model)
        # SummarizationMiddleware sẽ thêm node tương ứng vào StateGraph
        node_keys = list(agent.nodes.keys())
        assert any("SummarizationMiddleware" in k for k in node_keys)
