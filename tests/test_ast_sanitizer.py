from src.utils.ast_sanitizer import sanitize_and_validate_sql


def test_valid_simple_select():
    """Kiểm tra câu lệnh SELECT đơn giản hợp lệ."""
    sql = "SELECT c_custkey, c_name FROM customer"
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is True
    assert result.error_type is None
    assert "customer" in result.tables_used
    assert "c_custkey" in result.columns_used
    assert "c_name" in result.columns_used
    # Tự động tiêm LIMIT 1000
    assert "LIMIT 1000" in result.sanitized_sql.upper()


def test_valid_select_with_join_and_cte():
    """Kiểm tra câu lệnh SELECT có JOIN và CTE (WITH clause)."""
    sql = """
    WITH big_orders AS (
        SELECT o_orderkey, o_custkey, o_totalprice
        FROM orders
        WHERE o_totalprice > 50000
    )
    SELECT c.c_name, b.o_totalprice
    FROM customer c
    JOIN big_orders b ON c.c_custkey = b.o_custkey
    LIMIT 20
    """
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is True
    # big_orders là tên CTE, không phải bảng vật lý
    assert "orders" in result.tables_used
    assert "customer" in result.tables_used
    assert "big_orders" not in result.tables_used
    # Giữ nguyên LIMIT 20 vì nhỏ hơn 1000
    assert "LIMIT 20" in result.sanitized_sql.upper()


def test_auto_clamp_excessive_limit():
    """Kiểm tra câu lệnh có LIMIT > 1000 tự động bị hạ về 1000."""
    sql = "SELECT * FROM lineitem LIMIT 5000"
    result = sanitize_and_validate_sql(sql, default_limit=1000)

    assert result.is_valid is True
    assert "LIMIT 1000" in result.sanitized_sql.upper()
    assert "LIMIT 5000" not in result.sanitized_sql.upper()


def test_block_forbidden_dml_drop():
    """Kiểm tra chặn câu lệnh DROP TABLE."""
    sql = "DROP TABLE customer;"
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is False
    assert result.error_type == "FORBIDDEN_STATEMENT"
    assert "SELECT" in result.error_message


def test_block_forbidden_dml_delete():
    """Kiểm tra chặn câu lệnh DELETE."""
    sql = "DELETE FROM orders WHERE o_orderkey = 1"
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is False
    assert result.error_type == "FORBIDDEN_STATEMENT"


def test_block_forbidden_dml_update():
    """Kiểm tra chặn câu lệnh UPDATE."""
    sql = "UPDATE customer SET c_acctbal = 0 WHERE c_custkey = 10"
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is False
    assert result.error_type == "FORBIDDEN_STATEMENT"


def test_block_forbidden_dml_insert():
    """Kiểm tra chặn câu lệnh INSERT."""
    sql = "INSERT INTO region VALUES (6, 'ANTARCTICA', 'Cold region')"
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is False
    assert result.error_type == "FORBIDDEN_STATEMENT"


def test_block_multiple_statements_sql_injection():
    """Kiểm tra chặn SQL Injection dạng nối nhiều câu lệnh với dấu chấm phẩy."""
    sql = "SELECT * FROM customer; DROP TABLE customer;"
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is False
    assert result.error_type == "MULTIPLE_STATEMENTS"


def test_extract_tables_and_columns_accurately():
    """Kiểm tra trích xuất chính xác danh sách bảng và cột để phục vụ kiểm tra RBAC."""
    sql = """
    SELECT c.c_name, c.c_phone, o.o_totalprice
    FROM customer c
    JOIN orders o ON c.c_custkey = o.o_custkey
    WHERE c.c_acctbal > 1000
    """
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is True
    assert set(result.tables_used) == {"customer", "orders"}
    assert "c_name" in result.columns_used
    assert "c_phone" in result.columns_used
    assert "c_acctbal" in result.columns_used
    assert "o_totalprice" in result.columns_used


def test_syntax_error_handling():
    """Kiểm tra xử lý lỗi cú pháp SQL không hợp lệ."""
    sql = "SELECT c_name FROM WHERE GROUP BY ;;"
    result = sanitize_and_validate_sql(sql)

    assert result.is_valid is False
    assert result.error_type == "SYNTAX_ERROR"
    assert result.error_message is not None


def test_empty_query_handling():
    """Kiểm tra câu truy vấn rỗng."""
    result = sanitize_and_validate_sql("   ")

    assert result.is_valid is False
    assert result.error_type == "EMPTY_QUERY"
