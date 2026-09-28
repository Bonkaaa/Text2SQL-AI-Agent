"""Unit tests cho Component 2.2: Categorical Value Search (Entity / Value Linking) trên TPC-DS.

Kiểm tra:
- Khả năng ánh xạ từ khóa tiếng Việt / tiếng Anh về đúng giá trị phân loại trong TPC-DS.
- Khớp ngành hàng sản phẩm (item.i_category: Electronics, Home, Women, Men, Sports, Books...).
- Khớp nhân khẩu học (cd_gender: M/F, cd_marital_status: S/M/D/W).
- Khớp hình thức giao vận (sm_type: EXPRESS, NEXT DAY, OVERNIGHT...).
- Khớp tiểu bang địa chỉ (ca_state: CA, TX, NY, FL...).
- Định dạng context đầu ra để nạp vào prompt cho Schema Retriever / SQL Generator.
"""

from src.utils.categorical_search import (
    CategoricalMatch,
    find_matching_categorical_values,
    format_categorical_context,
    get_all_categorical_entries,
)


def test_get_all_categorical_entries():
    """Kiểm tra kho từ điển giá trị phân loại có đầy đủ các cột TPC-DS cốt lõi."""
    entries = get_all_categorical_entries()
    assert len(entries) > 0

    columns_indexed = {e.column for e in entries}
    assert "i_category" in columns_indexed
    assert "cd_gender" in columns_indexed
    assert "cd_marital_status" in columns_indexed
    assert "sm_type" in columns_indexed
    assert "ca_state" in columns_indexed


def test_match_item_categories_vietnamese():
    """Kiểm tra khớp ngành hàng sản phẩm với từ khóa tiếng Việt."""
    # 1. "ngành hàng điện tử" -> i_category = 'Electronics'
    matches_elec = find_matching_categorical_values(
        "Thống kê doanh số ngành hàng điện tử"
    )
    assert len(matches_elec) > 0
    top_elec = matches_elec[0]
    assert isinstance(top_elec, CategoricalMatch)
    assert top_elec.column == "i_category"
    assert top_elec.matched_value == "Electronics"

    # 2. "thời trang nữ" -> i_category = 'Women'
    matches_women = find_matching_categorical_values("Báo cáo bán hàng thời trang nữ")
    assert any(
        m.column == "i_category" and m.matched_value == "Women" for m in matches_women
    )

    # 3. "đồ gia dụng" -> i_category = 'Home'
    matches_home = find_matching_categorical_values(
        "Sản phẩm đồ gia dụng bán chạy nhất"
    )
    assert any(
        m.column == "i_category" and m.matched_value == "Home" for m in matches_home
    )

    # 4. "dụng cụ thể thao" -> i_category = 'Sports'
    matches_sports = find_matching_categorical_values("Doanh thu từ dụng cụ thể thao")
    assert any(
        m.column == "i_category" and m.matched_value == "Sports" for m in matches_sports
    )


def test_match_demographics():
    """Kiểm tra khớp nhân khẩu học giới tính và tình trạng hôn nhân."""
    # 1. "nam giới" -> cd_gender = 'M'
    matches_male = find_matching_categorical_values(
        "Khách hàng nam giới chi tiêu bao nhiêu"
    )
    assert any(m.column == "cd_gender" and m.matched_value == "M" for m in matches_male)

    # 2. "phụ nữ" -> cd_gender = 'F'
    matches_female = find_matching_categorical_values(
        "Số lượng người mua phụ nữ tại cửa hàng"
    )
    assert any(
        m.column == "cd_gender" and m.matched_value == "F" for m in matches_female
    )

    # 3. "độc thân" -> cd_marital_status = 'S'
    matches_single = find_matching_categorical_values("Phân khúc khách hàng độc thân")
    assert any(
        m.column == "cd_marital_status" and m.matched_value == "S"
        for m in matches_single
    )

    # 4. "đã kết hôn" -> cd_marital_status = 'M'
    matches_married = find_matching_categorical_values(
        "Khách hàng đã kết hôn mua gì nhiều"
    )
    assert any(
        m.column == "cd_marital_status" and m.matched_value == "M"
        for m in matches_married
    )


def test_match_shipmode_and_states():
    """Kiểm tra khớp phương thức vận chuyển và tiểu bang địa chỉ."""
    # 1. "giao hàng hỏa tốc" -> sm_type = 'EXPRESS'
    matches_express = find_matching_categorical_values("Đơn hàng giao hàng hỏa tốc")
    assert any(
        m.column == "sm_type" and m.matched_value == "EXPRESS" for m in matches_express
    )

    # 2. "giao qua đêm" -> sm_type = 'OVERNIGHT'
    matches_overnight = find_matching_categorical_values(
        "Chi phí vận chuyển giao qua đêm"
    )
    assert any(
        m.column == "sm_type" and m.matched_value == "OVERNIGHT"
        for m in matches_overnight
    )

    # 3. "bang california" -> ca_state = 'CA'
    matches_ca = find_matching_categorical_values("Khách hàng ở bang california")
    assert any(m.column == "ca_state" and m.matched_value == "CA" for m in matches_ca)

    # 4. "tiểu bang texas" -> ca_state = 'TX'
    matches_tx = find_matching_categorical_values("Doanh số tại tiểu bang texas")
    assert any(m.column == "ca_state" and m.matched_value == "TX" for m in matches_tx)


def test_no_false_positive_on_generic_text():
    """Kiểm tra câu hỏi không chứa thực thể phân loại thì không bị hallucinate kết quả sai lệch."""
    matches = find_matching_categorical_values(
        "Tính tổng số lượng hóa đơn phát sinh trong ngày hôm nay"
    )
    for m in matches:
        assert m.similarity_score >= 60.0


def test_format_categorical_context():
    """Kiểm tra format kết quả matching thành Markdown context cho prompt."""
    matches = [
        CategoricalMatch(
            table="item",
            column="i_category",
            matched_value="Electronics",
            query_keyword="điện tử",
            similarity_score=100.0,
            exact_match=True,
        ),
        CategoricalMatch(
            table="customer_address",
            column="ca_state",
            matched_value="CA",
            query_keyword="california",
            similarity_score=100.0,
            exact_match=True,
        ),
    ]

    formatted_str = format_categorical_context(matches)
    assert isinstance(formatted_str, str)
    assert "GIÁ TRỊ PHÂN LOẠI" in formatted_str
    assert "i_category = 'Electronics'" in formatted_str
    assert "ca_state = 'CA'" in formatted_str
    assert "điện tử" in formatted_str


def test_format_empty_categorical_context():
    """Kiểm tra format khi không tìm thấy match nào."""
    formatted_str = format_categorical_context([])
    assert formatted_str == ""
