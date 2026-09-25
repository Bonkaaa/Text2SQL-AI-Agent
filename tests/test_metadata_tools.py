"""Unit tests cho bộ 4 Strategic Metadata Tools (Component 2.3.1 - TDD).

Kiểm tra:
- search_tables_and_columns: Tra cứu DDL và cấu trúc bảng theo từ khóa.
- get_column_samples_and_values: Lấy giá trị phân loại (categorical values) và dữ liệu mẫu.
- find_join_path: Tìm đường đi ngắn nhất (BFS) và điều kiện JOIN giữa 2 bảng.
- search_business_definition: Tra cứu công thức chuẩn dbt Semantic Metrics.
"""

from src.agents.tools.metadata_tools import (
    find_join_path,
    get_column_samples_and_values,
    search_business_definition,
    search_tables_and_columns,
)


def test_search_tables_and_columns_found():
    """Kiểm tra tìm kiếm bảng và DDL khi có từ khóa liên quan."""
    res = search_tables_and_columns(query="doanh thu đơn hàng", top_k=3)
    assert isinstance(res, list)
    assert len(res) > 0

    tables = [r["table"] for r in res]
    assert "lineitem" in tables or "orders" in tables
    assert "schema_ddl" in res[0]
    assert "CREATE TABLE" in res[0]["schema_ddl"]


def test_search_tables_and_columns_fallback():
    """Kiểm tra fallback khi từ khóa không khớp bảng nào vẫn trả về top bảng cốt lõi."""
    res = search_tables_and_columns(query="từ khóa ngẫu nhiên xyz123", top_k=2)
    assert len(res) <= 2
    assert "table" in res[0]


def test_get_column_samples_and_values_categorical():
    """Kiểm tra lấy danh mục giá trị chuẩn cho c_mktsegment và o_orderstatus."""
    res_segment = get_column_samples_and_values(table="customer", column="c_mktsegment")
    assert res_segment["status"] == "SUCCESS"
    assert "AUTOMOBILE" in res_segment["values"]
    assert "BUILDING" in res_segment["values"]
    assert "MACHINERY" in res_segment["values"]

    res_status = get_column_samples_and_values(table="orders", column="o_orderstatus")
    assert res_status["status"] == "SUCCESS"
    assert "O" in res_status["values"]
    assert "F" in res_status["values"]


def test_get_column_samples_and_values_with_query_filter():
    """Kiểm tra lọc giá trị khi truyền query cụ thể."""
    res = get_column_samples_and_values(
        table="region", column="r_name", query="châu á asia"
    )
    assert res["status"] == "SUCCESS"
    assert any("ASIA" in val for val in res["values"])


def test_get_column_samples_and_values_unknown_column():
    """Kiểm tra phản hồi khi cột hoặc bảng không tồn tại."""
    res = get_column_samples_and_values(table="customer", column="cot_khong_ton_tai")
    assert res["status"] == "NOT_FOUND" or res["values"] == []


def test_find_join_path_direct_connection():
    """Kiểm tra tìm đường nối trực tiếp giữa 2 bảng có khóa ngoại liền kề."""
    res = find_join_path(table_a="orders", table_b="customer")
    assert res["found"] is True
    assert len(res["tables_chain"]) == 2
    assert res["tables_chain"] == ["orders", "customer"]
    assert len(res["join_conditions"]) == 1
    assert "orders.o_custkey = customer.c_custkey" in res["join_conditions"][0]
    assert res["bridge_tables_needed"] == []


def test_find_join_path_multi_hop_customer_to_part():
    """Kiểm tra tìm đường nối đa chặng: customer -> orders -> lineitem -> part."""
    res = find_join_path(table_a="customer", table_b="part")
    assert res["found"] is True
    assert res["tables_chain"] == ["customer", "orders", "lineitem", "part"]
    assert len(res["join_conditions"]) == 3
    assert res["bridge_tables_needed"] == ["orders", "lineitem"]
    conditions_str = " ".join(res["join_conditions"])
    assert "c_custkey" in conditions_str and "o_custkey" in conditions_str
    assert "l_partkey = part.p_partkey" in conditions_str


def test_find_join_path_multi_hop_customer_to_region():
    """Kiểm tra tìm đường nối: customer -> nation -> region."""
    res = find_join_path(table_a="customer", table_b="region")
    assert res["found"] is True
    assert res["tables_chain"] == ["customer", "nation", "region"]
    assert res["bridge_tables_needed"] == ["nation"]


def test_find_join_path_same_table():
    """Kiểm tra khi table_a trùng table_b."""
    res = find_join_path(table_a="lineitem", table_b="lineitem")
    assert res["found"] is True
    assert res["tables_chain"] == ["lineitem"]
    assert res["join_conditions"] == []


def test_find_join_path_invalid_table():
    """Kiểm tra khi truyền tên bảng không hợp lệ."""
    res = find_join_path(table_a="customer", table_b="bang_ao")
    assert res["found"] is False
    assert "error" in res


def test_search_business_definition_found():
    """Kiểm tra tìm kiếm công thức chỉ số doanh thu thuần dbt semantic metric."""
    res = search_business_definition(query="doanh thu thuần")
    assert res["found"] is True
    assert res["metric_id"] == "net_revenue"
    assert "SUM(l_extendedprice * (1 - l_discount))" in res["formula"]
    assert "lineitem" in res["required_tables"]


def test_search_business_definition_gross_profit():
    """Kiểm tra tìm kiếm công thức lợi nhuận gộp."""
    res = search_business_definition(query="lợi nhuận")
    assert res["found"] is True
    assert res["metric_id"] == "gross_profit"
    assert "partsupp" in res["required_tables"]


def test_search_business_definition_not_found():
    """Kiểm tra khi không tìm thấy chỉ số phù hợp."""
    res = search_business_definition(query="chỉ số kì lạ không tồn tại 12345")
    assert res["found"] is False
    assert "available_metrics" in res
