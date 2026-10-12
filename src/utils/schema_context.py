"""Từ điển lược đồ dữ liệu ngữ nghĩa & tầng chỉ số nghiệp vụ TPC-H (Semantic Schema & Metric Layer).

Component 2.1:
- Định nghĩa DDL chi tiết 8 bảng TPC-H có kèm chú thích tiếng Việt cho từng cột.
- Từ điển quan hệ khóa ngoại (Foreign Key) và quy tắc JOIN chuẩn (Star/Snowflake Schema).
- Định nghĩa các công thức tính toán chỉ số nghiệp vụ chuẩn (dbt Semantic Metrics Layer).
- Hàm kết xuất Markdown Schema Context phục vụ việc xây dựng prompt cho SQL Generator.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# Danh sách 8 bảng nghiệp vụ TPC-H (Chuỗi cung ứng & Bán lẻ)
TPCH_TABLE_NAMES: Final[list[str]] = [
    "region",
    "nation",
    "supplier",
    "customer",
    "part",
    "partsupp",
    "orders",
    "lineitem",
]


@dataclass(frozen=True)
class JoinRelationship:
    """Mô tả quan hệ JOIN chuẩn giữa hai bảng trong TPC-H."""

    from_table: str
    to_table: str
    condition: str
    join_type: str = "INNER"
    description: str = ""


@dataclass(frozen=True)
class SemanticMetric:
    """Định nghĩa chỉ số nghiệp vụ chuẩn (dbt Semantic Metric)."""

    metric_id: str
    vietnamese_name: str
    formula: str
    description: str
    required_tables: list[str]


# ==============================================================================
# 1. DDL CHI TIẾT 8 BẢNG TPC-H KÈM CHÚ THÍCH TIẾNG VIỆT
# ==============================================================================

TPCH_TABLE_SCHEMAS: Final[dict[str, str]] = {
    "region": """\
-- BẢNG: region (Châu lục / Khu vực kinh tế)
CREATE TABLE region (
    r_regionkey INTEGER PRIMARY KEY,    -- Mã khu vực địa lý (0: AFRICA, 1: AMERICA, 2: ASIA, 3: EUROPE, 4: MIDDLE EAST)
    r_name VARCHAR(25) NOT NULL,        -- Tên châu lục (AFRICA, AMERICA, ASIA, EUROPE, MIDDLE EAST)
    r_comment VARCHAR(152)             -- Ghi chú/mô tả khu vực
);""",
    "nation": """\
-- BẢNG: nation (Quốc gia thành viên)
CREATE TABLE nation (
    n_nationkey INTEGER PRIMARY KEY,    -- Mã quốc gia (0-24)
    n_name VARCHAR(25) NOT NULL,        -- Tên quốc gia (VIETNAM, JAPAN, CHINA, UNITED STATES, GERMANY...)
    n_regionkey INTEGER NOT NULL,       -- Khóa ngoại tham chiếu region(r_regionkey)
    n_comment VARCHAR(152)             -- Ghi chú quốc gia
);""",
    "supplier": """\
