from pathlib import Path
from unittest.mock import patch

from src.models.rbac import UserRole
from src.utils.audit_logger import AuditEvent, AuditLogger, log_audit_event


def test_audit_event_defaults():
    """Kiểm tra giá trị mặc định của AuditEvent: query_id tự sinh UUID, created_at tự sinh UTC."""
    event = AuditEvent(
        session_id="sess_1",
        user_id="user_1",
        role=UserRole.ANALYST.value,
        question="Doanh thu theo quốc gia năm 1995?",
        sql="SELECT n_name, sum(l_extendedprice) FROM customer ...",
        status="SUCCESS",
        bytes_scanned=10240,
        execution_time_ms=15.5,
    )

    assert event.query_id is not None
    assert len(event.query_id) > 10
    assert event.created_at is not None
    assert event.error_message is None
    assert event.status == "SUCCESS"


def test_log_event_and_retrieve(tmp_path: Path):
    """Kiểm tra ghi log sự kiện vào file JSONL và đọc lại."""
    log_file = tmp_path / "audit_test.jsonl"
    logger = AuditLogger(log_file_path=str(log_file))

    event = AuditEvent(
        session_id="sess_abc",
        user_id="analyst_1",
        role=UserRole.ANALYST.value,
        question="Top 5 khách hàng",
        sql="SELECT c_name FROM customer LIMIT 5",
        status="SUCCESS",
        bytes_scanned=512,
        execution_time_ms=8.2,
    )

    success = logger.log_event(event)
    assert success is True
    assert log_file.exists()

    logs = logger.get_logs()
    assert len(logs) == 1
    assert logs[0].query_id == event.query_id
    assert logs[0].user_id == "analyst_1"
    assert logs[0].status == "SUCCESS"


def test_get_logs_filtered_by_session(tmp_path: Path):
    """Kiểm tra lọc danh sách log theo session_id."""
    log_file = tmp_path / "audit_filter_test.jsonl"
    logger = AuditLogger(log_file_path=str(log_file))

    logger.log_event(
        AuditEvent(
            session_id="session_A",
            user_id="user_1",
            role=UserRole.ANALYST.value,
            question="Q1",
            sql="SELECT 1",
            status="SUCCESS",
        )
    )
    logger.log_event(
        AuditEvent(
            session_id="session_B",
            user_id="user_2",
            role=UserRole.ADMIN.value,
            question="Q2",
            sql="SELECT 2",
            status="BLOCKED_RBAC",
            error_message="Cấm truy cập cột c_phone",
        )
    )
    logger.log_event(
        AuditEvent(
            session_id="session_A",
            user_id="user_1",
            role=UserRole.ANALYST.value,
            question="Q3",
            sql="SELECT 3",
            status="SUCCESS",
        )
    )

    all_logs = logger.get_logs()
    assert len(all_logs) == 3

    session_a_logs = logger.get_logs(session_id="session_A")
    assert len(session_a_logs) == 2
    for log in session_a_logs:
        assert log.session_id == "session_A"


def test_logger_fail_safe_no_crash(tmp_path: Path):
    """Đảm bảo lỗi I/O khi ghi log không bao giờ làm sập ứng dụng (Fail-Safe)."""
    log_file = tmp_path / "audit_fail.jsonl"
    logger = AuditLogger(log_file_path=str(log_file))

    event = AuditEvent(
        session_id="sess_err",
        user_id="user_err",
        role=UserRole.ANALYST.value,
        question="Crash test",
        sql="SELECT 1",
        status="SUCCESS",
    )

    # Mock open() để cố ý ném lỗi OSError
    with patch("builtins.open", side_effect=OSError("Disk write error")):
        success = logger.log_event(event)

    # Logger phải bắt lỗi an toàn, trả về False và không ném exception
    assert success is False


def test_log_audit_event_module_level():
    """Kiểm tra hàm tiện ích log_audit_event cấp module gọi an toàn."""
    event = AuditEvent(
        session_id="sess_mod",
        user_id="user_mod",
        role=UserRole.ADMIN.value,
        question="Select all",
        sql="SELECT 100",
        status="SUCCESS",
    )
    result = log_audit_event(event)
    assert isinstance(result, bool)
