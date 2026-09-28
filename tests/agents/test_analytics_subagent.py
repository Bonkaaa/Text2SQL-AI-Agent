"""Unit tests cho CompiledSubAgent analytics-subagent (Phase 4 - Component 4.1).

Kiểm thử việc đóng gói Analytics LangGraph Subgraph thành một CompiledSubAgent
mà Deep Agent Master Supervisor có thể ủy quyền qua công cụ task('analytics-subagent', ...).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.analytics import (
    create_analytics_subagent_runnable,
    get_analytics_subagent,
)
from src.models.artifacts import KpiArtifact, QueryArtifact, ResponsePackage
from src.models.rbac import UserContext, UserRole


def test_get_analytics_subagent_structure():
    """Kiểm tra cấu trúc CompiledSubAgent của analytics-subagent."""
    subagent = get_analytics_subagent()
    assert subagent["name"] == "analytics-subagent"
    assert subagent["mode"] == "isolated"
    assert "description" in subagent
    assert len(subagent["description"]) > 20
    assert "runnable" in subagent
    assert callable(getattr(subagent["runnable"], "invoke", None))
    assert callable(getattr(subagent["runnable"], "ainvoke", None))


@pytest.mark.asyncio
async def test_analytics_subagent_async_runner():
    """Kiểm tra thực thi bất đồng bộ của analytics-subagent runnable."""
    mock_pkg = ResponsePackage(
        package_id="pkg_test_01",
        session_id="sess_subagent_test",
        direct_answer="Doanh thu năm 1995 tăng trưởng 12%.",
        artifacts=[
            KpiArtifact(
                title="Tổng doanh thu",
                value="1.2M",
            )
        ],
    )
    mock_artifact = QueryArtifact(
        artifact_id="q_art_01",
        task_id="task_1",
        sql="SELECT sum(l_extendedprice) FROM lineitem",
        status="SUCCESS",
        data=[{"revenue": 1200000.0}],
        columns=["revenue"],
        row_count=1,
    )

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "response_package": mock_pkg,
            "insight": "Doanh thu năm 1995 tăng trưởng 12%.",
            "artifacts": [mock_artifact],
            "status": "COMPLETED",
        }
    )

    runnable = create_analytics_subagent_runnable(graph=mock_graph)

    input_state = {
        "messages": [HumanMessage(content="Phân tích doanh thu năm 1995")],
        "session_id": "sess_subagent_test",
        "user_context": UserContext(
            user_id="analyst_test",
            session_id="sess_subagent_test",
            role=UserRole.ANALYST,
        ),
    }

    result = await runnable.ainvoke(input_state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert "Doanh thu năm 1995" in result["messages"][0].content
    assert result["status"] == "COMPLETED"
    assert result["sql"] == "SELECT sum(l_extendedprice) FROM lineitem"
    assert result["data"] == [{"revenue": 1200000.0}]
    assert result["columns"] == ["revenue"]
    assert "response_package" in result
    assert len(result["output_artifacts"]) == 1
