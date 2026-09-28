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


def test_analyst_blocked_on_wildcard_select_star_sensitive_table():
    """Kiểm tra role Analyst bị chặn khi dùng wildcard SELECT * trên bảng chứa cột PII (customer)."""
    context = UserContext(
        user_id="analyst_1", session_id="sess_1", role=UserRole.ANALYST
    )
    # Giả lập SELECT * FROM customer: columns_used rỗng nếu chưa expand, nhưng has_star=True
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


def test_analyst_blocked_on_wildcard_unexpandable_table():
    """Kiểm tra role Analyst bị từ chối Fail-Closed khi dùng wildcard trên bảng không thuộc TPC-H/TPC-DS."""
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


def test_tpcds_analyst_access_allowed_tables_and_columns():
    """Kiểm tra role Analyst được phép truy vấn 24 bảng TPC-DS và cột nghiệp vụ."""
    context = UserContext(
        user_id="analyst_tpcds", session_id="sess_tpcds", role=UserRole.ANALYST
    )
    tables = ["store_sales", "date_dim", "item", "store"]
    columns = ["ss_net_paid", "d_year", "i_category", "s_store_name"]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is True
    assert result.error_type is None
    assert len(result.violating_tables) == 0
    assert len(result.violating_columns) == 0


def test_tpcds_analyst_blocked_on_pii_and_income_columns():
    """Kiểm tra role Analyst bị chặn khi truy cập PII (email, birth year, street) và thu nhập."""
    context = UserContext(
        user_id="analyst_tpcds", session_id="sess_tpcds", role=UserRole.ANALYST
    )
    tables = ["customer", "customer_address", "income_band"]
    columns = [
        "c_customer_sk",
        "c_email_address",
        "c_birth_year",
        "ca_street_name",
        "ib_lower_bound",
    ]

    result = enforce_rbac_policy(
        tables_used=tables, columns_used=columns, user_context=context
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_COLUMN"
    assert "c_email_address" in result.violating_columns
    assert "c_birth_year" in result.violating_columns
    assert "ca_street_name" in result.violating_columns
    assert "ib_lower_bound" in result.violating_columns


def test_tpcds_analyst_blocked_on_wildcard_customer_address():
    """Kiểm tra role Analyst bị chặn khi dùng SELECT * trên customer_address (chứa ca_street_name)."""
    context = UserContext(
        user_id="analyst_tpcds", session_id="sess_tpcds", role=UserRole.ANALYST
    )
    tables = ["customer_address"]
    columns: list[str] = []

    result = enforce_rbac_policy(
        tables_used=tables,
        columns_used=columns,
        user_context=context,
        has_star=True,
    )

    assert result.is_allowed is False
    assert result.error_type == "UNAUTHORIZED_COLUMN"
    assert "ca_street_name" in result.violating_columns
    assert "ca_street_number" in result.violating_columns
