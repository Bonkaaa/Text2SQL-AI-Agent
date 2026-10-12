"""Unit tests cho Component 2.1: Semantic Schema & Metric Layer Dictionary (TPC-H 8 bảng).

Kiểm tra:
- Khai báo DDL chi tiết 8 bảng TPC-H kèm chú thích tiếng Việt cho từng cột.
- Danh bạ các quan hệ Foreign Key / JOIN chuẩn giữa các bảng TPC-H.
- Định nghĩa công thức nghiệp vụ chuỗi cung ứng chuẩn hóa (dbt Semantic Metrics).
- Hàm render_schema_context kết xuất Markdown context cho LLM Prompt với ngày tự nhiên.
"""

from src.utils.schema_context import (
    TPCH_TABLE_NAMES,
    JoinRelationship,
    SemanticMetric,
    get_all_table_schemas,
    get_join_relationships,
    get_semantic_metrics,
    get_table_schema,
    render_schema_context,
)


def test_tpch_table_names():
    """Kiểm tra đầy đủ đúng 8 bảng nghiệp vụ TPC-H."""
    expected_tables = {
        "region",
        "nation",
        "supplier",
        "customer",
        "part",
        "partsupp",
        "orders",
        "lineitem",
    }
    assert len(TPCH_TABLE_NAMES) == 8
    assert set(TPCH_TABLE_NAMES) == expected_tables


def test_get_table_schema():
    """Kiểm tra trích xuất schema DDL của từng bảng có chứa cột và comment tiếng Việt."""
    # 1. Bảng lineitem
    lineitem_schema = get_table_schema("lineitem")
    assert lineitem_schema is not None
    assert "l_orderkey" in lineitem_schema
    assert "l_extendedprice" in lineitem_schema
    assert "l_discount" in lineitem_schema
    assert "l_shipdate" in lineitem_schema

    # 2. Bảng orders
    orders_schema = get_table_schema("orders")
    assert orders_schema is not None
    assert "o_orderkey" in orders_schema
    assert "o_custkey" in orders_schema
    assert "o_orderdate" in orders_schema
    assert "o_orderstatus" in orders_schema

    # 3. Bảng customer
    customer_schema = get_table_schema("customer")
    assert customer_schema is not None
    assert "c_custkey" in customer_schema
    assert "c_mktsegment" in customer_schema

    # 4. Bảng part & partsupp
    part_schema = get_table_schema("part")
    assert part_schema is not None
    assert "p_partkey" in part_schema

    partsupp_schema = get_table_schema("partsupp")
    assert partsupp_schema is not None
    assert "ps_availqty" in partsupp_schema
    assert "ps_supplycost" in partsupp_schema

    # 5. Clean-cut: date_dim và store_sales không được tồn tại
    assert get_table_schema("date_dim") is None
    assert get_table_schema("store_sales") is None
    assert get_table_schema("non_existent_table") is None


def test_get_all_table_schemas():
    """Kiểm tra hàm lấy tất cả 8 schemas của TPC-H."""
    all_schemas = get_all_table_schemas()
    assert len(all_schemas) == 8
    for table_name in TPCH_TABLE_NAMES:
        assert table_name in all_schemas
        assert len(all_schemas[table_name]) > 0


def test_join_relationships():
    """Kiểm tra danh bạ các quan hệ JOIN chuẩn giữa các bảng TPC-H."""
    joins = get_join_relationships()
    assert len(joins) >= 8

    join_pairs = {(j.from_table, j.to_table) for j in joins}

    # customer nối orders
    assert ("orders", "customer") in join_pairs or ("customer", "orders") in join_pairs
    # orders nối lineitem
    assert ("lineitem", "orders") in join_pairs or ("orders", "lineitem") in join_pairs
    # part/supplier nối partsupp
    assert ("partsupp", "part") in join_pairs or ("part", "partsupp") in join_pairs
    assert ("partsupp", "supplier") in join_pairs or ("supplier", "partsupp") in join_pairs
    # geography
    assert ("customer", "nation") in join_pairs or ("nation", "customer") in join_pairs
    assert ("nation", "region") in join_pairs or ("region", "nation") in join_pairs

    # Kiểm tra cấu trúc JoinRelationship dataclass
    sample_join = next(
        j for j in joins if (j.from_table == "orders" and j.to_table == "customer") or (j.from_table == "customer" and j.to_table == "orders")
    )
    assert isinstance(sample_join, JoinRelationship)
    assert "custkey" in sample_join.condition


def test_semantic_metrics():
    """Kiểm tra từ điển công thức tính toán chuẩn chuỗi cung ứng TPC-H (dbt Semantic Metrics)."""
    metrics = get_semantic_metrics()
    assert len(metrics) >= 4

    # 1. Doanh thu thuần (net_revenue)
    net_rev = metrics.get("net_revenue")
    assert net_rev is not None
    assert isinstance(net_rev, SemanticMetric)
    assert "l_extendedprice * (1 - l_discount)" in net_rev.formula

    # 2. Doanh thu gộp (gross_revenue)
    gross_rev = metrics.get("gross_revenue")
    assert gross_rev is not None
    assert "l_extendedprice" in gross_rev.formula

    # 3. Giá trị tồn kho (inventory_value)
    inv_val = metrics.get("inventory_value")
    assert inv_val is not None
    assert "ps_availqty * ps_supplycost" in inv_val.formula

    # 4. Tỷ lệ trễ hạn giao (late_delivery_rate)
    late_del = metrics.get("late_delivery_rate")
    assert late_del is not None
    assert "l_receiptdate > l_commitdate" in late_del.formula


def test_render_schema_context_all():
    """Kiểm tra render toàn bộ schema context ra Markdown."""
    context = render_schema_context()
    assert isinstance(context, str)

    # Phải chứa DDL các bảng TPC-H chính
    assert "lineitem" in context
    assert "orders" in context
    assert "customer" in context

    # Không được chứa date_dim hay store_sales
    assert "date_dim" not in context
    assert "store_sales" not in context

    # Phải chứa phần JOIN chuẩn và Metrics
    assert "QUAN HỆ JOIN CHUẨN" in context or "JOIN" in context
    assert "l_extendedprice" in context


def test_render_schema_context_filtered():
    """Kiểm tra render schema context có chọn lọc bảng liên quan."""
    context = render_schema_context(selected_tables=["customer", "orders"])
    assert "customer" in context
    assert "orders" in context
    # Không render DDL chi tiết của partsupp nếu không được chọn
    assert "CREATE TABLE partsupp" not in context
