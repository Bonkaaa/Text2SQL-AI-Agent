"""Cấu hình và fixtures dùng chung cho toàn bộ test suites."""

from collections.abc import Generator
from pathlib import Path

import pytest

from src.models.rbac import UserContext, UserRole
from src.utils.audit_logger import AuditLogger
from src.utils.db_connector import DuckDBConnector
from src.utils.tpch_seeder import seed_tpch_data


@pytest.fixture(scope="session")
def shared_tpch_connector() -> Generator[DuckDBConnector]:
    """Fixture DuckDB in-memory với 8 bảng TPC-H dùng chung."""
    conn = seed_tpch_data(db_path=":memory:", scale_factor=0.01)
    connector = DuckDBConnector(connection=conn)
    yield connector
    conn.close()


@pytest.fixture
def default_user_context() -> UserContext:
    """Fixture cung cấp UserContext chuẩn cho vai trò Analyst."""
    return UserContext(
        user_id="analyst_test",
        session_id="session_test_default",
        role=UserRole.ANALYST,
    )


@pytest.fixture
def admin_user_context() -> UserContext:
    """Fixture cung cấp UserContext chuẩn cho vai trò Admin."""
    return UserContext(
        user_id="admin_test",
        session_id="session_admin_default",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def temp_audit_logger(tmp_path: Path) -> AuditLogger:
    """Fixture cung cấp AuditLogger ghi ra file JSONL tạm thời."""
    log_file = tmp_path / "test_audit.jsonl"
    return AuditLogger(log_file_path=str(log_file))
