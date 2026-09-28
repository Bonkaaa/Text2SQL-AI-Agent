"""Tra cứu giá trị phân loại thực tế trong database (Entity / Value Linking).

Component 2.2:
- Cung cấp danh bạ chỉ mục các giá trị phân loại chính trong 24 bảng TPC-DS kèm từ đồng nghĩa tiếng Việt/tiếng Anh.
- Hàm find_matching_categorical_values: Ánh xạ câu hỏi người dùng về đúng tên cột và giá trị chuẩn trong kho dữ liệu.
- Hàm format_categorical_context: Đóng gói các giá trị tìm được thành context Markdown nạp vào prompt cho LLM.
"""

import re
from dataclasses import dataclass
from typing import Final

from rapidfuzz import fuzz


@dataclass(frozen=True)
class CategoricalEntry:
    """Định nghĩa một mục giá trị phân loại được lập chỉ mục."""

    table: str
    column: str
    value: str
    aliases: list[str]
    description: str


@dataclass(frozen=True)
class CategoricalMatch:
    """Kết quả ánh xạ giá trị phân loại từ câu hỏi người dùng."""

    table: str
    column: str
    matched_value: str
    query_keyword: str
    similarity_score: float
    exact_match: bool


# ==============================================================================
# 1. TỪ ĐIỂN CHỈ MỤC GIÁ TRỊ PHÂN LOẠI TPC-DS (CATEGORICAL VALUE REGISTRY)
# ==============================================================================

