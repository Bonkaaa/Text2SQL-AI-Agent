"""Unit tests kiểm tra tính bền vững (durability) và cô lập của SQLite PendingApprovalStore.

Kiểm tra:
- Khả năng lưu trữ và phục hồi dữ liệu qua các lần khởi động lại (process restart simulation).
- Cô lập các task khác nhau trong cùng một session_id (chống ghi đè task).
- Cập nhật trạng thái phê duyệt (resolve) kèm execution_result.
"""

import tempfile
import time
from pathlib import Path

from src.agents.control_pipeline.pending_store import (
    PendingApproval,
    SQLitePendingApprovalStore,
)
from src.models.rbac import UserContext, UserRole


def test_sqlite_pending_store_durability_and_restart():
    """Kiểm tra lưu trữ trên file SQLite sống sót qua các lần khởi động lại ứng dụng."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_approvals.sqlite"

        # Worker 1: Tạo và lưu pending approval
        store_1 = SQLitePendingApprovalStore(db_path=db_path)
        user_context = UserContext(
            user_id="analyst_u1",
            session_id="session_restart_test",
            role=UserRole.ANALYST,
        )
        approval_1 = PendingApproval(
            approval_id="appr_001",
            session_id="session_restart_test",
            task_id="task_001",
            sql="SELECT * FROM customer WHERE c_mktsegment = 'BUILDING'",
            reason="Chi phí quét vượt ngưỡng 40%",
            estimated_bytes=850000,
            tables_used=["customer"],
            user_context=user_context,
        )
        store_1.save(approval_1)

        # Worker 2: Giả lập ứng dụng restart hoặc worker khác mở file database
        store_2 = SQLitePendingApprovalStore(db_path=db_path)
        loaded = store_2.get(session_id="session_restart_test", task_id="task_001")

        assert loaded is not None
        assert loaded.approval_id == "appr_001"
        assert loaded.session_id == "session_restart_test"
        assert loaded.task_id == "task_001"
        assert loaded.sql == "SELECT * FROM customer WHERE c_mktsegment = 'BUILDING'"
        assert loaded.estimated_bytes == 850000
        assert loaded.status == "PENDING"
        assert loaded.tables_used == ["customer"]
        assert loaded.user_context is not None
        assert loaded.user_context.user_id == "analyst_u1"


def test_sqlite_pending_store_multi_task_independence():
    """Kiểm tra nhiều task trong cùng session không bị ghi đè dữ liệu của nhau."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_multi_task.sqlite"
        store = SQLitePendingApprovalStore(db_path=db_path)

        user_context = UserContext(
            user_id="analyst_u1",
            session_id="shared_session_123",
            role=UserRole.ANALYST,
        )

        appr_task_a = PendingApproval(
            approval_id="appr_A",
            session_id="shared_session_123",
            task_id="task_A",
            sql="SELECT count(*) FROM orders",
            estimated_bytes=300000,
            user_context=user_context,
        )
        appr_task_b = PendingApproval(
            approval_id="appr_B",
            session_id="shared_session_123",
            task_id="task_B",
            sql="SELECT count(*) FROM lineitem",
            estimated_bytes=900000,
            user_context=user_context,
        )

        store.save(appr_task_a)
        store.save(appr_task_b)

        # Tra cứu theo từng task_id
        res_a = store.get(session_id="shared_session_123", task_id="task_A")
        res_b = store.get(session_id="shared_session_123", task_id="task_B")

        assert res_a is not None
        assert res_a.task_id == "task_A"
        assert "orders" in res_a.sql

        assert res_b is not None
        assert res_b.task_id == "task_B"
        assert "lineitem" in res_b.sql


