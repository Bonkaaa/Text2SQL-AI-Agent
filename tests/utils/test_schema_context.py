"""Unit tests cho Component 2.1: Semantic Schema & Metric Layer Dictionary (TPC-DS 24 bảng).

Kiểm tra:
- Khai báo DDL chi tiết 24 bảng TPC-DS kèm chú thích tiếng Việt.
- Danh bạ các quan hệ Foreign Key / JOIN chuẩn giữa các bảng (Snowflake Schema).
- Định nghĩa công thức nghiệp vụ bán lẻ chuẩn hóa (dbt Semantic Metrics).
- Hàm render_schema_context kết xuất Markdown context cho LLM Prompt.
"""

from src.utils.schema_context import (
    TPCDS_TABLE_NAMES,
    JoinRelationship,
    SemanticMetric,
    get_all_table_schemas,
    get_join_relationships,
    get_semantic_metrics,
    get_table_schema,
    render_schema_context,
)


def test_tpcds_table_names():
    """Kiểm tra đầy đủ 24 bảng nghiệp vụ TPC-DS."""
    expected_tables = {
        "store_sales",
        "store_returns",
        "catalog_sales",
        "catalog_returns",
        "web_sales",
        "web_returns",
        "inventory",
        "item",
        "customer",
        "customer_address",
        "customer_demographics",
        "date_dim",
        "household_demographics",
        "income_band",
        "promotion",
        "reason",
        "ship_mode",
        "time_dim",
        "warehouse",
        "store",
        "call_center",
        "catalog_page",
        "web_page",
        "web_site",
    }
    assert len(TPCDS_TABLE_NAMES) == 24
    assert set(TPCDS_TABLE_NAMES) == expected_tables


def test_get_table_schema():
    """Kiểm tra trích xuất schema DDL của từng bảng có chứa cột và comment tiếng Việt."""
    # 1. Bảng store_sales
    store_sales_schema = get_table_schema("store_sales")
    assert store_sales_schema is not None
    assert "ss_sold_date_sk" in store_sales_schema
    assert "ss_item_sk" in store_sales_schema
    assert "ss_customer_sk" in store_sales_schema
    assert "ss_net_profit" in store_sales_schema
    assert "store_sales" in store_sales_schema

    # 2. Bảng item
    item_schema = get_table_schema("item")
    assert item_schema is not None
    assert "i_item_sk" in item_schema
    assert "i_category" in item_schema
    assert "i_current_price" in item_schema

    # 3. Bảng date_dim (Bảng thời gian bắt buộc)
    date_schema = get_table_schema("date_dim")
    assert date_schema is not None
    assert "d_date_sk" in date_schema
    assert "d_year" in date_schema
    assert "d_moy" in date_schema

    # 4. Bảng customer
    customer_schema = get_table_schema("customer")
    assert customer_schema is not None
    assert "c_customer_sk" in customer_schema
    assert "c_current_addr_sk" in customer_schema

    # 5. Bảng không tồn tại
    assert get_table_schema("non_existent_table_xyz") is None


def test_get_all_table_schemas():
    """Kiểm tra hàm lấy tất cả 24 schemas."""
    all_schemas = get_all_table_schemas()
    assert len(all_schemas) == 24
    for table_name in TPCDS_TABLE_NAMES:
        assert table_name in all_schemas
        assert len(all_schemas[table_name]) > 0