CATEGORICAL_REGISTRY: Final[list[CategoricalEntry]] = [
    # -------------------------------------------------------------------------
    # 1. item.i_category (10 Ngành hàng chuẩn trong TPC-DS)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Electronics",
        aliases=[
            "điện tử",
            "dien tu",
            "ngành hàng điện tử",
            "thiết bị điện tử",
            "công nghệ",
            "đồ điện tử",
            "máy móc điện tử",
            "electronics",
            "electronic",
        ],
        description="Ngành hàng điện tử, công nghệ, âm thanh và vi tính",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Home",
        aliases=[
            "nhà cửa",
            "nha cua",
            "đồ gia dụng",
            "do gia dung",
            "gia dụng",
            "gia dung",
            "đồ dùng gia đình",
            "nội thất nhà cửa",
            "thiết bị nhà",
            "home",
        ],
        description="Ngành hàng đồ gia dụng, thiết bị và tiện ích nhà cửa",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Women",
        aliases=[
            "thời trang nữ",
            "thoi trang nu",
            "đồ nữ",
            "do nu",
            "quần áo nữ",
            "quan ao nu",
            "nữ giới",
            "phái nữ",
            "phái đẹp",
            "women",
            "womens",
        ],
        description="Ngành hàng thời trang và trang phục nữ giới",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Men",
        aliases=[
            "thời trang nam",
            "thoi trang nam",
            "đồ nam",
            "do nam",
            "quần áo nam",
            "quan ao nam",
            "nam giới",
            "phái mạnh",
            "men",
            "mens",
        ],
        description="Ngành hàng thời trang và trang phục nam giới",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Children",
        aliases=[
            "trẻ em",
            "tre em",
            "đồ trẻ em",
            "do tre em",
            "thời trang trẻ em",
            "trẻ con",
            "quần áo trẻ con",
            "trẻ nhỏ",
            "children",
            "kids",
        ],
        description="Ngành hàng thời trang và đồ dùng cho trẻ em",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Books",
        aliases=[
            "sách",
            "sach",
            "sách báo",
            "sach bao",
            "ấn phẩm",
            "an pham",
            "sách giáo khoa",
            "tiểu thuyết",
            "tạp chí",
            "books",
            "book",
        ],
        description="Ngành hàng sách, ấn phẩm và tài liệu",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Shoes",
        aliases=[
            "giày dép",
            "giay dep",
            "giày",
            "giay",
            "dép",
            "dep",
            "sneakers",
            "boots",
            "giày thể thao",
            "shoes",
            "shoe",
        ],
        description="Ngành hàng giày dép các loại",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Jewelry",
        aliases=[
            "trang sức",
            "trang suc",
            "vàng bạc",
            "vang bac",
            "đá quý",
            "da quy",
            "kim hoàn",
            "phụ kiện trang sức",
            "jewelry",
            "jewellery",
        ],
        description="Ngành hàng vàng bạc, trang sức và phụ kiện cao cấp",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Sports",
        aliases=[
            "thể thao",
            "the thao",
            "dụng cụ thể thao",
            "đồ thể thao",
            "trang thiết bị thể thao",
            "sports",
            "sport",
        ],
        description="Ngành hàng dụng cụ, đồ tập và thiết bị thể thao",
    ),
    CategoricalEntry(
        table="item",
        column="i_category",
        value="Music",
        aliases=[
            "âm nhạc",
            "am nhac",
            "đĩa nhạc",
            "dia nhac",
            "nhạc cụ",
            "băng đĩa",
            "cd nhạc",
            "music",
        ],
        description="Ngành hàng sản phẩm âm nhạc, đĩa CD và nhạc cụ",
    ),
    # -------------------------------------------------------------------------
    # 2. customer_demographics.cd_gender (Giới tính khách hàng)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="customer_demographics",
        column="cd_gender",
        value="M",
        aliases=[
            "khách hàng nam",
            "khach hang nam",
            "nam giới",
            "nam gioi",
            "đàn ông",
            "dan ong",
            "phái nam",
            "phái mạnh",
            "male",
        ],
        description="Giới tính Nam",
    ),
    CategoricalEntry(
        table="customer_demographics",
        column="cd_gender",
        value="F",
        aliases=[
            "khách hàng nữ",
            "khach hang nu",
            "nữ giới",
            "nu gioi",
            "phụ nữ",
            "phu nu",
            "phái nữ",
            "phái đẹp",
            "female",
        ],
        description="Giới tính Nữ",
    ),
    # -------------------------------------------------------------------------
    # 3. customer_demographics.cd_marital_status (Tình trạng hôn nhân)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="customer_demographics",
        column="cd_marital_status",
        value="S",
        aliases=[
            "độc thân",
            "doc than",
            "chưa kết hôn",
            "chua ket hon",
            "chưa có gia đình",
            "chua co gia dinh",
            "single",
        ],
        description="Tình trạng hôn nhân: Độc thân",
    ),
    CategoricalEntry(
        table="customer_demographics",
        column="cd_marital_status",
        value="M",
        aliases=[
            "đã kết hôn",
            "da ket hon",
            "có gia đình",
            "co gia dinh",
            "lập gia đình",
            "da lap gia dinh",
            "married",
        ],
        description="Tình trạng hôn nhân: Đã kết hôn",
    ),
    CategoricalEntry(
        table="customer_demographics",
        column="cd_marital_status",
        value="D",
        aliases=[
            "ly hôn",
            "ly hon",
            "ly dị",
            "ly di",
            "đã ly dị",
            "divorced",
        ],
        description="Tình trạng hôn nhân: Đã ly hôn",
    ),
    CategoricalEntry(
        table="customer_demographics",
        column="cd_marital_status",
        value="W",
        aliases=[
            "góa",
            "goa",
            "góa bụa",
            "goa bua",
            "widowed",
        ],
        description="Tình trạng hôn nhân: Góa",
    ),
    # -------------------------------------------------------------------------
    # 4. ship_mode.sm_type (Phương thức vận chuyển TPC-DS)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="ship_mode",
        column="sm_type",
        value="EXPRESS",
        aliases=[
            "hỏa tốc",
            "hoa toc",
            "chuyển phát nhanh",
            "chuyen phat nhanh",
            "giao nhanh",
            "express",
        ],
        description="Vận chuyển giao hàng hỏa tốc / express",
    ),
    CategoricalEntry(
        table="ship_mode",
        column="sm_type",
        value="NEXT DAY",
        aliases=[
            "giao ngày hôm sau",
            "giao ngay hom sau",
            "hôm sau",
            "qua ngày",
            "next day",
        ],
        description="Vận chuyển giao hàng trong ngày kế tiếp",
    ),
    CategoricalEntry(
        table="ship_mode",
        column="sm_type",
        value="OVERNIGHT",
        aliases=[
            "giao qua đêm",
            "qua đêm",
            "qua dem",
            "overnight",
        ],
        description="Vận chuyển giao hàng qua đêm",
    ),
    CategoricalEntry(
        table="ship_mode",
        column="sm_type",
        value="TWO DAY",
        aliases=[
            "giao trong 2 ngày",
            "hai ngày",
            "2 ngày",
            "two day",
        ],
        description="Vận chuyển giao hàng trong vòng 2 ngày",
    ),
    CategoricalEntry(
        table="ship_mode",
        column="sm_type",
        value="REGULAR",
        aliases=[
            "tiêu chuẩn",
            "tieu chuan",
            "thông thường",
            "thong thuong",
            "giao thông thường",
            "regular",
        ],
        description="Vận chuyển tiêu chuẩn thông thường",
    ),
    CategoricalEntry(
        table="ship_mode",
        column="sm_type",
        value="LIBRARY",
        aliases=[
            "thư viện",
            "thu vien",
            "bưu phẩm thư viện",
            "library",
        ],
        description="Hình thức gửi bưu phẩm ấn phẩm / thư viện",
    ),
    # -------------------------------------------------------------------------
    # 5. customer_address.ca_state (Các tiểu bang Hoa Kỳ phổ biến)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="CA",
        aliases=[
            "california",
            "tiểu bang california",
            "bang california",
            "bang ca",
        ],
        description="Tiểu bang California, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="TX",
        aliases=[
            "texas",
            "tiểu bang texas",
            "bang texas",
            "bang tx",
        ],
        description="Tiểu bang Texas, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="NY",
        aliases=[
            "new york",
            "tiểu bang new york",
            "bang new york",
            "bang ny",
        ],
        description="Tiểu bang New York, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="FL",
        aliases=[
            "florida",
            "tiểu bang florida",
            "bang florida",
            "bang fl",
        ],
        description="Tiểu bang Florida, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="IL",
        aliases=[
            "illinois",
            "tiểu bang illinois",
            "bang illinois",
            "bang il",
        ],
        description="Tiểu bang Illinois, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="CO",
        aliases=[
            "colorado",
            "tiểu bang colorado",
            "bang colorado",
            "bang co",
        ],
        description="Tiểu bang Colorado, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="GA",
        aliases=[
            "georgia",
            "tiểu bang georgia",
            "bang georgia",
            "bang ga",
        ],
        description="Tiểu bang Georgia, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="TN",
        aliases=[
            "tennessee",
            "tiểu bang tennessee",
            "bang tennessee",
            "bang tn",
        ],
        description="Tiểu bang Tennessee, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="KY",
        aliases=[
            "kentucky",
            "tiểu bang kentucky",
            "bang kentucky",
            "bang ky",
        ],
        description="Tiểu bang Kentucky, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="PA",
        aliases=[
            "pennsylvania",
            "tiểu bang pennsylvania",
            "bang pennsylvania",
            "bang pa",
        ],
        description="Tiểu bang Pennsylvania, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="OH",
        aliases=[
            "ohio",
            "tiểu bang ohio",
            "bang ohio",
            "bang oh",
        ],
        description="Tiểu bang Ohio, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="NC",
        aliases=[
            "north carolina",
            "bắc carolina",
            "tiểu bang bắc carolina",
            "bang nc",
        ],
        description="Tiểu bang North Carolina, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="VA",
        aliases=[
            "virginia",
            "tiểu bang virginia",
            "bang virginia",
            "bang va",
        ],
        description="Tiểu bang Virginia, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="WA",
        aliases=[
            "washington",
            "tiểu bang washington",
            "bang washington",
            "bang wa",
        ],
        description="Tiểu bang Washington, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_state",
        value="MI",
        aliases=[
            "michigan",
            "tiểu bang michigan",
            "bang michigan",
            "bang mi",
        ],
        description="Tiểu bang Michigan, Hoa Kỳ",
    ),
    CategoricalEntry(
        table="customer_address",
        column="ca_country",
        value="United States",
        aliases=[
            "hoa kỳ",
            "hoa ky",
            "nước mỹ",
            "nuoc my",
            "united states",
            "usa",
            "us",
        ],
        description="Quốc gia Hoa Kỳ",
    ),
    # -------------------------------------------------------------------------
    # 6. customer.c_preferred_cust_flag (Cờ khách hàng VIP / thân thiết)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="customer",
        column="c_preferred_cust_flag",
        value="Y",
        aliases=[
            "khách hàng thân thiết",
            "khach hang than thiet",
            "khách vip",
            "khach vip",
            "ưu tiên",
            "preferred customer",
            "vip",
        ],
        description="Khách hàng thân thiết VIP",
    ),
    CategoricalEntry(
        table="customer",
        column="c_preferred_cust_flag",
        value="N",
        aliases=[
            "khách vãng lai",
            "khach vang lai",
            "khách thông thường",
            "non-preferred",
        ],
        description="Khách hàng thông thường / vãng lai",
    ),
]


