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
    """Kiểm tra role Analyst bị chặn khi truy cập các cột PII hoặc tài chính cá nhân TPC-H."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    tables = ["customer"]
    columns = [
        "c_name",
        "c_phone",
        "c_acctbal",
        "c_address",
    ]  # c_phone, c_acctbal, c_address bị cấm

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_COLUMN"
    assert "c_phone" in result.violating_columns
    assert "c_acctbal" in result.violating_columns
    assert "c_address" in result.violating_columns
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
    columns = ["c_phone", "c_acctbal", "s_phone", "s_acctbal", "s_address", "query_id"]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=admin_context
    )

    assert result.is_allowed is True
    assert len(result.violating_tables) == 0
    assert len(result.violating_columns) == 0
    assert result.error_type is None


def test_analyst_blocked_on_wildcard_select_star_sensitive_table():
    """Kiểm tra role Analyst bị chặn khi dùng wildcard SELECT * trên bảng chứa cột PII (customer)."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    tables = ["customer"]
    columns: list[str] = []

    result = enforce_rbac_policy(
        tables_used=tables,
        columns_used=columns,
        user_context=context,
        has_star=True,
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_COLUMN"
    assert "c_phone" in result.violating_columns
    assert "c_acctbal" in result.violating_columns
    assert "c_address" in result.violating_columns


def test_analyst_blocked_on_wildcard_unexpandable_table():
    """Kiểm tra role Analyst bị từ chối Fail-Closed khi dùng wildcard trên bảng không thuộc TPC-H."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    result = enforce_rbac_policy(
        tables_used=["unknown_external_table"],
        columns_used=["*"],
        user_context=context,
        has_star=True,
    )

    assert result.is_allowed is False
    assert result.error_type == "FORBIDDEN_WILDCARD"
    assert "Fail-Closed" in result.error_message


def test_tpch_analyst_access_all_8_tables():
    """Kiểm tra role Analyst được phép truy vấn cả 8 bảng TPC-H với các cột thông thường."""
    context = UserContext(
        user_id="analyst_tpch", session_id="sess_tpch", role=UserRole.ANALYST
    )
    tables = [
        "customer",
        "orders",
        "lineitem",
        "part",
        "partsupp",
        "supplier",
        "nation",
        "region",
    ]
    columns = [
        "c_name",
        "c_mktsegment",
        "o_orderdate",
        "o_totalprice",
        "l_quantity",
        "l_extendedprice",
        "p_name",
        "ps_availqty",
        "s_name",
        "n_name",
        "r_name",
    ]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is True
    assert result.error_type is None
    assert len(result.violating_tables) == 0
    assert len(result.violating_columns) == 0


def test_tpch_analyst_blocked_on_supplier_pii_and_finance():
    """Kiểm tra role Analyst bị chặn khi truy cập PII và tài chính của supplier."""
    context = UserContext(
        user_id="analyst_tpch", session_id="sess_tpch", role=UserRole.ANALYST
    )
    tables = ["supplier"]
    columns = ["s_name", "s_phone", "s_address", "s_acctbal"]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_COLUMN"
    assert "s_phone" in result.violating_columns
    assert "s_address" in result.violating_columns
    assert "s_acctbal" in result.violating_columns


def test_tpch_analyst_blocked_on_wildcard_supplier():
    """Kiểm tra role Analyst bị chặn khi dùng SELECT * trên supplier (chứa s_phone, s_address, s_acctbal)."""
    context = UserContext(
        user_id="analyst_tpch", session_id="sess_tpch", role=UserRole.ANALYST
    )
    tables = ["supplier"]
    columns: list[str] = []

    result = enforce_rbac_policy(
        tables_used=tables,
        columns_used=columns,
        user_context=context,
        has_star=True,
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_COLUMN"
    assert "s_phone" in result.violating_columns
    assert "s_address" in result.violating_columns
    assert "s_acctbal" in result.violating_columns
