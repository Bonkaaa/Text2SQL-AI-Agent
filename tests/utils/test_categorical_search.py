"""Unit tests cho Component 2.2: Categorical Value Search trên TPC-H (8 bảng).

Kiểm tra:
- Khả năng ánh xạ từ khóa tiếng Việt / tiếng Anh về đúng giá trị phân loại trong TPC-H.
- Khớp phân khúc thị trường (customer.c_mktsegment: AUTOMOBILE, BUILDING, FURNITURE, HOUSEHOLD, MACHINERY).
- Khớp phương thức giao vận (lineitem.l_shipmode: AIR, SHIP, TRUCK, RAIL, MAIL, FOB, REG AIR).
- Khớp trạng thái đơn hàng (orders.o_orderstatus: O, F, P) và mức độ ưu tiên (orders.o_orderpriority).
- Khớp khu vực địa lý (region.r_name: ASIA, EUROPE, AFRICA, AMERICA, MIDDLE EAST).
- Khớp quốc gia (nation.n_name: VIETNAM, JAPAN, CHINA, UNITED STATES, GERMANY...).
- Khớp cờ hoàn trả (lineitem.l_returnflag: R, A, N).
- Định dạng context đầu ra để nạp vào prompt cho Schema Retriever / SQL Generator.
"""

from src.utils.categorical_search import (
    CategoricalMatch,
    find_matching_categorical_values,
    format_categorical_context,
    get_all_categorical_entries,
)
from src.utils.table_keywords import TABLE_KEYWORD_MAP, get_table_keywords


def test_get_all_categorical_entries():
    """Kiểm tra kho từ điển giá trị phân loại có đầy đủ các cột TPC-H cốt lõi."""
    entries = get_all_categorical_entries()
    assert len(entries) > 0

    columns_indexed = {e.column for e in entries}
    assert "c_mktsegment" in columns_indexed
    assert "l_shipmode" in columns_indexed
    assert "o_orderstatus" in columns_indexed
    assert "o_orderpriority" in columns_indexed
    assert "r_name" in columns_indexed
    assert "n_name" in columns_indexed
    assert "l_returnflag" in columns_indexed


def test_match_mktsegment_vietnamese():
    """Kiểm tra khớp phân khúc thị trường khách hàng với từ khóa tiếng Việt."""
    # 1. "ngành ô tô" -> c_mktsegment = 'AUTOMOBILE'
    matches_auto = find_matching_categorical_values(
        "Khách hàng thuộc phân khúc ngành ô tô"
    )
    assert len(matches_auto) > 0
    top_auto = matches_auto[0]
    assert isinstance(top_auto, CategoricalMatch)
    assert top_auto.column == "c_mktsegment"
    assert top_auto.matched_value == "AUTOMOBILE"

    # 2. "xây dựng" -> c_mktsegment = 'BUILDING'
    matches_build = find_matching_categorical_values("Doanh thu từ phân khúc xây dựng")
    assert any(
        m.column == "c_mktsegment" and m.matched_value == "BUILDING"
        for m in matches_build
    )

    # 3. "nội thất" -> c_mktsegment = 'FURNITURE'
    matches_furn = find_matching_categorical_values("Đơn hàng của khách ngành nội thất")
    assert any(
        m.column == "c_mktsegment" and m.matched_value == "FURNITURE"
        for m in matches_furn
    )


def test_match_shipmode_and_returns():
    """Kiểm tra khớp phương thức giao hàng và cờ hoàn trả."""
    # 1. "đường hàng không" -> l_shipmode = 'AIR'
    matches_air = find_matching_categorical_values(
        "Các mặt hàng vận chuyển đường hàng không"
    )
    assert any(
        m.column == "l_shipmode" and m.matched_value == "AIR" for m in matches_air
    )

    # 2. "tàu biển" / "đường biển" -> l_shipmode = 'SHIP'
    matches_ship = find_matching_categorical_values("Đơn hàng vận chuyển bằng tàu biển")
    assert any(
        m.column == "l_shipmode" and m.matched_value == "SHIP" for m in matches_ship
    )

    # 3. "hoàn trả" -> l_returnflag = 'R'
    matches_ret = find_matching_categorical_values("Tỷ lệ các mặt hàng bị hoàn trả")
    assert any(
        m.column == "l_returnflag" and m.matched_value == "R" for m in matches_ret
    )


def test_match_geography():
    """Kiểm tra khớp khu vực kinh tế (region) và quốc gia (nation)."""
    # 1. "châu á" -> r_name = 'ASIA'
    matches_asia = find_matching_categorical_values("Top 5 khách hàng khu vực Châu Á")
    assert any(m.column == "r_name" and m.matched_value == "ASIA" for m in matches_asia)

    # 2. "châu âu" -> r_name = 'EUROPE'
    matches_eu = find_matching_categorical_values("Doanh số các nhà cung cấp ở Châu Âu")
    assert any(m.column == "r_name" and m.matched_value == "EUROPE" for m in matches_eu)

    # 3. "nhật bản" -> n_name = 'JAPAN'
    matches_jp = find_matching_categorical_values("Khách hàng tại quốc gia Nhật Bản")
    assert any(m.column == "n_name" and m.matched_value == "JAPAN" for m in matches_jp)


def test_no_false_positive_on_generic_text():
    """Kiểm tra câu hỏi chung không ánh xạ nhầm giá trị phân loại."""
    matches = find_matching_categorical_values(
        "Cho tôi xem danh sách 10 khách hàng đầu tiên"
    )
    assert len(matches) == 0


def test_format_categorical_context():
    """Kiểm tra hàm format_categorical_context tạo Markdown chính xác."""
    sample_matches = [
        CategoricalMatch(
            table="customer",
            column="c_mktsegment",
            matched_value="AUTOMOBILE",
            query_keyword="ngành ô tô",
            similarity_score=100.0,
            exact_match=True,
        )
    ]
    context = format_categorical_context(sample_matches)
    assert "c_mktsegment" in context
    assert "AUTOMOBILE" in context
    assert "ngành ô tô" in context


def test_format_empty_categorical_context():
    """Kiểm tra danh sách rỗng trả về chuỗi rỗng."""
    assert format_categorical_context([]) == ""


def test_tpch_table_keywords_mapping():
    """Kiểm tra từ điển từ khóa tiếng Việt của đúng 8 bảng TPC-H."""
    keywords = get_table_keywords()
    assert len(keywords) == 8
    assert "customer" in keywords
    assert "khách hàng" in keywords["customer"]
    assert "orders" in keywords
    assert "đơn hàng" in keywords["orders"]
    assert "lineitem" in keywords
    assert "mặt hàng" in keywords["lineitem"] or "chi tiết" in keywords["lineitem"]
    assert "supplier" in keywords
    assert "nhà cung cấp" in keywords["supplier"]
    assert "part" in keywords
    assert "linh kiện" in keywords["part"]
    assert "partsupp" in keywords
    assert "tồn kho" in keywords["partsupp"] or "cung ứng" in keywords["partsupp"]
    assert "nation" in keywords
    assert "quốc gia" in keywords["nation"]
    assert "region" in keywords
    assert "khu vực" in keywords["region"] or "châu lục" in keywords["region"]
    assert TABLE_KEYWORD_MAP == keywords
