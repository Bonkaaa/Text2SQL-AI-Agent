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
            assert (
                data["clarification_question"]
                == mock_supervisor_result["clarification_question"]
            )
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
async def test_ask_query_client_role_escalation_blocked():
    """Kiểm tra Endpoint /api/v1/query/ask chặn người dùng thông thường cố tình leo quyền ADMIN qua body."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "question": "Top 5 khách hàng",
            "role": UserRole.ADMIN.value,
        }
        # Gọi không có header X-User-Role (mặc định Analyst) nhưng body lại đòi quyền ADMIN
        response = await client.post("/api/v1/query/ask", json=payload)
        assert response.status_code == 403
        assert "không được phép tự nâng quyền" in response.json()["detail"]


@pytest.mark.asyncio
async def test_approve_query_unauthorized_non_admin():
    """Kiểm tra Endpoint /api/v1/query/approve chặn người dùng không có quyền ADMIN."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "session_id": "sess_hitl_001",
            "approved": True,
        }
        # Gọi không có header Admin (mặc định Analyst)
        response = await client.post("/api/v1/query/approve", json=payload)
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]


@pytest.mark.asyncio
async def test_approve_query_success():
    """Kiểm tra Endpoint /api/v1/query/approve tiếp nhận quyết định duyệt HITL từ Admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "session_id": "sess_hitl_001",
            "approved": True,
        }
        response = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={"X-User-Role": "Admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is True
        assert data["session_id"] == "sess_hitl_001"
        assert (
            "tiếp nhận" in data["message"].lower()
            or "thành công" in data["message"].lower()
        )


@pytest.mark.asyncio
async def test_approve_query_rejection():
    """Kiểm tra Endpoint /api/v1/query/approve tiếp nhận quyết định từ chối HITL từ Admin."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "session_id": "sess_hitl_002",
            "approved": False,
            "rejection_reason": "Chi phí quét vượt ngân sách dự toán",
        }
        response = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={"X-User-Role": "Admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is False
        assert "từ chối" in data["message"].lower()


@pytest.mark.asyncio
async def test_approve_query_success_with_pending_execution():
    """Kiểm tra Endpoint /api/v1/query/approve thực thi câu SQL từ PendingApprovalStore khi Admin duyệt."""
    from src.agents.control_pipeline.pending_store import (
        get_pending_approval,
        save_pending_approval,
    )
    from src.models.rbac import UserContext

    user_context = UserContext(
        user_id="user_test",
        session_id="sess_hitl_exec",
        role=UserRole.ANALYST,
    )
    save_pending_approval(
        session_id="sess_hitl_exec",
        sql="SELECT c_customer_sk FROM customer LIMIT 2",
        estimated_bytes=50000,
        user_context=user_context,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "session_id": "sess_hitl_exec",
            "approved": True,
        }
        response = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={"X-User-Role": "Admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["approved"] is True
        assert data["session_id"] == "sess_hitl_exec"
        assert "thực thi thành công" in data["message"]
        assert len(data["data"]) == 2

        # Kiểm tra trạng thái pending đã chuyển thành APPROVED
        saved = get_pending_approval("sess_hitl_exec")
        assert saved is not None
        assert saved.status == "APPROVED"


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


@pytest.mark.asyncio
async def test_admin_token_protection_against_header_spoofing(monkeypatch):
    """Kiểm tra chặn giả mạo X-User-Role: Admin khi server đã cấu hình admin_api_key."""
    from src.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "admin_api_key", "secret_admin_key_999")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Trường hợp 1: Client chỉ gửi header X-User-Role: Admin (không có token) -> Bị chặn 403
        payload = {"session_id": "sess_spoof_01", "approved": True}
        resp_spoofed = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={"X-User-Role": "Admin"},
        )
        assert resp_spoofed.status_code == 403
        assert "ADMIN đã được xác thực" in resp_spoofed.json()["detail"]

        # Trường hợp 2: Client gửi đúng X-Admin-Token hợp lệ -> Được chấp thuận 200
        resp_valid = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={
                "X-User-Role": "Admin",
                "X-Admin-Token": "secret_admin_key_999",
            },
        )
        assert resp_valid.status_code == 200