def test_sqlite_pending_store_resolve_and_cleanup():
    """Kiểm tra resolve cập nhật execution_result và remove xóa mục."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_resolve.sqlite"
        store = SQLitePendingApprovalStore(db_path=db_path)

        appr = PendingApproval(
            approval_id="appr_resolve",
            session_id="sess_res",
            sql="SELECT 1",
            estimated_bytes=100,
        )
        store.save(appr)

        # Phê duyệt
        resolved = store.resolve(
            session_id="sess_res",
            approved=True,
            execution_result={"data": [{"val": 1}], "columns": ["val"], "row_count": 1},
        )
        assert resolved is not None
        assert resolved.status == "APPROVED"
        assert resolved.execution_result is not None
        assert resolved.execution_result["row_count"] == 1

        # Xóa
        removed = store.remove(session_id="sess_res")
        assert removed is not None
        assert store.get(session_id="sess_res") is None


def test_session_ownership_durability_and_hijacking_prevention():
    """Kiểm tra quyền sở hữu session bền vững trong SQLite và chống hijacking bằng Session Secret Token."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_session_owner.sqlite"

        # Worker 1: Đăng ký session ban đầu cho Alice -> sinh session_token ngẫu nhiên
        store_1 = SQLitePendingApprovalStore(db_path=db_path)
        ok, _, alice_token = store_1.register_or_verify_session(
            session_id="sess_alice_secure", user_id="alice", is_admin=False
        )
        assert ok is True
        assert alice_token is not None
        assert len(alice_token) > 20

        # Alice gửi lại kèm đúng session_token -> Thành công
        ok_alice_valid, _, _ = store_1.register_or_verify_session(
            session_id="sess_alice_secure",
            user_id="alice",
            session_token=alice_token,
            is_admin=False,
        )
        assert ok_alice_valid is True

        # Kẻ tấn công tự khai user_id="alice" nhưng token sai/thiếu -> Bị từ chối (Chống Spoofing)
        ok_spoof, msg_spoof, _ = store_1.register_or_verify_session(
            session_id="sess_alice_secure",
            user_id="alice",
            session_token="bad_stolen_token",
            is_admin=False,
        )
        assert ok_spoof is False
        assert "Session Token không hợp lệ" in msg_spoof

        # Bob cố tình chiếm phiên của Alice -> Bị chặn
        ok_bob, msg_bob, _ = store_1.register_or_verify_session(
            session_id="sess_alice_secure", user_id="bob", is_admin=False
        )
        assert ok_bob is False
        assert "thuộc quyền sở hữu của người dùng khác" in msg_bob

        # Anonymous cố gắng chiếm phiên của Alice -> Bị chặn
        ok_anon, msg_anon, _ = store_1.register_or_verify_session(
            session_id="sess_alice_secure", user_id="anonymous_user", is_admin=False
        )
        assert ok_anon is False
        assert "thuộc quyền sở hữu của người dùng khác" in msg_anon

        # Worker 2: Giả lập restart process
        store_2 = SQLitePendingApprovalStore(db_path=db_path)

        # Bob vẫn bị chặn sau khi restart
        ok_bob_after, _, _ = store_2.register_or_verify_session(
            session_id="sess_alice_secure", user_id="bob", is_admin=False
        )
        assert ok_bob_after is False

        # Admin luôn có quyền truy cập
        ok_admin, _, _ = store_2.register_or_verify_session(
            session_id="sess_alice_secure", user_id="admin_root", is_admin=True
        )
        assert ok_admin is True


def test_claim_for_processing_atomic_cas_and_idempotency():
    """Kiểm tra cơ chế nguyên tử Compare-And-Set chống duplicate execution và bảo đảm idempotency."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_cas.sqlite"
        store = SQLitePendingApprovalStore(db_path=db_path)

        approval = PendingApproval(
            approval_id="appr_cas_001",
            session_id="sess_cas",
            sql="SELECT sum(o_totalprice) FROM orders",
            status="PENDING",
        )
        store.save(approval)

        # Lần 1: Worker 1 claim thành công
        claimed_1, app_1, state_1 = store.claim_for_processing(
            approval_id="appr_cas_001", session_id="sess_cas"
        )
        assert claimed_1 is True
        assert state_1 == "CLAIMED"
        assert app_1 is not None
        assert app_1.status == "PROCESSING"

        # Lần 2: Worker 2 cố gắng claim cùng lúc -> IN_PROGRESS
        claimed_2, _, state_2 = store.claim_for_processing(
            approval_id="appr_cas_001", session_id="sess_cas"
        )
        assert claimed_2 is False
        assert state_2 == "IN_PROGRESS"

        # Worker 1 hoàn tất thực thi và cập nhật trạng thái APPROVED
        store.resolve(
            session_id="sess_cas",
            approved=True,
            approval_id="appr_cas_001",
            execution_result={"data": [{"sum": 500000}], "row_count": 1},
        )

        # Lần 3: Gọi lại khi đã APPROVED -> Trả ALREADY_APPROVED kèm cached result
        claimed_3, app_3, state_3 = store.claim_for_processing(
            approval_id="appr_cas_001", session_id="sess_cas"
        )
        assert claimed_3 is False
        assert state_3 == "ALREADY_APPROVED"
        assert app_3 is not None
        assert app_3.execution_result == {"data": [{"sum": 500000}], "row_count": 1}


def test_store_mismatched_approval_and_session_id():
    """Kiểm tra bắt buộc kiểm tra đồng thời approval_id và session_id chống session spoofing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_mismatch.sqlite"
        store = SQLitePendingApprovalStore(db_path=db_path)

        appr = PendingApproval(
            approval_id="appr_alpha",
            session_id="session_alpha",
            sql="SELECT 42",
        )
        store.save(appr)

        # Ghép approval_id của Alpha với session_id của Beta -> Phải trả None / NOT_FOUND
        res_mismatch = store.get(approval_id="appr_alpha", session_id="session_beta")
        assert res_mismatch is None

        claimed, _, state = store.claim_for_processing(
            approval_id="appr_alpha", session_id="session_beta"
        )
        assert claimed is False
        assert state == "NOT_FOUND"


