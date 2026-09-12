"""Unit tests cho Component 2.2: Categorical Value Search (Entity / Value Linking).

Kiểm tra:
- Khả năng ánh xạ từ khóa tiếng Việt / tiếng Anh về đúng giá trị phân loại trong TPC-H.
- Khớp phân khúc thị trường (c_mktsegment: AUTOMOBILE, MACHINERY, BUILDING...).
- Khớp khu vực địa lý (r_name: ASIA, EUROPE, AMERICA...).
- Khớp quốc gia (n_name: VIETNAM, JAPAN, CHINA, UNITED STATES...).
- Khớp trạng thái đơn hàng và phương thức giao vận (o_orderstatus, l_shipmode).
- Định dạng context đầu ra để nạp vào prompt cho Schema Retriever / SQL Generator.
"""

from src.utils.categorical_search import (
    CategoricalMatch,
    find_matching_categorical_values,
    format_categorical_context,
    get_all_categorical_entries,
)


def test_get_all_categorical_entries():
    """Kiểm tra kho từ điển giá trị phân loại có đầy đủ các cột TPC-H cốt lõi."""
    entries = get_all_categorical_entries()
    assert len(entries) > 0

    columns_indexed = {e.column for e in entries}
    assert "c_mktsegment" in columns_indexed
    assert "r_name" in columns_indexed
    assert "n_name" in columns_indexed
    assert "o_orderstatus" in columns_indexed
    assert "l_shipmode" in columns_indexed


def test_match_market_segment_vietnamese():
    """Kiểm tra khớp phân khúc thị trường với từ khóa tiếng Việt."""
    # 1. "ngành ô tô" -> c_mktsegment = 'AUTOMOBILE'
    matches = find_matching_categorical_values("Thống kê khách hàng thuộc ngành ô tô")
    assert len(matches) > 0
    top = matches[0]
    assert isinstance(top, CategoricalMatch)
    assert top.column == "c_mktsegment"
    assert top.matched_value == "AUTOMOBILE"

    # 2. "máy móc" -> c_mktsegment = 'MACHINERY'
    matches_machinery = find_matching_categorical_values(
        "Doanh thu từ các công ty máy móc"
    )
    assert any(
        m.column == "c_mktsegment" and m.matched_value == "MACHINERY"
        for m in matches_machinery
    )

    # 3. "xây dựng" -> c_mktsegment = 'BUILDING'
    matches_building = find_matching_categorical_values("Khách hàng mảng xây dựng")
    assert any(
        m.column == "c_mktsegment" and m.matched_value == "BUILDING"
        for m in matches_building
    )


def test_match_region_and_nation():
    """Kiểm tra khớp khu vực địa lý và quốc gia."""
    # 1. "châu á" -> r_name = 'ASIA'
    matches_asia = find_matching_categorical_values(
        "Báo cáo thị trường châu á năm 1995"
    )
    assert any(m.column == "r_name" and m.matched_value == "ASIA" for m in matches_asia)

    # 2. "châu âu" -> r_name = 'EUROPE'
    matches_europe = find_matching_categorical_values("Doanh số tại châu âu")
    assert any(
        m.column == "r_name" and m.matched_value == "EUROPE" for m in matches_europe
    )

    # 3. "việt nam" -> n_name = 'VIETNAM'
    matches_vn = find_matching_categorical_values(
        "Khách hàng ở Việt Nam đã mua những gì"
    )
    assert any(
        m.column == "n_name" and m.matched_value == "VIETNAM" for m in matches_vn
    )

    # 4. "nhật bản" -> n_name = 'JAPAN'
    matches_japan = find_matching_categorical_values("Các nhà cung cấp đến từ Nhật Bản")
    assert any(
        m.column == "n_name" and m.matched_value == "JAPAN" for m in matches_japan
    )


def test_match_order_status_and_shipmode():
    """Kiểm tra khớp trạng thái đơn hàng và phương thức vận chuyển."""
    # 1. "vận chuyển bằng máy bay" -> l_shipmode = 'AIR'
    matches_air = find_matching_categorical_values(
        "Đơn hàng vận chuyển bằng đường hàng không"
    )
    assert any(
        m.column == "l_shipmode" and m.matched_value == "AIR" for m in matches_air
    )

    # 2. "đường tàu thủy" / "đường biển" -> l_shipmode = 'SHIP'
    matches_ship = find_matching_categorical_values("Giao hàng bằng đường biển")
    assert any(
        m.column == "l_shipmode" and m.matched_value == "SHIP" for m in matches_ship
    )

    # 3. "đơn hàng hoàn tất" -> o_orderstatus = 'F'
    matches_status = find_matching_categorical_values("Danh sách đơn hàng đã hoàn tất")
    assert any(
        m.column == "o_orderstatus" and m.matched_value == "F" for m in matches_status
    )


def test_no_false_positive_on_generic_text():
    """Kiểm tra câu hỏi không chứa thực thể phân loại thì không bị hallucinate kết quả sai lệch."""
    matches = find_matching_categorical_values(
        "Tính tổng số lượng đơn hàng trong ngày hôm nay"
    )
    # Các match nếu có phải có điểm tương đồng thấp hoặc không có match rác
    for m in matches:
        assert m.similarity_score >= 60.0


def test_format_categorical_context():
    """Kiểm tra format kết quả matching thành Markdown context cho prompt."""
    matches = [
        CategoricalMatch(
            table="customer",
            column="c_mktsegment",
            matched_value="AUTOMOBILE",
            query_keyword="ô tô",
            similarity_score=100.0,
            exact_match=True,
        ),
        CategoricalMatch(
            table="region",
            column="r_name",
            matched_value="ASIA",
            query_keyword="châu á",
            similarity_score=100.0,
            exact_match=True,
        ),
    ]

    formatted_str = format_categorical_context(matches)
    assert isinstance(formatted_str, str)
    assert "GIÁ TRỊ PHÂN LOẠI" in formatted_str
    assert "c_mktsegment = 'AUTOMOBILE'" in formatted_str
    assert "r_name = 'ASIA'" in formatted_str
    assert "ô tô" in formatted_str


def test_format_empty_categorical_context():
    """Kiểm tra format khi không tìm thấy match nào."""
    formatted_str = format_categorical_context([])
    assert formatted_str == ""