@pytest.mark.asyncio
async def test_session_ownership_cross_user_access_blocked():
    """Kiểm tra chặn truy cập chéo phiên (session hijacking) giữa 2 người dùng khác nhau."""
    mock_result = {
        "status": "COMPLETED",
        "question": "Câu hỏi test",
        "session_id": "sess_alice_secret",
        "is_ambiguous": False,
        "final_answer": "Trả lời",
        "execution_time_ms": 10.0,
    }

    with patch(
        "src.api.routes.query.arun_supervisor",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Alice tạo phiên
            resp_alice = await client.post(
                "/api/v1/query/ask",
                json={"question": "Doanh thu", "session_id": "sess_alice_secret"},
                headers={"X-User-Id": "alice_id", "X-User-Role": "Analyst"},
            )
            assert resp_alice.status_code == 200

            # Bob cố tình can thiệp vào phiên của Alice
            resp_bob = await client.post(
                "/api/v1/query/ask",
                json={"question": "Doanh thu", "session_id": "sess_alice_secret"},
                headers={"X-User-Id": "bob_id", "X-User-Role": "Analyst"},
            )
            assert resp_bob.status_code == 403
            assert "thuộc quyền sở hữu của người dùng khác" in resp_bob.json()["detail"]


def test_production_startup_validation_fail_closed():
    """Kiểm tra Settings bắt buộc fail-closed khi khởi động môi trường production thiếu admin_api_key."""
    from pydantic import ValidationError

    from src.config import Settings

    # Thiếu key ở production -> Ném lỗi
    with pytest.raises(ValidationError) as exc_info:
        Settings(app_env="production", admin_api_key=None)
    assert "admin_api_key bắt buộc phải được cấu hình" in str(exc_info.value)

    # Key quá ngắn (< 16 ký tự) -> Ném lỗi
    with pytest.raises(ValidationError) as exc_info2:
        Settings(app_env="production", admin_api_key="short_key_123")
    assert "dài tối thiểu 16 ký tự" in str(exc_info2.value)

    # Key hợp lệ (>= 16 ký tự) -> Khởi tạo thành công
    valid_settings = Settings(
        app_env="production", admin_api_key="super_secret_production_key_2026"
    )
    assert valid_settings.admin_api_key == "super_secret_production_key_2026"


@pytest.mark.asyncio
async def test_approve_idempotent_duplicate_request():
    """Kiểm tra tính Idempotent của /approve: gọi lần 2 không chạy lại query, trả ALREADY_APPROVED."""
    from src.agents.control_pipeline.pending_store import (
        clear_all_pending_approvals,
        save_pending_approval,
    )
    from src.models.rbac import UserContext

    clear_all_pending_approvals()
    user_context = UserContext(
        user_id="user_idem",
        session_id="sess_idempotent_test",
        role=UserRole.ANALYST,
    )
    saved = save_pending_approval(
        session_id="sess_idempotent_test",
        sql="SELECT c_customer_sk FROM customer LIMIT 1",
        estimated_bytes=1000,
        user_context=user_context,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "session_id": "sess_idempotent_test",
            "approval_id": saved.approval_id,
            "approved": True,
        }

        # Lần 1: Thực thi thành công
        resp_1 = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={"X-User-Role": "Admin"},
        )
        assert resp_1.status_code == 200
        data_1 = resp_1.json()
        assert data_1["status"] == "SUCCESS"
        assert len(data_1["data"]) == 1

        # Lần 2: Gọi lại cùng approval_id -> ALREADY_APPROVED không chạy lại SQL
        resp_2 = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={"X-User-Role": "Admin"},
        )
        assert resp_2.status_code == 200
        data_2 = resp_2.json()
        assert data_2["status"] == "ALREADY_APPROVED"
        assert data_2["data"] == data_1["data"]
        assert "trước đó" in data_2["message"]


