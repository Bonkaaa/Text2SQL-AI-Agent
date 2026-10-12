"""Unit tests cho Component 3.2: Subagent & DeepAgent SQL Generator."""

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph.state import CompiledStateGraph

from src.agents.prompts import SQL_GENERATOR_SYSTEM_PROMPT
from src.agents.sql_generator import (
    agenerate_sql,
    clean_sql_query,
    create_sql_generator_agent,
    generate_sql,
    get_sql_generator_subagent,
    sql_generator_subagent,
)
from src.models.state import SQLGenerationResult

# ==============================================================================
# MOCK CHAT MODELS HỖ TRỢ DEEPAGENT
# ==============================================================================


class ToolAwareFakeChatModel(FakeListChatModel):
    """FakeChatModel hỗ trợ bind_tools cho DeepAgent harness."""

    def bind_tools(self, tools, **kwargs):
        return self


class DeepAgentStructuredMockChat(BaseChatModel):
    """Mock Chat Model mô phỏng việc sinh structured tool call cho DeepAgent."""

    sql_result: SQLGenerationResult

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "SQLGenerationResult",
                    "args": self.sql_result.model_dump(),
                    "id": "call_structured_1",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "deepagent-structured-mock"


class MultiStepMockChat(BaseChatModel):
    """Mock Chat Model mô phỏng 2 bước: gọi metadata tool rồi gọi response_format tool."""

    step: int = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.step == 0:
            self.step += 1
            ai_msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "find_join_path",
                        "args": {"table_a": "customer", "table_b": "orders"},
                        "id": "call_join_1",
                    }
                ],
            )
            return ChatResult(generations=[ChatGeneration(message=ai_msg)])

        payload = {
            "sql": "SELECT c.c_name, o.o_totalprice FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey;",
            "thought_process": "Đã nối customer và orders qua c_custkey",
            "explanation": "Nối bảng customer và orders theo khóa ngoại.",
            "confidence_score": 0.98,
            "dialect": "duckdb",
        }
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "SQLGenerationResult",
                    "args": payload,
                    "id": "call_done_2",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "multi-step-mock"


# ==============================================================================
# UNIT TESTS: SUBAGENT SPECIFICATION & HELPERS
# ==============================================================================


def test_subagent_dict_structure():
    """Kiểm tra cấu trúc Dictionary của SubAgent SQL Generator theo chuẩn DeepAgents."""
    assert isinstance(sql_generator_subagent, dict)
    assert sql_generator_subagent["name"] == "sql-generator"
    assert "suy luận và sinh câu lệnh SQL" in sql_generator_subagent["description"]
    assert sql_generator_subagent["system_prompt"] == SQL_GENERATOR_SYSTEM_PROMPT
    assert sql_generator_subagent["mode"] == "isolated"
    assert len(sql_generator_subagent["tools"]) == 4
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


# ==============================================================================
# UNIT TESTS: DEEPAGENT GRAPH CREATION & STRUCTURE
# ==============================================================================


def test_create_sql_generator_agent_structure():
    """Kiểm tra cấu trúc CompiledStateGraph của DeepAgent SQL Generator."""
    fake_llm = ToolAwareFakeChatModel(responses=[""])
    agent = create_sql_generator_agent(
        model=fake_llm,
        skills=["skills/duckdb-sql", "skills/tpch-analytics"],
    )

    assert isinstance(agent, CompiledStateGraph)

    # Kiểm tra các nodes cần thiết trong StateGraph
    node_keys = list(agent.nodes.keys())
    assert "model" in node_keys
    assert "tools" in node_keys
    assert "SkillsMiddleware.before_agent" in node_keys

    # Kiểm tra các tools gắn vào agent
    tools_node = agent.nodes["tools"]
    tool_names = list(tools_node.bound.tools_by_name.keys())
    assert "search_tables_and_columns" in tool_names
    assert "get_column_samples_and_values" in tool_names
    assert "find_join_path" in tool_names
    assert "search_business_definition" in tool_names


# ==============================================================================
# UNIT TESTS: SYNCHRONOUS RUNNER (generate_sql)
# ==============================================================================


def test_generate_sql_first_attempt_mock_llm():
    """Kiểm tra hàm generate_sql ở lần sinh đầu tiên (first attempt) với Mock LLM."""
    mock_result = SQLGenerationResult(
        sql="SELECT c_name, c_mktsegment FROM customer WHERE c_mktsegment = 'BUILDING';",
        dialect="duckdb",
        explanation="Lấy danh sách khách hàng thuộc phân khúc BUILDING.",
        assumptions=[],
    )

    mock_llm = DeepAgentStructuredMockChat(sql_result=mock_result)

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


def test_generate_sql_retry_flow_mock_llm():
    """Kiểm tra hàm generate_sql ở lượt retry khi có error_context và actionable_feedback."""
    mock_fixed_result = SQLGenerationResult(
        sql="SELECT c_name, c_mktsegment FROM customer WHERE c_mktsegment = 'AUTOMOBILE';",
        dialect="duckdb",
        explanation="Đã loại bỏ cột c_phone vi phạm chính sách RBAC.",
        assumptions=["Thay thế c_phone bằng c_name"],
    )

    mock_llm = DeepAgentStructuredMockChat(sql_result=mock_fixed_result)

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


def test_generate_sql_cleans_wrapped_markdown_sql():
    """Kiểm tra generate_sql tự động làm sạch trường sql nếu LLM vô tình bọc trong markdown."""
    mock_result_with_markdown = SQLGenerationResult(
        sql="```sql\nSELECT count(*) FROM orders;\n```",
        dialect="duckdb",
        explanation="Đếm số lượng đơn hàng.",
        assumptions=[],
    )

    mock_llm = DeepAgentStructuredMockChat(sql_result=mock_result_with_markdown)

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


def test_generate_sql_active_tool_calling_loop():
    """Kiểm tra luồng Active Tool Calling: LLM gọi find_join_path trước khi sinh câu SQL."""
    mock_llm = MultiStepMockChat()

    result = generate_sql(
        question="Lấy tên khách hàng và tổng tiền đơn hàng",
        schema_context="customer, orders",
        llm=mock_llm,
    )

    assert (
        result.sql
        == "SELECT c.c_name, o.o_totalprice FROM customer c JOIN orders o ON c.c_custkey = o.o_custkey;"
    )
    assert result.dialect == "duckdb"
    assert "Nối bảng customer và orders" in result.explanation


# ==============================================================================
# UNIT TESTS: ASYNCHRONOUS RUNNER (agenerate_sql)
# ==============================================================================


@pytest.mark.asyncio
async def test_agenerate_sql_async_flow():
    """Kiểm tra runner bất đồng bộ agenerate_sql qua DeepAgent."""
    mock_result = SQLGenerationResult(
        sql="SELECT count(*) FROM region WHERE r_name = 'ASIA';",
        dialect="duckdb",
        explanation="Đếm số bản ghi khu vực Châu Á.",
        assumptions=[],
    )
    mock_llm = DeepAgentStructuredMockChat(sql_result=mock_result)

    result = await agenerate_sql(
        question="Đếm khu vực Châu Á",
        schema_context="Bảng region",
        dialect="duckdb",
        llm=mock_llm,
    )

    assert isinstance(result, SQLGenerationResult)
    assert result.sql == "SELECT count(*) FROM region WHERE r_name = 'ASIA';"
    assert result.dialect == "duckdb"
