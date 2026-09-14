"""Integration Test Suite cho FastAPI Gateway Endpoints (Component 5.1).

Tuân thủ quy trình TDD:
- Kiểm tra Endpoint /health và /api/v1/health.
- Kiểm tra Endpoint /api/v1/query/ask (luồng thành công, luồng làm rõ, luồng lỗi).
- Kiểm tra Endpoint /api/v1/query/approve (Human-in-the-loop approval/rejection).
- Kiểm tra Endpoint /api/v1/query/history (Lịch sử artifacts của phiên).
- Kiểm tra Endpoint /api/v1/audit/logs (RBAC: Admin được phép 200, Analyst bị cấm 403).
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
async def test_health_check():
    """Kiểm tra Endpoint /health trả về trạng thái healthy và kết nối database."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "version" in data


@pytest.mark.asyncio
async def test_ask_query_clear_question_success():
    """Kiểm tra Endpoint /api/v1/query/ask xử lý câu hỏi rõ ràng trả về COMPLETED."""
    mock_supervisor_result = {
        "status": "COMPLETED",
        "question": "Top 5 khách hàng chi tiêu lớn nhất",
        "session_id": "sess_test_clear",
        "is_ambiguous": False,
        "final_answer": "Top 5 khách hàng gồm Customer#001, Customer#002...",
        "sql": "SELECT c_name, sum(l_extendedprice) FROM customer JOIN orders ...",
        "data": [
            {"c_name": "Customer#001", "total_spent": 150000.0},
            {"c_name": "Customer#002", "total_spent": 140000.0},
        ],
        "columns": ["c_name", "total_spent"],
        "recharts_config": {"chart_type": "bar", "x_key": "c_name"},
        "execution_time_ms": 120.5,
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
                "question": "Top 5 khách hàng chi tiêu lớn nhất",
                "session_id": "sess_test_clear",
                "role": UserRole.ANALYST.value,
            }
            response = await client.post("/api/v1/query/ask", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "COMPLETED"
            assert data["session_id"] == "sess_test_clear"
            assert data["is_ambiguous"] is False
            assert "Customer#001" in data["final_answer"]
            assert len(data["data"]) == 2
            assert data["columns"] == ["c_name", "total_spent"]


@pytest.mark.asyncio
async def test_ask_query_ambiguous_question_clarification():
    """Kiểm tra Endpoint /api/v1/query/ask xử lý câu hỏi mơ hồ trả về CLARIFICATION_REQUIRED."""
    mock_supervisor_result = {
        "status": "CLARIFICATION_REQUIRED",
        "question": "Doanh thu thế nào?",
        "session_id": "sess_test_clarify",
        "is_ambiguous": True,
        "clarification_question": "Bạn muốn xem doanh thu theo năm hay theo phân khúc?",
        "suggested_options": ["A. Doanh thu theo năm", "B. Doanh thu theo phân khúc"],
        "data": None,
        "columns": None,
        "sql": None,
        "recharts_config": None,
        "execution_time_ms": 45.0,
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
                "question": "Doanh thu thế nào?",
                "session_id": "sess_test_clarify",
            }
            response = await client.post("/api/v1/query/ask", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "CLARIFICATION_REQUIRED"
            assert data["is_ambiguous"] is True
            assert data["clarification_question"] == mock_supervisor_result["clarification_question"]
            assert len(data["suggested_options"]) == 2
            assert data["data"] is None


@pytest.mark.asyncio
async def test_ask_query_validation_error_empty_question():
    """Kiểm tra validation lỗi 422 Unprocessable Entity khi question rỗng."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {"question": ""}
        response = await client.post("/api/v1/query/ask", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_approve_query_success():
    """Kiểm tra Endpoint /api/v1/query/approve tiếp nhận quyết định duyệt HITL."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "session_id": "sess_hitl_001",
            "approved": True,
        }
        response = await client.post("/api/v1/query/approve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is True
        assert data["session_id"] == "sess_hitl_001"
        assert "tiếp nhận" in data["message"].lower() or "thành công" in data["message"].lower()


@pytest.mark.asyncio
async def test_approve_query_rejection():
    """Kiểm tra Endpoint /api/v1/query/approve tiếp nhận quyết định từ chối HITL."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "session_id": "sess_hitl_002",
            "approved": False,
            "rejection_reason": "Chi phí quét vượt ngân sách dự toán",
        }
        response = await client.post("/api/v1/query/approve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is False
        assert "từ chối" in data["message"].lower()


@pytest.mark.asyncio
async def test_query_history_endpoint():
    """Kiểm tra Endpoint /api/v1/query/history đọc lịch sử phiên truy vấn."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/query/history?session_id=sess_hist_001")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "sess_hist_001"
        assert isinstance(data["history"], list)


@pytest.mark.asyncio
async def test_audit_logs_admin_authorized():
    """Kiểm tra Endpoint /api/v1/audit/logs cho phép người dùng vai trò ADMIN."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"X-User-Role": "Admin"}
        response = await client.get("/api/v1/audit/logs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "logs" in data
        assert isinstance(data["logs"], list)


@pytest.mark.asyncio
async def test_audit_logs_analyst_forbidden():
    """Kiểm tra Endpoint /api/v1/audit/logs chặn người dùng vai trò ANALYST với mã 403."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = {"X-User-Role": "Analyst"}
        response = await client.get("/api/v1/audit/logs", headers=headers)
        assert response.status_code == 403
        data = response.json()
        assert "quyền truy cập bị từ chối" in data["detail"].lower()