# ==============================================================================
# 2. CÁC HÀM TÌM KIẾM VÀ ÁNH XẠ (ENTITY / VALUE LINKING)
# ==============================================================================


def get_all_categorical_entries() -> list[CategoricalEntry]:
    """Lấy danh sách tất cả các mục giá trị phân loại đã được lập chỉ mục."""
    return list(CATEGORICAL_REGISTRY)


def _normalize_text(text: str) -> str:
    """Chuẩn hóa văn bản tiếng Việt/Anh để phục vụ so khớp."""
    text = text.lower().strip()
    # Thay thế dấu câu thừa bằng khoảng trắng
    text = re.sub(r"[?,.:;!\"'()\[\]{}]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def find_matching_categorical_values(
    query: str,
    top_k: int = 5,
    min_score: float = 65.0,
) -> list[CategoricalMatch]:
    """Tìm kiếm và ánh xạ các giá trị phân loại có trong câu hỏi của người dùng.

    Thuật toán kết hợp:
    1. Exact keyword / alias substring search (ưu tiên điểm 100).
    2. Fuzzy matching (rapidfuzz token_set_ratio) cho từ khóa gõ sai hoặc biến thể.

    Args:
        query: Câu hỏi ngôn ngữ tự nhiên của người dùng.
        top_k: Số lượng kết quả phân loại tối đa cần trả về.
        min_score: Ngưỡng điểm tương đồng tối thiểu (0-100).

    Returns:
        Danh sách các đối tượng CategoricalMatch đã sắp xếp theo độ tương đồng giảm dần.
    """
    if not query or not query.strip():
        return []

    norm_query = _normalize_text(query)
    matches_map: dict[tuple[str, str, str], CategoricalMatch] = {}

    # Bước 1: Exact Substring Matching theo từng Alias
    for entry in CATEGORICAL_REGISTRY:
        matched_alias: str | None = None
        for alias in entry.aliases:
            norm_alias = _normalize_text(alias)
            # Kiểm tra cụm từ alias xuất hiện nguyên vẹn trong query
            pattern = rf"(?:\b|^){re.escape(norm_alias)}(?:\b|$)"
            if re.search(pattern, norm_query):
                matched_alias = alias
                break

        if matched_alias:
            key = (entry.table, entry.column, entry.value)
            matches_map[key] = CategoricalMatch(
                table=entry.table,
                column=entry.column,
                matched_value=entry.value,
                query_keyword=matched_alias,
                similarity_score=100.0,
                exact_match=True,
            )

    # Bước 2: Fuzzy Matching cho các trường hợp còn lại (nếu chưa match exact)
    for entry in CATEGORICAL_REGISTRY:
        key = (entry.table, entry.column, entry.value)
        if key in matches_map:
            continue

        # Nếu cột này đã có exact match thì không fuzzy match thêm giá trị khác cho cùng cột
        col_key = (entry.table, entry.column)
        if any(
            m.exact_match for (t, c, _), m in matches_map.items() if (t, c) == col_key
        ):
            continue

        best_score = 0.0
        best_alias = ""
        for alias in entry.aliases:
            norm_alias = _normalize_text(alias)
            # Tránh false positive với các alias quá ngắn (< 4 ký tự)
            if len(norm_alias) < 4:
                continue

            score = fuzz.token_set_ratio(norm_alias, norm_query)
            if score > best_score:
                best_score = score
                best_alias = alias

        if best_score >= min_score:
            matches_map[key] = CategoricalMatch(
                table=entry.table,
                column=entry.column,
                matched_value=entry.value,
                query_keyword=best_alias,
                similarity_score=float(best_score),
                exact_match=False,
            )

    # Sắp xếp theo score giảm dần
    sorted_matches = sorted(
        matches_map.values(),
        key=lambda m: (m.exact_match, m.similarity_score),
        reverse=True,
    )

    return sorted_matches[:top_k]


