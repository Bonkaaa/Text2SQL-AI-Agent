"""Unit and integration tests for Supervisor HITL detection and approval flow."""

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.supervisor import (
    arun_supervisor,
    check_hitl_pending,
    run_supervisor,
)
from src.api.main import app
from src.models.rbac import UserContext, UserRole


def test_check_hitl_pending_positive():
    """Kiểm tra check_hitl_pending trích xuất chính xác thông tin khi có thông điệp BLOCKED_HITL."""
    hitl_message = AIMessage(
        content=(
            "Truy vấn SQL TẠM DỪNG CHỜ PHÊ DUYỆT (HITL Required) [BLOCKED_HITL].\n"
            "- Câu lệnh: SELECT l_orderkey, SUM(l_extendedprice) FROM lineitem GROUP BY l_orderkey\n"
            "- Dung lượng quét ước tính: 181969200 bytes\n"
            "- Lý do rủi ro: Khối lượng quét lớn (~1,444,200 dòng, vượt ngưỡng 500,000 dòng); "
            "Truy vấn trên bảng dữ liệu lớn (lineitem) nhưng thiếu bộ lọc mốc thời gian/phân vùng."
        )
    )
    messages = [
        HumanMessage(content="Tính tổng doanh thu trên từng đơn hàng"),
        hitl_message,
    ]

    is_hitl, reason, sql, est_bytes = check_hitl_pending(messages)

    assert is_hitl is True
    assert sql == "SELECT l_orderkey, SUM(l_extendedprice) FROM lineitem GROUP BY l_orderkey"
    assert est_bytes == 181969200
    assert "Khối lượng quét lớn" in reason
    assert "lineitem" in reason


def test_check_hitl_pending_negative():
    """Kiểm tra check_hitl_pending trả về False khi tin nhắn bình thường hoặc thành công."""
    success_message = AIMessage(
        content=(
            "Truy vấn SQL thực thi THÀNH CÔNG trên database (12.34ms).\n"
            "- Câu lệnh đã chạy: SELECT c_name FROM customer LIMIT 5\n"
            "- Số lượng bản ghi: 5\n"
            "- Dữ liệu mẫu thực tế: []"
        )
    )
    messages = [
        HumanMessage(content="Lấy 5 khách hàng"),
        success_message,
    ]

    is_hitl, reason, sql, est_bytes = check_hitl_pending(messages)

    assert is_hitl is False
    assert reason is None
    assert sql is None
    assert est_bytes is None


def test_run_supervisor_pending_approval_flow():
    """Kiểm tra run_supervisor bắt kịp trạng thái PENDING_APPROVAL khi agent trả về BLOCKED_HITL."""
    hitl_content = (
        "Truy vấn SQL TẠM DỪNG CHỜ PHÊ DUYỆT (HITL Required) [BLOCKED_HITL].\n"
        "- Câu lệnh: SELECT * FROM lineitem\n"
        "- Dung lượng quét ước tính: 181969200 bytes\n"
        "- Lý do rủi ro: Truy vấn trên bảng dữ liệu lớn (lineitem) nhưng thiếu bộ lọc mốc thời gian/phân vùng."
    )

    class MockAgent:
        def invoke(self, *args, **kwargs):
            return {
                "messages": [
                    HumanMessage(content="Xem bảng lineitem"),
                    AIMessage(content=hitl_content),
                ],
                "files": {},
            }

    user = UserContext(
        user_id="test_analyst",
        session_id="sess_hitl_unit_01",
        role=UserRole.ANALYST,
    )

    result = run_supervisor(
        question="Xem bảng lineitem",
        user_context=user,
        session_id="sess_hitl_unit_01",
        agent=MockAgent(),
        skip_clarification=True,
    )

    assert result["status"] == "PENDING_APPROVAL"
    assert result["requires_hitl"] is True
    assert result["sql"] == "SELECT * FROM lineitem"
    assert result["estimated_cost_bytes"] == 181969200
    assert "lineitem" in result["hitl_reason"]
    assert "⚠️ **Truy vấn yêu cầu phê duyệt từ quản trị viên" in result["final_answer"]


@pytest.mark.asyncio
async def test_arun_supervisor_pending_approval_flow():
    """Kiểm tra arun_supervisor bất đồng bộ bắt kịp trạng thái PENDING_APPROVAL."""
    hitl_content = (
        "Truy vấn SQL TẠM DỪNG CHỜ PHÊ DUYỆT (HITL Required) [BLOCKED_HITL].\n"
        "- Câu lệnh: SELECT * FROM orders\n"
        "- Dung lượng quét ước tính: 45000000 bytes\n"
        "- Lý do rủi ro: Khối lượng quét lớn (~600,000 dòng); thiếu bộ lọc thời gian."
    )

    class MockAsyncAgent:
        async def ainvoke(self, *args, **kwargs):
            return {
                "messages": [
                    HumanMessage(content="Xem toàn bộ đơn hàng"),
                    AIMessage(content=hitl_content),
                ],
                "files": {},
            }

    user = UserContext(
        user_id="test_analyst",
        session_id="sess_hitl_unit_02",
        role=UserRole.ANALYST,
    )

    result = await arun_supervisor(
        question="Xem toàn bộ đơn hàng",
        user_context=user,
        session_id="sess_hitl_unit_02",
        agent=MockAsyncAgent(),
        skip_clarification=True,
    )

    assert result["status"] == "PENDING_APPROVAL"
    assert result["requires_hitl"] is True
    assert result["sql"] == "SELECT * FROM orders"
    assert result["estimated_cost_bytes"] == 45000000
    assert "⚠️ **Truy vấn yêu cầu phê duyệt" in result["final_answer"]


@pytest.mark.asyncio
async def test_ask_query_api_returns_pending_approval(monkeypatch):
    """Kiểm tra endpoint POST /api/v1/query/ask trả về status PENDING_APPROVAL và requires_hitl=True."""
    async def mock_arun(*args, **kwargs):
        return {
            "status": "PENDING_APPROVAL",
            "question": "Thống kê chi tiết lineitem",
            "session_id": "sess_api_hitl_01",
            "is_ambiguous": False,
            "requires_hitl": True,
            "hitl_reason": "Dung lượng quét lớn trên bảng lineitem",
            "sql": "SELECT * FROM lineitem",
            "estimated_cost_bytes": 181969200,
            "messages": [],
            "final_answer": "Truy vấn yêu cầu phê duyệt HITL.",
            "files": {},
        }

    monkeypatch.setattr("src.api.routes.query.arun_supervisor", mock_arun)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/query/ask",
            json={
                "question": "Thống kê chi tiết lineitem",
                "session_id": "sess_api_hitl_01",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING_APPROVAL"
        assert data["requires_hitl"] is True
        assert data["sql"] == "SELECT * FROM lineitem"
        assert data["estimated_cost_bytes"] == 181969200
        assert "phê duyệt" in data["final_answer"].lower()
