"""Bộ kiểm thử Deep Agent Supervisor (Component 4.3).

Tuân thủ quy trình TDD:
- Kiểm tra danh sách subagent chuẩn hóa: schema-retriever, sql-generator, control-pipeline, response-synthesizer.
- Kiểm tra hàm khởi tạo create_text2sql_supervisor với middleware (TodoListMiddleware), skills, memory.
- Kiểm tra đăng ký công cụ hoạch định 'write_todos' và ủy quyền 'task'.
- Kiểm tra luồng chạy run_supervisor / arun_supervisor tích hợp SessionTracer và Pre-flight Gatekeeper.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.graph.state import CompiledStateGraph

from src.agents.supervisor import (
    arun_supervisor,
    create_text2sql_supervisor,
    get_supervisor_subagents,
    run_supervisor,
)
from src.models.rbac import UserContext, UserRole
from src.models.state import ClarificationResult
from src.utils.session_tracer import SessionTracer


@pytest.fixture
def mock_analyst_user() -> UserContext:
    """Fixture cung cấp UserContext Analyst phục vụ kiểm thử."""
    return UserContext(
        user_id="analyst_test_01",
        session_id="test_sess_supervisor",
        role=UserRole.ANALYST,
    )


@pytest.fixture
def fake_llm() -> FakeListChatModel:
    """Fixture cung cấp FakeListChatModel với các phản hồi mẫu."""
    return FakeListChatModel(
        responses=[
            "Tôi đã nhận được yêu cầu. Đang lập kế hoạch.",
            "Kế hoạch hoàn tất. Đang chuyển giao tác vụ.",
            "Hoàn tất trả lời câu hỏi nghiệp vụ.",
        ]
    )


def test_get_supervisor_subagents(fake_llm):
    """Kiểm tra khởi tạo danh sách 4 subagent chuyên biệt cho Supervisor."""
    subagents = get_supervisor_subagents(
        tier1_model=fake_llm,
        tier2_model=fake_llm,
    )
    assert len(subagents) == 4

    subagent_names = [sub["name"] for sub in subagents]
    assert "schema-retriever" in subagent_names
    assert "sql-generator" in subagent_names
    assert "control-pipeline" in subagent_names
    assert "response-synthesizer" in subagent_names

    for sub in subagents:
        assert sub["mode"] == "isolated"
        assert "description" in sub
        assert len(sub["description"]) > 10


def test_create_text2sql_supervisor_graph_structure(fake_llm):
    """Kiểm tra cấu trúc StateGraph của Deep Agent Supervisor sau khi compile."""
    subagents = get_supervisor_subagents(tier1_model=fake_llm, tier2_model=fake_llm)
    agent = create_text2sql_supervisor(
        model=fake_llm,
        subagents=subagents,
        skills=["skills/tpch-analytics", "skills/duckdb-sql"],
        memory=["AGENTS.md"],
    )

    assert isinstance(agent, CompiledStateGraph)

    # Kiểm tra sự hiện diện của các middleware thiết yếu trong StateGraph nodes
    node_keys = list(agent.nodes.keys())
    assert "model" in node_keys
    assert "tools" in node_keys
    assert "TodoListMiddleware.after_model" in node_keys
    assert "ToolCallLimitMiddleware.after_model" in node_keys
    assert "ModelCallLimitMiddleware.after_model" in node_keys
    assert "SkillsMiddleware.before_agent" in node_keys
    assert "MemoryMiddleware.before_agent" in node_keys

    # Kiểm tra các công cụ đăng ký trong tools node
    tools_node = agent.nodes["tools"]
    tool_names = list(tools_node.bound.tools_by_name.keys())
    assert "write_todos" in tool_names
    assert "task" in tool_names


def test_create_text2sql_supervisor_custom_skills_and_memory(fake_llm):
    """Kiểm tra khả năng tùy biến skills và memory cho Deep Agent Supervisor."""
    subagents = get_supervisor_subagents(tier1_model=fake_llm, tier2_model=fake_llm)
    agent = create_text2sql_supervisor(
        model=fake_llm,
        subagents=subagents,
        skills=[],
        memory=[],
        name="custom-text2sql-supervisor",
    )
    assert isinstance(agent, CompiledStateGraph)
    node_keys = list(agent.nodes.keys())
    # Khi skills và memory rỗng, middleware tương ứng không được đưa vào graph
    assert "SkillsMiddleware.before_agent" not in node_keys
    assert "MemoryMiddleware.before_agent" not in node_keys
    # TodoListMiddleware và Limit Middleware vẫn luôn luôn hoạt động
    assert "TodoListMiddleware.after_model" in node_keys
    assert "ToolCallLimitMiddleware.after_model" in node_keys
    assert "ModelCallLimitMiddleware.after_model" in node_keys


def test_supervisor_limits_configuration():
    """Kiểm tra giá trị cấu hình mặc định của tool và model call limits từ Settings."""
    from src.config import get_settings

    settings = get_settings()
    assert settings.supervisor_tool_call_limit == 20
    assert settings.supervisor_tool_call_thread_limit == 100
    assert settings.supervisor_model_call_limit == 20
    assert settings.supervisor_model_call_thread_limit == 100


def test_run_supervisor_fast_path_clarification(mock_analyst_user, tmp_path: Path):
    """Kiểm tra Fast-Path Gatekeeper trả về câu hỏi làm rõ khi phát hiện câu hỏi mơ hồ."""
    ambiguous_question = "Cho tôi xem một vài số liệu"

    clarification_mock = ClarificationResult(
        needs_clarification=True,
        reason="VAGUE_METRIC",
        clarification_question="Bạn muốn xem số liệu doanh thu hay số lượng đơn hàng?",
        suggested_options=["A. Doanh thu theo năm", "B. Số lượng đơn hàng theo quý"],
    )

    tracer = SessionTracer(session_id="sess_clarify_test", base_dir=tmp_path)

    with patch(
        "src.agents.supervisor.check_clarification_needed",
        return_value=clarification_mock,
    ):
        result = run_supervisor(
            question=ambiguous_question,
            user_context=mock_analyst_user,
            tracer=tracer,
        )

        assert result["status"] == "CLARIFICATION_REQUIRED"
        assert result["is_ambiguous"] is True
        assert result["clarification_question"] == clarification_mock.clarification_question
        assert len(result["suggested_options"]) == 2
        assert result["data"] is None

        # Kiểm tra SessionTracer đã ghi nhận artifact và summary
        trace_dir = tracer.get_trace_dir()
        assert trace_dir is not None
        assert (trace_dir / "01_clarification.json").exists()
        assert (trace_dir / "metadata.json").exists()


def test_run_supervisor_execution_flow(mock_analyst_user, fake_llm, tmp_path: Path):
    """Kiểm tra luồng thực thi run_supervisor đồng bộ với câu hỏi rõ ràng."""
    clear_question = "Top 5 khách hàng có tổng chi tiêu cao nhất"

    clarification_mock = ClarificationResult(
        needs_clarification=False,
    )

    tracer = SessionTracer(session_id="sess_exec_test", base_dir=tmp_path)

    # Mock agent invoke trả về messages
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "messages": [
            MagicMock(content="Đã phân tích xong câu hỏi."),
            MagicMock(content="Top 5 khách hàng chi tiêu cao nhất gồm Customer#001, Customer#002..."),
        ]
    }

    with (
        patch(
            "src.agents.supervisor.check_clarification_needed",
            return_value=clarification_mock,
        ),
        patch(
            "src.agents.supervisor.create_text2sql_supervisor",
            return_value=mock_agent,
        ),
    ):
        result = run_supervisor(
            question=clear_question,
            user_context=mock_analyst_user,
            tracer=tracer,
            agent=mock_agent,
        )

        assert result["status"] == "COMPLETED"
        assert result["question"] == clear_question
        assert result["session_id"] == mock_analyst_user.session_id
        assert len(result["messages"]) == 2

        # Kiểm tra SessionTracer đã lưu trace đầy đủ
        trace_dir = tracer.get_trace_dir()
        assert trace_dir is not None
        assert (trace_dir / "metadata.json").exists()


@pytest.mark.asyncio
async def test_arun_supervisor_execution_flow(mock_analyst_user, fake_llm, tmp_path: Path):
    """Kiểm tra hàm bất đồng bộ arun_supervisor tương thích FastAPI endpoint."""
    clear_question = "Tổng doanh thu năm 1995 là bao nhiêu?"

    clarification_mock = ClarificationResult(
        needs_clarification=False,
    )

    tracer = SessionTracer(session_id="sess_async_test", base_dir=tmp_path)

    mock_agent = MagicMock()
    from unittest.mock import AsyncMock

    mock_agent.ainvoke = AsyncMock(
        return_value={
            "messages": [
                MagicMock(content="Doanh thu năm 1995 đạt 15,200,000 USD."),
            ]
        }
    )

    with (
        patch(
            "src.agents.supervisor.check_clarification_needed",
            return_value=clarification_mock,
        ),
        patch(
            "src.agents.supervisor.create_text2sql_supervisor",
            return_value=mock_agent,
        ),
    ):
        result = await arun_supervisor(
            question=clear_question,
            user_context=mock_analyst_user,
            tracer=tracer,
            agent=mock_agent,
        )

        assert result["status"] == "COMPLETED"
        assert result["session_id"] == mock_analyst_user.session_id
        trace_dir = tracer.get_trace_dir()
        assert trace_dir is not None
        assert (trace_dir / "metadata.json").exists()


def test_supervisor_invoke_with_mock_model(mock_analyst_user):
    """Kiểm tra đồ thị create_text2sql_supervisor thực thi invoke thành công qua DeepAgents harness."""
    from langchain_core.messages import HumanMessage

    class ToolAwareFakeChatModel(FakeListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    fake_model = ToolAwareFakeChatModel(
        responses=["Tôi là Supervisor. Đã hoàn tất xử lý câu hỏi."]
    )
    subagents = get_supervisor_subagents(tier1_model=fake_model, tier2_model=fake_model)
    agent = create_text2sql_supervisor(
        model=fake_model,
        subagents=subagents,
    )
    config = {"configurable": {"thread_id": "test_thread_invoke"}}
    input_state = {"messages": [HumanMessage(content="Xin chào")]}
    output = agent.invoke(input_state, config=config, context=mock_analyst_user)

    assert "messages" in output
    assert len(output["messages"]) >= 2
    assert "Supervisor" in output["messages"][-1].content