def format_categorical_context(matches: list[CategoricalMatch]) -> str:
    """Đóng gói danh sách kết quả tra cứu thành chuỗi Markdown đưa vào prompt.

    Args:
        matches: Danh sách các giá trị phân loại đã khớp.

    Returns:
        Chuỗi Markdown hướng dẫn LLM sử dụng đúng giá trị trong mệnh đề WHERE.
    """
    if not matches:
        return ""

    lines = [
        "### GIÁ TRỊ PHÂN LOẠI THỰC TẾ TRONG DATABASE (CATEGORICAL VALUE LINKING):",
        "Khi sinh câu lệnh SQL, bắt buộc dùng đúng các giá trị chuẩn sau trong mệnh đề WHERE:",
    ]
    for m in matches:
        match_type = (
            "khớp chính xác"
            if m.exact_match
            else f"độ tương đồng {m.similarity_score:.0f}%"
        )
        lines.append(
            f"- Cột **{m.table}.{m.column}**: Dùng điều kiện `{m.column} = '{m.matched_value}'` "
            f'(ánh xạ từ từ khóa: *"{m.query_keyword}"*, {match_type})'
        )

    return "\n".join(lines)


__all__ = [
    "CATEGORICAL_REGISTRY",
    "CategoricalEntry",
    "CategoricalMatch",
    "find_matching_categorical_values",
    "format_categorical_context",
    "get_all_categorical_entries",
]