@pytest.mark.asyncio
async def test_approve_mismatched_session_and_approval_id():
    """Kiểm tra từ chối yêu cầu /approve khi approval_id không thuộc session_id chỉ định."""
    from src.agents.control_pipeline.pending_store import save_pending_approval

    saved = save_pending_approval(
        session_id="sess_legit_alpha",
        sql="SELECT 1",
        estimated_bytes=100,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Gửi approval_id của Alpha nhưng khai session_id là Beta
        payload = {
            "session_id": "sess_spoofed_beta",
            "approval_id": saved.approval_id,
            "approved": True,
        }
        response = await client.post(
            "/api/v1/query/approve",
            json=payload,
            headers={"X-User-Role": "Admin"},
        )
        assert response.status_code == 400
        assert "không khớp với phiên" in response.json()["detail"]


@pytest.mark.asyncio
async def test_session_ownership_anonymous_cannot_hijack_registered_session():
    """Kiểm tra anonymous không thể chiếm hoặc truy cập phiên đã được sở hữu bởi user có định danh."""
    mock_result = {
        "status": "COMPLETED",
        "question": "Câu hỏi test",
        "session_id": "sess_alice_owned",
        "is_ambiguous": False,
        "final_answer": "Trả lời",
        "execution_time_ms": 10.0,
    }

    with patch(
        "src.api.routes.query.arun_supervisor",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Alice tạo phiên
            resp_alice = await client.post(
                "/api/v1/query/ask",
                json={"question": "Doanh thu", "session_id": "sess_alice_owned"},
                headers={"X-User-Id": "alice_registered", "X-User-Role": "Analyst"},
            )
            assert resp_alice.status_code == 200

            # Anonymous cố gắng truy cập phiên của Alice
            resp_anon = await client.post(
                "/api/v1/query/ask",
                json={"question": "Doanh thu", "session_id": "sess_alice_owned"},
                headers={"X-User-Id": "anonymous_user"},
            )
            assert resp_anon.status_code == 403
            assert (
                "thuộc quyền sở hữu của người dùng khác" in resp_anon.json()["detail"]
            )


@pytest.mark.asyncio
async def test_session_secret_token_anti_spoofing():
    """Kiểm tra cơ chế Session Secret Token: Kẻ tấn công tự khai trùng User ID vẫn bị từ chối 403 nếu không có token."""
    mock_result = {
        "status": "COMPLETED",
        "question": "Doanh thu năm 1995",
        "session_id": "sess_token_guard",
        "final_answer": "Doanh thu là 1M USD.",
        "sql": "SELECT 1000000",
        "data": [{"revenue": 1000000}],
        "columns": ["revenue"],
    }

    with patch(
        "src.api.routes.query.arun_supervisor",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Alice tạo phiên -> nhận session_token trong body và header
            resp_alice = await client.post(
                "/api/v1/query/ask",
                json={"question": "Doanh thu", "session_id": "sess_token_guard"},
                headers={"X-User-Id": "alice_legit", "X-User-Role": "Analyst"},
            )
            assert resp_alice.status_code == 200
            alice_token = resp_alice.json().get("session_token")
            assert alice_token is not None
            assert resp_alice.headers.get("X-Session-Token") == alice_token

            # 2. Kẻ tấn công Eve giả mạo header X-User-Id: alice_legit nhưng không có session_token
            resp_eve_no_token = await client.post(
                "/api/v1/query/ask",
                json={"question": "Đánh cắp dữ liệu", "session_id": "sess_token_guard"},
                headers={"X-User-Id": "alice_legit", "X-User-Role": "Analyst"},
            )
            assert resp_eve_no_token.status_code == 403
            assert (
                "Session Token không hợp lệ hoặc thiếu"
                in resp_eve_no_token.json()["detail"]
            )

            # 3. Kẻ tấn công Eve gửi sai token
            resp_eve_bad_token = await client.post(
                "/api/v1/query/ask",
                json={"question": "Đánh cắp dữ liệu", "session_id": "sess_token_guard"},
                headers={
                    "X-User-Id": "alice_legit",
                    "X-User-Role": "Analyst",
                    "X-Session-Token": "bad_token_guess",
                },
            )
            assert resp_eve_bad_token.status_code == 403

            # 4. Alice gửi đúng token -> Thành công
            resp_alice_turn2 = await client.post(
                "/api/v1/query/ask",
                json={
                    "question": "Tiếp tục phân tích",
                    "session_id": "sess_token_guard",
                },
                headers={
                    "X-User-Id": "alice_legit",
                    "X-User-Role": "Analyst",
                    "X-Session-Token": alice_token,
                },
            )
            assert resp_alice_turn2.status_code == 200


@pytest.mark.asyncio
async def test_approve_query_unexpected_db_crash_marks_failed():
    """Kiểm tra khi DB gặp crash/exception trong lúc execute phê duyệt, status chuyển sang FAILED tránh zombie PROCESSING lock."""
    from src.agents.control_pipeline.pending_store import (
        get_pending_approval,
        save_pending_approval,
    )
    from src.models.rbac import UserContext

    user_context = UserContext(
        user_id="user_test",
        session_id="sess_crash_test",
        role=UserRole.ANALYST,
    )
    appr = save_pending_approval(
        session_id="sess_crash_test",
        sql="SELECT crash_now()",
        estimated_bytes=50000,
        user_context=user_context,
    )

    with patch(
        "src.utils.db_connector.DuckDBConnector.execute_query",
        side_effect=RuntimeError("DuckDB out of memory error!"),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            payload = {
                "session_id": "sess_crash_test",
                "approval_id": appr.approval_id,
                "approved": True,
            }
            response = await client.post(
                "/api/v1/query/approve",
                json=payload,
                headers={"X-User-Role": "Admin"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "FAILED"
            assert "Lỗi khi thực thi truy vấn sau phê duyệt" in data["message"]

            # Kiểm tra trạng thái pending trong DB đã được cập nhật FAILED, không kẹt PROCESSING
            saved = get_pending_approval("sess_crash_test")
            assert saved is not None
            assert saved.status == "FAILED"
            assert "out of memory" in (saved.rejection_reason or "")