def test_join_relationships():
    """Kiểm tra danh bạ các quan hệ JOIN chuẩn giữa các bảng TPC-DS."""
    joins = get_join_relationships()
    assert len(joins) >= 35

    join_pairs = {(j.from_table, j.to_table) for j in joins}

    # Fact sales nối date_dim
    assert ("store_sales", "date_dim") in join_pairs or (
        "date_dim",
        "store_sales",
    ) in join_pairs
    assert ("web_sales", "date_dim") in join_pairs or (
        "date_dim",
        "web_sales",
    ) in join_pairs
    assert ("catalog_sales", "date_dim") in join_pairs or (
        "date_dim",
        "catalog_sales",
    ) in join_pairs

    # Fact sales nối item
    assert ("store_sales", "item") in join_pairs or (
        "item",
        "store_sales",
    ) in join_pairs
    assert ("web_sales", "item") in join_pairs or ("item", "web_sales") in join_pairs
    assert ("catalog_sales", "item") in join_pairs or (
        "item",
        "catalog_sales",
    ) in join_pairs

    # Snowflake Dimension joins
    assert ("customer", "customer_address") in join_pairs or (
        "customer_address",
        "customer",
    ) in join_pairs
    assert ("customer", "customer_demographics") in join_pairs or (
        "customer_demographics",
        "customer",
    ) in join_pairs
    assert ("customer", "household_demographics") in join_pairs or (
        "household_demographics",
        "customer",
    ) in join_pairs
    assert ("household_demographics", "income_band") in join_pairs or (
        "income_band",
        "household_demographics",
    ) in join_pairs

    # Inventory joins
    assert ("inventory", "warehouse") in join_pairs or (
        "warehouse",
        "inventory",
    ) in join_pairs
    assert ("inventory", "item") in join_pairs or ("item", "inventory") in join_pairs

    # Kiểm tra cấu trúc JoinRelationship dataclass
    sample_join = next(
        j for j in joins if (j.from_table == "store_sales" and j.to_table == "date_dim")
    )
    assert isinstance(sample_join, JoinRelationship)
    assert "d_date_sk" in sample_join.condition


def test_semantic_metrics():
    """Kiểm tra từ điển công thức tính toán chuẩn bán lẻ (dbt Semantic Metrics)."""
    metrics = get_semantic_metrics()
    assert len(metrics) >= 8

    # 1. Doanh thu thuần cửa hàng (store_net_sales)
    store_sales = metrics.get("store_net_sales")
    assert store_sales is not None
    assert isinstance(store_sales, SemanticMetric)
    assert "SUM(ss_net_paid)" in store_sales.formula

    # 2. Doanh thu thuần trực tuyến (web_net_sales)
    web_sales = metrics.get("web_net_sales")
    assert web_sales is not None
    assert "SUM(ws_net_paid)" in web_sales.formula

    # 3. Lợi nhuận ròng (net_profit)
    profit = metrics.get("net_profit")
    assert profit is not None
    assert "SUM(ss_net_profit)" in profit.formula

    # 4. Tỷ lệ hoàn trả (return_rate)
    return_rate = metrics.get("return_rate")
    assert return_rate is not None
    assert "sr_return_amt" in return_rate.formula

    # 5. Tồn kho (inventory_quantity)
    inv = metrics.get("inventory_quantity")
    assert inv is not None
    assert "inv_quantity_on_hand" in inv.formula


def test_render_schema_context_all():
    """Kiểm tra render toàn bộ schema context ra Markdown."""
    context = render_schema_context()
    assert isinstance(context, str)

    # Phải chứa DDL các bảng chính
    assert "store_sales" in context
    assert "item" in context
    assert "date_dim" in context
    assert "customer" in context

    # Phải chứa phần JOIN chuẩn
    assert "QUAN HỆ JOIN CHUẨN" in context or "JOIN" in context
    assert "d_date_sk" in context

    # Phải chứa phần Metrics
    assert "CÔNG THỨC CHUẨN" in context or "METRICS" in context
    assert "ss_net_paid" in context


def test_render_schema_context_filtered():
    """Kiểm tra render schema context có chọn lọc bảng liên quan."""
    context = render_schema_context(selected_tables=["customer", "customer_address"])
    assert "customer" in context
    assert "customer_address" in context
    # Không render DDL chi tiết của web_returns nếu không được chọn
    assert "CREATE TABLE web_returns" not in context

    # Phải có JOIN liên quan giữa customer và customer_address
    assert (
        "c_current_addr_sk = ca_address_sk" in context
        or "customer_address.ca_address_sk" in context
    )


def test_table_keywords_mapping():
    """Kiểm tra từ điển từ khóa đồng nghĩa của 24 bảng TPC-DS."""
    from src.utils.table_keywords import TABLE_KEYWORD_MAP, get_table_keywords

    keywords = get_table_keywords()
    assert len(keywords) == 24
    assert "store_sales" in keywords
    assert "bán lẻ" in keywords["store_sales"]
    assert "web_sales" in keywords
    assert "online" in keywords["web_sales"]
    assert "date_dim" in keywords
    assert "năm" in keywords["date_dim"]
    assert TABLE_KEYWORD_MAP == keywords
