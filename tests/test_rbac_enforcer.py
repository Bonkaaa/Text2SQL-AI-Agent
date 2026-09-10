from src.models.rbac import UserContext, UserRole
from src.utils.rbac_enforcer import enforce_rbac_policy


def test_analyst_access_allowed_tables_and_columns():
    """Kiểm tra role Analyst truy vấn các bảng và cột thông thường được cho phép."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    tables = ["customer", "orders", "lineitem"]
    columns = ["c_name", "c_mktsegment", "o_totalprice", "l_quantity"]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is True
    assert result.error_type is None
    assert result.error_message is None
    assert len(result.violating_tables) == 0
    assert len(result.violating_columns) == 0


def test_analyst_blocked_when_accessing_forbidden_columns():
    """Kiểm tra role Analyst bị chặn khi truy cập các cột PII hoặc tài chính cá nhân."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    tables = ["customer"]
    columns = ["c_name", "c_phone", "c_acctbal"]  # c_phone và c_acctbal bị cấm

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_COLUMN"
    assert "c_phone" in result.violating_columns
    assert "c_acctbal" in result.violating_columns
    assert "c_phone" in result.error_message


def test_analyst_blocked_when_accessing_forbidden_table():
    """Kiểm tra role Analyst bị chặn khi truy cập bảng nội bộ không được phép (audit_log)."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    tables = ["audit_log", "customer"]
    columns = ["query_id", "c_name"]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_TABLE"
    assert "audit_log" in result.violating_tables
    assert "audit_log" in result.error_message


def test_analyst_blocked_on_both_table_and_columns():
    """Kiểm tra role Analyst bị chặn khi vi phạm cả bảng lẫn cột."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    tables = ["audit_log"]
    columns = ["s_phone"]  # s_phone bị cấm

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is False
    assert len(result.violating_tables) > 0
    assert len(result.violating_columns) > 0


def test_admin_full_access():
    """Kiểm tra role Admin được phép truy cập tất cả bảng và cột bao gồm PII và audit_log."""
    admin_context = UserContext(
        user_id="admin_1", session_id="sess_admin", role=UserRole.ADMIN
    )
    tables = ["audit_log", "customer", "supplier"]
    columns = ["c_phone", "c_acctbal", "s_phone", "s_acctbal", "query_id"]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=admin_context
    )

    assert result.is_allowed is True
    assert len(result.violating_tables) == 0
    assert len(result.violating_columns) == 0
    assert result.error_type is None
