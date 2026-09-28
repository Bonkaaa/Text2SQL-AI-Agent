"""Integration Test Suite cho API v4.0 Evolution (Component 4.2).

Kiểm thử các tính năng mới trong QueryResponse:
1. SECURITY_BLOCKED: is_safe=False, safety_category, refusal_reason khi bị chặn bảo mật/ngoài miền.
2. ResponsePackage & Output Artifacts: Trả về gói composable artifacts (KPI, Chart, Table) cho Frontend.
3. AnalysisPlan Tasks: Danh sách nhiệm vụ phân tích đa bước.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.models.rbac import UserRole


@pytest.fixture
def anyio_backend():
    """Chỉ định backend asyncio cho anyio / httpx."""
    return "asyncio"


@pytest.mark.asyncio
async def test_ask_query_security_blocked():
    """Kiểm tra API trả về status=SECURITY_BLOCKED khi câu hỏi vi phạm an ninh."""
    mock_supervisor_result = {
        "status": "SECURITY_BLOCKED",
        "question": "DROP TABLE customer;",
        "session_id": "sess_sec_blocked",
        "is_safe": False,
        "safety_category": "UNSAFE_DATA_MUTATION",
        "refusal_reason": "Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin và bảo mật dữ liệu của hệ thống.",
        "final_answer": "Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin và bảo mật dữ liệu của hệ thống.",
        "data": None,
        "columns": None,
        "sql": None,
        "recharts_config": None,
        "execution_time_ms": 1.2,
    }

    with patch(
        "src.api.routes.query.arun_supervisor",
        new_callable=AsyncMock,
        return_value=mock_supervisor_result,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = {
                "question": "DROP TABLE customer;",
                "session_id": "sess_sec_blocked",
                "role": UserRole.ANALYST.value,
            }
            response = await client.post("/api/v1/query/ask", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "SECURITY_BLOCKED"
            assert data["is_safe"] is False
            assert data["safety_category"] == "UNSAFE_DATA_MUTATION"
            assert "vi phạm quy tắc an toàn" in data["refusal_reason"]
            assert data["data"] is None
            assert data["sql"] is None


@pytest.mark.asyncio
async def test_ask_query_with_response_package():
    """Kiểm tra API trả về ResponsePackage và Output Artifacts hoàn chỉnh từ Phase 3."""
    mock_pkg = {
        "package_id": "pkg_001",
        "session_id": "sess_pkg_test",
        "direct_answer": "Doanh thu năm 1995 tăng trưởng 15% đạt 1.5M USD.",
        "artifacts": [
            {
                "type": "kpi",
                "title": "Tổng doanh thu",
                "value": "1.5M USD",
                "delta": 15.0,
                "delta_type": "increase",
            },
            {
                "type": "chart",
                "chart_type": "bar",
                "title": "Doanh thu theo quý",
                "x_key": "quarter",
                "y_keys": ["revenue"],
                "series_labels": {"revenue": "Doanh thu"},
                "data": [
                    {"quarter": "Q1", "revenue": 350000},
                    {"quarter": "Q2", "revenue": 400000},
                ],
            },
        ],
    }

    mock_supervisor_result = {
        "status": "COMPLETED",
        "question": "Phân tích doanh thu năm 1995",
        "session_id": "sess_pkg_test",
        "is_safe": True,
        "is_ambiguous": False,
        "final_answer": "Doanh thu năm 1995 tăng trưởng 15% đạt 1.5M USD.",
        "response_package": mock_pkg,
        "output_artifacts": mock_pkg["artifacts"],
        "tasks": [
            {
                "task_id": "t1",
                "description": "Tính tổng doanh thu năm 1995",
                "status": "COMPLETED",
            },
            {
                "task_id": "t2",
                "description": "Phân rã doanh thu theo quý",
                "status": "COMPLETED",
            },
        ],
        "sql": "SELECT sum(l_extendedprice) FROM lineitem WHERE extract(year FROM l_shipdate) = 1995",
        "data": [{"revenue": 1500000}],
        "columns": ["revenue"],
        "execution_time_ms": 85.0,
    }

    with patch(
        "src.api.routes.query.arun_supervisor",
        new_callable=AsyncMock,
        return_value=mock_supervisor_result,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = {
                "question": "Phân tích doanh thu năm 1995",
                "session_id": "sess_pkg_test",
            }
            response = await client.post("/api/v1/query/ask", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "COMPLETED"
            assert data["is_safe"] is True
            assert data["response_package"] is not None
            assert data["response_package"]["package_id"] == "pkg_001"
            assert len(data["output_artifacts"]) == 2
            assert data["output_artifacts"][0]["type"] == "kpi"
            assert data["output_artifacts"][1]["type"] == "chart"
            assert len(data["tasks"]) == 2
            assert data["tasks"][0]["task_id"] == "t1"
            assert data["metadata"]["query_count"] >= 0
