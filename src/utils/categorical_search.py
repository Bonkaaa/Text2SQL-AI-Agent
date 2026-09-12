"""Tra cứu giá trị phân loại thực tế trong database (Entity / Value Linking).

Component 2.2:
- Cung cấp danh bạ chỉ mục các giá trị phân loại chính trong 8 bảng TPC-H kèm từ đồng nghĩa tiếng Việt/tiếng Anh.
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
# 1. TỪ ĐIỂN CHỈ MỤC GIÁ TRỊ PHÂN LOẠI TPC-H (CATEGORICAL VALUE REGISTRY)
# ==============================================================================

CATEGORICAL_REGISTRY: Final[list[CategoricalEntry]] = [
    # -------------------------------------------------------------------------
    # customer.c_mktsegment (Phân khúc thị trường khách hàng)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="AUTOMOBILE",
        aliases=[
            "ô tô",
            "o to",
            "xe hơi",
            "xe hoi",
            "ngành ô tô",
            "nganh o to",
            "công nghiệp ô tô",
            "phương tiện giao thông",
            "automobile",
            "car",
        ],
        description="Ngành công nghiệp sản xuất và phân phối ô tô, xe hơi",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="BUILDING",
        aliases=[
            "xây dựng",
            "xay dung",
            "ngành xây dựng",
            "nganh xay dung",
            "công trình",
            "cong trinh",
            "vật liệu xây dựng",
            "nhà ở",
            "building",
            "construction",
        ],
        description="Ngành xây dựng, công trình và kiến trúc",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="FURNITURE",
        aliases=[
            "nội thất",
            "noi that",
            "ngành nội thất",
            "đồ gỗ",
            "do go",
            "bàn ghế",
            "đồ dùng trong nhà",
            "furniture",
        ],
        description="Ngành sản xuất và buôn bán đồ gỗ, bàn ghế nội thất",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="HOUSEHOLD",
        aliases=[
            "đồ gia dụng",
            "do gia dung",
            "gia dụng",
            "gia dung",
            "hộ gia đình",
            "thiết bị gia đình",
            "household",
        ],
        description="Thiết bị và đồ dùng tiêu dùng cho hộ gia đình",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="MACHINERY",
        aliases=[
            "máy móc",
            "may moc",
            "ngành máy móc",
            "cơ khí",
            "co khi",
            "chế tạo máy",
            "thiết bị máy móc",
            "công nghiệp cơ khí",
            "machinery",
            "machine",
        ],
        description="Ngành cơ khí, thiết bị máy móc công nghiệp",
    ),
    # -------------------------------------------------------------------------
    # region.r_name (Khu vực địa lý thế giới)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="region",
        column="r_name",
        value="AFRICA",
        aliases=["châu phi", "chau phi", "châu lục phi", "africa"],
        description="Khu vực địa lý Châu Phi",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="AMERICA",
        aliases=["châu mỹ", "chau my", "bắc mỹ", "nam mỹ", "châu lục mỹ", "america"],
        description="Khu vực địa lý Châu Mỹ",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="ASIA",
        aliases=["châu á", "chau a", "á châu", "khu vực châu á", "asia"],
        description="Khu vực địa lý Châu Á",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="EUROPE",
        aliases=["châu âu", "chau au", "âu châu", "khu vực châu âu", "europe"],
        description="Khu vực địa lý Châu Âu",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="MIDDLE EAST",
        aliases=["trung đông", "trung dong", "khu vực trung đông", "middle east"],
        description="Khu vực địa lý Trung Đông",
    ),
    # -------------------------------------------------------------------------
    # nation.n_name (25 Quốc gia chuẩn TPC-H)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="VIETNAM",
        aliases=["việt nam", "viet nam", "vn", "vietnam"],
        description="Quốc gia Việt Nam",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="JAPAN",
        aliases=["nhật bản", "nhat ban", "nhật", "nhat", "japan"],
        description="Quốc gia Nhật Bản",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="CHINA",
        aliases=["trung quốc", "trung quoc", "trung hoa", "china"],
        description="Quốc gia Trung Quốc",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="UNITED STATES",
        aliases=[
            "hoa kỳ",
            "hoa ky",
            "mỹ",
            "my",
            "nước mỹ",
            "nuoc my",
            "united states",
            "usa",
            "us",
        ],
        description="Hợp chủng quốc Hoa Kỳ",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="GERMANY",
        aliases=["đức", "duc", "nước đức", "nuoc duc", "germany"],
        description="Cộng hòa Liên bang Đức",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="FRANCE",
        aliases=["pháp", "phap", "nước pháp", "france"],
        description="Cộng hòa Pháp",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="UNITED KINGDOM",
        aliases=["vương quốc anh", "anh quốc", "nước anh", "united kingdom", "uk"],
        description="Vương quốc Anh",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="INDIA",
        aliases=["ấn độ", "an do", "nước ấn", "india"],
        description="Cộng hòa Ấn Độ",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="INDONESIA",
        aliases=["indonesia", "in-đô-nê-xi-a"],
        description="Cộng hòa Indonesia",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="BRAZIL",
        aliases=["brazil", "bơ-ra-xin"],
        description="Cộng hòa Liên bang Brazil",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="CANADA",
        aliases=["canada"],
        description="Quốc gia Canada",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="RUSSIA",
        aliases=["nga", "nước nga", "russia"],
        description="Liên bang Nga",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="EGYPT",
        aliases=["ai cập", "ai cap", "egypt"],
        description="Ai Cập",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="ARGENTINA",
        aliases=["argentina"],
        description="Argentina",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="SAUDI ARABIA",
        aliases=["ả rập xê út", "a rap xe ut", "saudi arabia"],
        description="Ả Rập Xê Út",
    ),
    # -------------------------------------------------------------------------
    # orders.o_orderstatus (Trạng thái đơn hàng)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="orders",
        column="o_orderstatus",
        value="O",
        aliases=["đang xử lý", "đang mở", "chưa giao", "open", "order open"],
        description="Trạng thái đơn hàng đang mở hoặc đang xử lý",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderstatus",
        value="F",
        aliases=[
            "đã hoàn tất",
            "hoàn tất",
            "hoàn thành",
            "đã giao xong",
            "fulfilled",
            "finished",
        ],
        description="Trạng thái đơn hàng đã hoàn tất giao dịch",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderstatus",
        value="P",
        aliases=["đang chờ", "chờ duyệt", "chờ xử lý", "pending"],
        description="Trạng thái đơn hàng đang chờ duyệt",
    ),
    # -------------------------------------------------------------------------
    # lineitem.l_shipmode (Phương thức vận chuyển)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="AIR",
        aliases=["đường hàng không", "hàng không", "máy bay", "đường bay", "air"],
        description="Vận chuyển bằng máy bay / đường hàng không",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="SHIP",
        aliases=["đường biển", "đường tàu thủy", "tàu biển", "đường thủy", "ship"],
        description="Vận chuyển bằng đường biển / tàu thủy",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="TRUCK",
        aliases=["đường bộ", "xe tải", "đường ô tô", "truck"],
        description="Vận chuyển bằng xe tải đường bộ",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="RAIL",
        aliases=["đường sắt", "tàu hỏa", "hỏa xa", "rail"],
        description="Vận chuyển bằng đường sắt / tàu hỏa",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="MAIL",
        aliases=["bưu điện", "thư tín", "chuyển phát", "mail"],
        description="Vận chuyển qua dịch vụ bưu chính thư tín",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="FOB",
        aliases=["fob", "giao tại cảng"],
        description="Phương thức giao nhận tại mạn tàu (FOB)",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="REG AIR",
        aliases=["hàng không thông thường", "reg air"],
        description="Vận chuyển bằng hàng không phổ thông",
    ),
    # -------------------------------------------------------------------------
    # lineitem.l_returnflag (Cờ trạng thái hoàn trả hàng)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="lineitem",
        column="l_returnflag",
        value="R",
        aliases=[
            "hoàn trả",
            "trả hàng",
            "hoàn hàng",
            "bị trả lại",
            "returned",
            "return",
        ],
        description="Dòng hàng bị người mua gửi trả lại",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_returnflag",
        value="A",
        aliases=["chấp nhận", "tiếp nhận", "accepted"],
        description="Dòng hàng đã được chấp nhận",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_returnflag",
        value="N",
        aliases=["không hoàn", "không trả", "none"],
        description="Dòng hàng bình thường không có hoàn trả",
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
            # Tránh false positive với các alias quá ngắn (< 4 ký tự như 'nga', 'car')
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