-- BẢNG: supplier (Nhà cung cấp hàng hóa)
CREATE TABLE supplier (
    s_suppkey INTEGER PRIMARY KEY,      -- Mã nhà cung cấp
    s_name VARCHAR(25) NOT NULL,        -- Tên nhà cung cấp (Supplier#000000001)
    s_address VARCHAR(40) NOT NULL,     -- Địa chỉ trụ sở/kho (PII - CẤM Analyst)
    s_nationkey INTEGER NOT NULL,       -- Khóa ngoại tham chiếu nation(n_nationkey)
    s_phone VARCHAR(15) NOT NULL,       -- Số điện thoại (PII - CẤM Analyst)
    s_acctbal DECIMAL(15, 2) NOT NULL,  -- Số dư tài khoản đối tác (Tài chính - CẤM Analyst)
    s_comment VARCHAR(101)             -- Đánh giá/khiếu nại nhà cung cấp
);""",
    "customer": """\
-- BẢNG: customer (Khách hàng)
CREATE TABLE customer (
    c_custkey INTEGER PRIMARY KEY,      -- Mã khách hàng
    c_name VARCHAR(25) NOT NULL,        -- Tên khách hàng (Customer#000000001)
    c_address VARCHAR(40) NOT NULL,     -- Địa chỉ cá nhân (PII - CẤM Analyst)
    c_nationkey INTEGER NOT NULL,       -- Khóa ngoại tham chiếu nation(n_nationkey)
    c_phone VARCHAR(15) NOT NULL,       -- Số điện thoại (PII - CẤM Analyst)
    c_acctbal DECIMAL(15, 2) NOT NULL,  -- Số dư tài khoản khách hàng (Tài chính - CẤM Analyst)
    c_mktsegment VARCHAR(10) NOT NULL,  -- Phân khúc thị trường (AUTOMOBILE, BUILDING, FURNITURE, HOUSEHOLD, MACHINERY)
    c_comment VARCHAR(117)             -- Ghi chú khách hàng
);""",
    "part": """\
-- BẢNG: part (Danh mục linh kiện / mặt hàng)
CREATE TABLE part (
    p_partkey INTEGER PRIMARY KEY,      -- Mã mặt hàng/linh kiện
    p_name VARCHAR(55) NOT NULL,        -- Tên mặt hàng
    p_mfgr VARCHAR(25) NOT NULL,        -- Nhà sản xuất (Manufacturer#1...)
    p_brand VARCHAR(10) NOT NULL,       -- Thương hiệu (Brand#11...)
    p_type VARCHAR(25) NOT NULL,        -- Loại linh kiện (ECONOMY ANODIZED STEEL, PROMO POLISHED BRASS...)
    p_size INTEGER NOT NULL,            -- Kích cỡ linh kiện (1-50)
    p_container VARCHAR(10) NOT NULL,   -- Quy cách đóng gói (SM CASE, JUMBO BOX, MED BAG...)
    p_retailprice DECIMAL(15, 2) NOT NULL, -- Giá bán lẻ niêm yết (USD)
    p_comment VARCHAR(23)              -- Mô tả chi tiết
);""",
    "partsupp": """\
-- BẢNG: partsupp (Mối quan hệ cung ứng - Tồn kho mặt hàng từ nhà cung cấp)
CREATE TABLE partsupp (
    ps_partkey INTEGER NOT NULL,        -- Khóa ngoại tham chiếu part(p_partkey)
    ps_suppkey INTEGER NOT NULL,        -- Khóa ngoại tham chiếu supplier(s_suppkey)
    ps_availqty INTEGER NOT NULL,       -- Số lượng tồn kho sẵn sàng cung cấp
    ps_supplycost DECIMAL(15, 2) NOT NULL, -- Đơn giá chi phí nhập hàng từ nhà cung cấp
    ps_comment VARCHAR(199),           -- Ghi chú tồn kho
    PRIMARY KEY (ps_partkey, ps_suppkey)
);""",
    "orders": """\
-- BẢNG: orders (Đơn đặt hàng)
CREATE TABLE orders (
    o_orderkey INTEGER PRIMARY KEY,     -- Mã đơn đặt hàng
    o_custkey INTEGER NOT NULL,         -- Khóa ngoại tham chiếu customer(c_custkey)
    o_orderstatus VARCHAR(1) NOT NULL,  -- Trạng thái đơn (O: Đang xử lý, F: Đã hoàn tất, P: Chờ duyệt)
    o_totalprice DECIMAL(15, 2) NOT NULL, -- Tổng tiền đơn hàng
    o_orderdate DATE NOT NULL,          -- Ngày đặt hàng (Định dạng: YYYY-MM-DD - Cột ngày tự nhiên)
    o_orderpriority VARCHAR(15) NOT NULL, -- Mức độ ưu tiên (1-URGENT, 2-HIGH, 3-MEDIUM, 4-NOT SPECIFIED, 5-LOW)
    o_clerk VARCHAR(15) NOT NULL,       -- Nhân viên phụ trách (Clerk#000000001)
    o_shippriority INTEGER NOT NULL,    -- Thứ tự ưu tiên vận chuyển
    o_comment VARCHAR(79)              -- Ghi chú đơn hàng
);""",
    "lineitem": """\
-- BẢNG: lineitem (Chi tiết từng dòng sản phẩm trong đơn hàng - Bảng sự kiện chính)
CREATE TABLE lineitem (
    l_orderkey INTEGER NOT NULL,        -- Khóa ngoại tham chiếu orders(o_orderkey)
    l_partkey INTEGER NOT NULL,         -- Khóa ngoại tham chiếu part(p_partkey)
    l_suppkey INTEGER NOT NULL,         -- Khóa ngoại tham chiếu supplier(s_suppkey)
    l_linenumber INTEGER NOT NULL,      -- Số thứ tự dòng hàng trong đơn
    l_quantity DECIMAL(15, 2) NOT NULL, -- Số lượng đặt mua
    l_extendedprice DECIMAL(15, 2) NOT NULL, -- Giá gốc = l_quantity * p_retailprice
    l_discount DECIMAL(15, 2) NOT NULL, -- Tỷ lệ chiết khấu (0.00 đến 0.10, tức 0% - 10%)
    l_tax DECIMAL(15, 2) NOT NULL,      -- Tỷ lệ thuế VAT (0.00 đến 0.08, tức 0% - 8%)
    l_returnflag VARCHAR(1) NOT NULL,   -- Cờ hoàn trả (R: Hoàn hàng, A: Chấp nhận, N: Chưa xử lý)
    l_linestatus VARCHAR(1) NOT NULL,   -- Trạng thái dòng hàng (O: Mở, F: Đã xuất xong)
    l_shipdate DATE NOT NULL,           -- Ngày giao hàng xuất kho (Định dạng DATE tự nhiên)
    l_commitdate DATE NOT NULL,         -- Ngày cam kết giao cho khách
    l_receiptdate DATE NOT NULL,        -- Ngày khách thực nhận hàng
    l_shipinstruct VARCHAR(25) NOT NULL, -- Hướng dẫn giao (DELIVER IN PERSON, TAKE BACK RETURN, NONE)
    l_shipmode VARCHAR(10) NOT NULL,    -- Phương thức vận chuyển (AIR, FOB, MAIL, RAIL, REG AIR, SHIP, TRUCK)
    l_comment VARCHAR(44),             -- Ghi chú dòng hàng
    PRIMARY KEY (l_orderkey, l_linenumber)
);""",
}

# Danh sách cột tương ứng từng bảng phục vụ kiểm tra RBAC Wildcard
TPCH_TABLE_COLUMNS: Final[dict[str, list[str]]] = {
    "region": ["r_regionkey", "r_name", "r_comment"],
    "nation": ["n_nationkey", "n_name", "n_regionkey", "n_comment"],
    "supplier": [
        "s_suppkey",
        "s_name",
        "s_address",
        "s_nationkey",
        "s_phone",
        "s_acctbal",
        "s_comment",
    ],
    "customer": [
        "c_custkey",
        "c_name",
        "c_address",
        "c_nationkey",
        "c_phone",
        "c_acctbal",
        "c_mktsegment",
        "c_comment",
    ],
    "part": [
        "p_partkey",
        "p_name",
        "p_mfgr",
        "p_brand",
        "p_type",
        "p_size",
        "p_container",
        "p_retailprice",
        "p_comment",
    ],
    "partsupp": [
        "ps_partkey",
        "ps_suppkey",
        "ps_availqty",
        "ps_supplycost",
        "ps_comment",
    ],
    "orders": [
        "o_orderkey",
        "o_custkey",
        "o_orderstatus",
        "o_totalprice",
        "o_orderdate",
        "o_orderpriority",
        "o_clerk",
        "o_shippriority",
        "o_comment",
    ],
    "lineitem": [
        "l_orderkey",
        "l_partkey",
        "l_suppkey",
        "l_linenumber",
        "l_quantity",
        "l_extendedprice",
        "l_discount",
        "l_tax",
        "l_returnflag",
        "l_linestatus",
        "l_shipdate",
        "l_commitdate",
        "l_receiptdate",
        "l_shipinstruct",
        "l_shipmode",
        "l_comment",
    ],
}


# ==============================================================================
# 2. QUAN HỆ JOIN CHUẨN GIỮA CÁC BẢNG (STAR / SNOWFLAKE SCHEMA)
# ==============================================================================

TPCH_JOIN_RELATIONSHIPS: Final[list[JoinRelationship]] = [
    JoinRelationship(
        from_table="orders",
        to_table="customer",
        condition="orders.o_custkey = customer.c_custkey",
        join_type="INNER",
        description="Nối đơn hàng với khách hàng đặt đơn",
    ),
    JoinRelationship(
        from_table="lineitem",
        to_table="orders",
        condition="lineitem.l_orderkey = orders.o_orderkey",
        join_type="INNER",
        description="Nối chi tiết dòng sản phẩm với đơn hàng tổng thể",
    ),
    JoinRelationship(
        from_table="lineitem",
        to_table="part",
        condition="lineitem.l_partkey = part.p_partkey",
        join_type="INNER",
        description="Nối chi tiết đơn hàng với danh mục linh kiện/mặt hàng",
    ),
    JoinRelationship(
        from_table="lineitem",
        to_table="supplier",
        condition="lineitem.l_suppkey = supplier.s_suppkey",
        join_type="INNER",
        description="Nối chi tiết đơn hàng với nhà cung cấp linh kiện",
    ),
    JoinRelationship(
        from_table="partsupp",
        to_table="part",
        condition="partsupp.ps_partkey = part.p_partkey",
        join_type="INNER",
        description="Nối tồn kho nhà cung cấp với linh kiện",
    ),
    JoinRelationship(
        from_table="partsupp",
        to_table="supplier",
        condition="partsupp.ps_suppkey = supplier.s_suppkey",
        join_type="INNER",
        description="Nối tồn kho nhà cung cấp với thông tin nhà cung cấp",
    ),
    JoinRelationship(
        from_table="lineitem",
        to_table="partsupp",
        condition="lineitem.l_partkey = partsupp.ps_partkey AND lineitem.l_suppkey = partsupp.ps_suppkey",
        join_type="INNER",
        description="Nối chi tiết dòng hàng với tồn kho và chi phí nhập kho",
    ),
    JoinRelationship(
        from_table="customer",
        to_table="nation",
        condition="customer.c_nationkey = nation.n_nationkey",
        join_type="INNER",
        description="Nối khách hàng với quốc gia cư trú",
    ),
    JoinRelationship(
        from_table="supplier",
        to_table="nation",
        condition="supplier.s_nationkey = nation.n_nationkey",
        join_type="INNER",
        description="Nối nhà cung cấp với quốc gia đặt trụ sở",
    ),
    JoinRelationship(
        from_table="nation",
        to_table="region",
        condition="nation.n_regionkey = region.r_regionkey",
        join_type="INNER",
        description="Nối quốc gia với khu vực/châu lục",
    ),
]


# ==============================================================================
# 3. CHỈ SỐ NGHIỆP VỤ CHUẨN (dbt SEMANTIC METRICS LAYER)
# ==============================================================================

TPCH_SEMANTIC_METRICS: Final[dict[str, SemanticMetric]] = {
    "net_revenue": SemanticMetric(
        metric_id="net_revenue",
        vietnamese_name="Doanh thu thuần",
        formula="SUM(l_extendedprice * (1 - l_discount))",
        description="Doanh thu thực tế sau khi trừ chiết khấu",
        required_tables=["lineitem"],
    ),
    "gross_revenue": SemanticMetric(
        metric_id="gross_revenue",
        vietnamese_name="Doanh thu gộp",
        formula="SUM(l_extendedprice)",
        description="Tổng giá trị hàng hóa theo giá niêm yết chưa trừ chiết khấu",
        required_tables=["lineitem"],
    ),
    "total_discount": SemanticMetric(
        metric_id="total_discount",
        vietnamese_name="Tổng tiền chiết khấu",
        formula="SUM(l_extendedprice * l_discount)",
        description="Tổng số tiền giảm giá chiết khấu cho khách hàng",
        required_tables=["lineitem"],
    ),
    "total_tax": SemanticMetric(
        metric_id="total_tax",
        vietnamese_name="Tổng thuế thu được",
        formula="SUM(l_extendedprice * (1 - l_discount) * l_tax)",
        description="Tổng số tiền thuế VAT thu được từ các đơn hàng",
        required_tables=["lineitem"],
    ),
    "inventory_value": SemanticMetric(
        metric_id="inventory_value",
        vietnamese_name="Giá trị tồn kho",
        formula="SUM(ps_availqty * ps_supplycost)",
        description="Tổng giá trị tồn kho của các mặt hàng tính theo chi phí cung ứng",
        required_tables=["partsupp"],
    ),
    "gross_profit": SemanticMetric(
        metric_id="gross_profit",
        vietnamese_name="Lợi nhuận gộp ước tính",
        formula="SUM(l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity)",
        description="Doanh thu thực tế trừ đi chi phí nhập kho của nhà cung cấp",
        required_tables=["lineitem", "partsupp"],
    ),
    "late_delivery_rate": SemanticMetric(
        metric_id="late_delivery_rate",
        vietnamese_name="Tỷ lệ trễ hạn giao hàng",
        formula="COUNT(CASE WHEN l_receiptdate > l_commitdate THEN 1 END) * 100.0 / COUNT(*)",
        description="Tỷ lệ phần trăm đơn hàng giao cho khách sau ngày cam kết",
        required_tables=["lineitem"],
    ),
}


# ==============================================================================
# 4. CÁC HÀM TIỆN ÍCH TRUY XUẤT VÀ RENDER SCHEMA CONTEXT
# ==============================================================================


def get_table_schema(table_name: str) -> str | None:
    """Lấy định nghĩa DDL kèm chú thích tiếng Việt cho một bảng cụ thể."""
    return TPCH_TABLE_SCHEMAS.get(table_name.lower())


def get_all_table_schemas() -> dict[str, str]:
    """Lấy từ điển DDL của toàn bộ 8 bảng TPC-H."""
    return dict(TPCH_TABLE_SCHEMAS)


def get_join_relationships() -> list[JoinRelationship]:
    """Lấy danh sách tất cả các quan hệ JOIN chuẩn trong TPC-H."""
    return list(TPCH_JOIN_RELATIONSHIPS)


def get_semantic_metrics() -> dict[str, SemanticMetric]:
    """Lấy từ điển tất cả các chỉ số nghiệp vụ chuẩn (Semantic Metrics)."""
    return dict(TPCH_SEMANTIC_METRICS)


def render_schema_context(selected_tables: list[str] | None = None) -> str:
    """Kết xuất ngữ cảnh lược đồ dữ liệu (Markdown) đưa vào prompt cho SQL Generator.

    Args:
        selected_tables: Danh sách bảng liên quan cần trích xuất (None = toàn bộ 8 bảng).

    Returns:
        Chuỗi Markdown chứa DDL, các điều kiện JOIN chuẩn và công thức tính toán.
    """
    tables_to_render = (
        [t.lower() for t in selected_tables if t.lower() in TPCH_TABLE_SCHEMAS]
        if selected_tables
        else TPCH_TABLE_NAMES
    )

    lines: list[str] = [
        "### NGỮ CẢNH LƯỢC ĐỒ CƠ SỞ DỮ LIỆU TPC-H (8 BẢNG):",
        "> QUY TẮC CỘT NGÀY TỰ NHIÊN: Lọc thời gian trực tiếp trên trường DATE (o_orderdate, l_shipdate, l_commitdate, l_receiptdate). Không cần join bảng thời gian trung gian.",
        "> QUY TẮC DOANH THU THUẦN: Doanh thu thuần = SUM(l_extendedprice * (1 - l_discount)).",
        "",
    ]

    # 1. DDL các bảng
    lines.append("#### 1. CẤU TRÚC CÁC BẢNG (DDL):")
    for tbl in tables_to_render:
        schema = TPCH_TABLE_SCHEMAS.get(tbl)
        if schema:
            lines.append(f"```sql\n{schema}\n```\n")

    # 2. Điều kiện JOIN chuẩn giữa các bảng được chọn
    table_set = set(tables_to_render)
    relevant_joins = [
        j
        for j in TPCH_JOIN_RELATIONSHIPS
        if j.from_table in table_set and j.to_table in table_set
    ]

    lines.append("#### 2. QUAN HỆ JOIN CHUẨN GIỮA CÁC BẢNG:")
    joins_to_show = relevant_joins if relevant_joins else [
        j for j in TPCH_JOIN_RELATIONSHIPS if j.from_table in table_set or j.to_table in table_set
    ]
    for j in joins_to_show:
        lines.append(
            f"- **{j.from_table} JOIN {j.to_table}**: `{j.condition}` ({j.description})"
        )
    lines.append("")

    # 3. Chỉ số nghiệp vụ chuẩn (dbt Semantic Metrics)
    lines.append("#### 3. CÔNG THỨC CHUẨN NGHIỆP VỤ CHUỖI CUNG ỨNG (dbt SEMANTIC METRICS):")
    for metric in TPCH_SEMANTIC_METRICS.values():
        lines.append(
            f"- **{metric.vietnamese_name}** (`{metric.metric_id}`): `{metric.formula}` — {metric.description}"
        )

    return "\n".join(lines)


__all__ = [
    "TPCH_JOIN_RELATIONSHIPS",
    "TPCH_SEMANTIC_METRICS",
    "TPCH_TABLE_COLUMNS",
    "TPCH_TABLE_NAMES",
    "TPCH_TABLE_SCHEMAS",
    "JoinRelationship",
    "SemanticMetric",
    "get_all_table_schemas",
    "get_join_relationships",
    "get_semantic_metrics",
    "get_table_schema",
    "render_schema_context",
]
