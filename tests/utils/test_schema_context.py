"""Unit tests cho Component 2.1: Semantic Schema & Metric Layer Dictionary.

Kiểm tra:
- Khai báo DDL chi tiết 8 bảng TPC-H kèm chú thích tiếng Việt.
- Danh bạ các quan hệ Foreign Key / JOIN chuẩn giữa các bảng.
- Định nghĩa công thức nghiệp vụ chuẩn hóa (dbt Semantic Metrics).
- Hàm render_schema_context kết xuất Markdown context cho LLM Prompt.
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
    """Kiểm tra đầy đủ 8 bảng nghiệp vụ TPC-H."""
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
    assert set(TPCH_TABLE_NAMES) == expected_tables


def test_get_table_schema():
    """Kiểm tra trích xuất schema DDL của từng bảng có chứa cột và comment tiếng Việt."""
    # 1. Bảng customer
    customer_schema = get_table_schema("customer")
    assert customer_schema is not None
    assert "c_custkey" in customer_schema
    assert "c_mktsegment" in customer_schema
    assert "c_phone" in customer_schema
    assert "Khách hàng" in customer_schema

    # 2. Bảng lineitem
    lineitem_schema = get_table_schema("lineitem")
    assert lineitem_schema is not None
    assert "l_orderkey" in lineitem_schema
    assert "l_extendedprice" in lineitem_schema
    assert "l_discount" in lineitem_schema
    assert "l_shipdate" in lineitem_schema

    # 3. Bảng không tồn tại
    assert get_table_schema("non_existent_table") is None


def test_get_all_table_schemas():
    """Kiểm tra hàm lấy tất cả 8 schemas."""
    all_schemas = get_all_table_schemas()
    assert len(all_schemas) == 8
    for table_name in TPCH_TABLE_NAMES:
        assert table_name in all_schemas
        assert len(all_schemas[table_name]) > 0


def test_join_relationships():
    """Kiểm tra danh bạ các quan hệ JOIN chuẩn giữa các bảng TPC-H."""
    joins = get_join_relationships()
    assert len(joins) >= 8

    # Kiểm tra một số quan hệ cốt lõi
    join_pairs = {(j.from_table, j.to_table) for j in joins}
    assert ("lineitem", "orders") in join_pairs or ("orders", "lineitem") in join_pairs
    assert ("orders", "customer") in join_pairs or ("customer", "orders") in join_pairs
    assert ("customer", "nation") in join_pairs or ("nation", "customer") in join_pairs
    assert ("supplier", "nation") in join_pairs or ("nation", "supplier") in join_pairs
    assert ("nation", "region") in join_pairs or ("region", "nation") in join_pairs
    assert ("lineitem", "part") in join_pairs or ("part", "lineitem") in join_pairs
    assert ("partsupp", "part") in join_pairs or ("part", "partsupp") in join_pairs
    assert ("partsupp", "supplier") in join_pairs or (
        "supplier",
        "partsupp",
    ) in join_pairs

    # Kiểm tra cấu trúc JoinRelationship dataclass/model
    sample_join = next(
        j
        for j in joins
        if (j.from_table == "lineitem" and j.to_table == "orders")
        or (j.from_table == "orders" and j.to_table == "lineitem")
    )
    assert isinstance(sample_join, JoinRelationship)
    assert "orderkey" in sample_join.condition.lower()


def test_semantic_metrics():
    """Kiểm tra từ điển công thức tính toán chuẩn (dbt Semantic Metrics Layer)."""
    metrics = get_semantic_metrics()
    assert len(metrics) >= 6

    # 1. Doanh thu thuần (Net Revenue)
    net_rev = metrics.get("net_revenue")
    assert net_rev is not None
    assert isinstance(net_rev, SemanticMetric)
    assert "SUM(l_extendedprice * (1 - l_discount))" in net_rev.formula

    # 2. Chiết khấu trung bình (Avg Discount)
    avg_disc = metrics.get("avg_discount")
    assert avg_disc is not None
    assert "AVG(l_discount)" in avg_disc.formula

    # 3. Lợi nhuận gộp ước tính (Estimated Gross Profit)
    gross_profit = metrics.get("gross_profit")
    assert gross_profit is not None
    assert (
        "SUM(l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity)"
        in gross_profit.formula
    )

    # 4. Doanh thu gộp (Gross Revenue)
    gross_rev = metrics.get("gross_revenue")
    assert gross_rev is not None
    assert "SUM(l_extendedprice)" in gross_rev.formula

    # 5. Tỷ lệ hoàn hàng (Return Rate)
    return_rate = metrics.get("return_rate")
    assert return_rate is not None
    assert "l_returnflag = 'R'" in return_rate.formula


def test_render_schema_context_all():
    """Kiểm tra render toàn bộ schema context ra Markdown."""
    context = render_schema_context()
    assert isinstance(context, str)

    # Phải chứa DDL các bảng chính
    assert "customer" in context
    assert "orders" in context
    assert "lineitem" in context

    # Phải chứa phần JOIN chuẩn
    assert "QUAN HỆ JOIN CHUẨN" in context or "JOIN" in context
    assert "l_orderkey = o_orderkey" in context or "orders.o_orderkey" in context

    # Phải chứa phần Metrics
    assert "CÔNG THỨC CHUẨN" in context or "METRICS" in context
    assert "l_extendedprice * (1 - l_discount)" in context


def test_render_schema_context_filtered():
    """Kiểm tra render schema context có chọn lọc bảng liên quan."""
    context = render_schema_context(selected_tables=["customer", "orders"])
    assert "BẢNG customer" in context or "customer" in context
    assert "BẢNG orders" in context or "orders" in context
    # Không render DDL chi tiết của partsupp nếu không được chọn
    assert "CREATE TABLE partsupp" not in context

    # Phải có JOIN liên quan giữa customer và orders
    assert (
        "o_custkey = c_custkey" in context
        or "orders.o_custkey = customer.c_custkey" in context
    )


def test_table_keywords_mapping():
    """Kiểm tra từ điển từ khóa đồng nghĩa của 8 bảng TPC-H."""
    from src.utils.table_keywords import TABLE_KEYWORD_MAP, get_table_keywords

    keywords = get_table_keywords()
    assert len(keywords) == 8
    assert "customer" in keywords
    assert "khách hàng" in keywords["customer"]
    assert "lineitem" in keywords
    assert "doanh thu" in keywords["lineitem"]
    assert TABLE_KEYWORD_MAP == keywords