def test_claim_for_processing_lease_timeout_and_worker_reclaim():
    """Kiểm tra cơ chế Lease Timeout: Khi worker chết kẹt PROCESSING, worker khác reclaim thành công."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_lease.sqlite"
        store = SQLitePendingApprovalStore(db_path=db_path)

        appr = PendingApproval(
            approval_id="appr_lease_001",
            session_id="sess_lease",
            sql="SELECT count(*) FROM lineitem",
            status="PENDING",
        )
        store.save(appr)

        # Worker 1 claim
        claimed_w1, _, _ = store.claim_for_processing(
            approval_id="appr_lease_001",
            session_id="sess_lease",
            worker_id="worker_died_1",
            lease_timeout_seconds=5,
        )
        assert claimed_w1 is True

        # Khi chưa hết hạn lease (ngay tức thì), Worker 2 claim thất bại
        claimed_w2, _, state_w2 = store.claim_for_processing(
            approval_id="appr_lease_001",
            session_id="sess_lease",
            worker_id="worker_alive_2",
            lease_timeout_seconds=5,
        )
        assert claimed_w2 is False
        assert state_w2 == "IN_PROGRESS"

        # Giả lập thời gian trôi qua quá lease timeout (cập nhật processing_started_at về quá khứ 10s)
        past_time = time.time() - 10
        with store._connection() as conn:
            conn.execute(
                "UPDATE pending_approvals SET processing_started_at = ? WHERE approval_id = ?",
                (past_time, "appr_lease_001"),
            )
            conn.commit()

        # Worker 2 reclaim thành công do worker 1 đã timeout
        claimed_reclaim, app_rec, state_rec = store.claim_for_processing(
            approval_id="appr_lease_001",
            session_id="sess_lease",
            worker_id="worker_alive_2",
            lease_timeout_seconds=5,
        )
        assert claimed_reclaim is True
        assert state_rec == "CLAIMED"
        assert app_rec is not None
        assert app_rec.processing_owner == "worker_alive_2"


def test_atomic_consume_and_plan_isolation():
    """Kiểm tra tính nguyên tử của consume và cô lập approval theo plan_id / question_hash."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_consume.sqlite"
        store = SQLitePendingApprovalStore(db_path=db_path)

        appr = PendingApproval(
            approval_id="appr_consume_01",
            session_id="sess_consume",
            task_id="task_1",
            plan_id="plan_uuid_alpha",
            question_hash="hash_question_1",
            sql="SELECT 100",
            status="APPROVED",
            consumed=0,
        )
        store.save(appr)

        # Tra cứu theo đúng plan_id và question_hash -> Tìm thấy
        found = store.get(
            session_id="sess_consume",
            plan_id="plan_uuid_alpha",
            question_hash="hash_question_1",
        )
        assert found is not None
        assert found.approval_id == "appr_consume_01"

        # Tra cứu với plan_id khác hoặc question_hash khác -> Không tìm thấy (chống collision task_1)
        found_wrong_plan = store.get(
            session_id="sess_consume",
            plan_id="plan_uuid_beta",
            question_hash="hash_question_1",
        )
        assert found_wrong_plan is None

        found_wrong_hash = store.get(
            session_id="sess_consume",
            plan_id="plan_uuid_alpha",
            question_hash="hash_question_2",
        )
        assert found_wrong_hash is None

        # Worker consume lần 1: thành công
        consumed_first = store.consume("appr_consume_01")
        assert consumed_first is True

        # Worker consume lần 2 (cùng approval): trả False (ngăn chặn double-consumption)
        consumed_second = store.consume("appr_consume_01")
        assert consumed_second is False

        # Sau khi consume, approval không còn được xem là pending/unconsumed
        found_after = store.get(
            session_id="sess_consume",
            plan_id="plan_uuid_alpha",
            question_hash="hash_question_1",
        )
        assert found_after is not None
        assert found_after.consumed == 1
