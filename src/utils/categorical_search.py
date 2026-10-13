"""Tra cứu giá trị phân loại thực tế trong database TPC-H (Entity / Value Linking).

Component 2.2:
- Cung cấp danh bạ chỉ mục các giá trị phân loại chính trong 8 bảng TPC-H kèm từ đồng nghĩa tiếng Việt/tiếng Anh.
- Hàm find_matching_categorical_values: Ánh xạ câu hỏi người dùng về đúng tên cột và giá trị chuẩn trong kho dữ liệu.
- Hàm format_categorical_context: Đóng gói các giá trị tìm được thành context Markdown nạp vào prompt cho LLM.
"""

from __future__ import annotations

import re
import unicodedata
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
    # 1. customer.c_mktsegment (5 Phân khúc thị trường)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="AUTOMOBILE",
        aliases=[
            "ngành ô tô",
            "nganh o to",
            "ô tô",
            "o to",
            "ô-tô",
            "xe hơi",
            "xe hoi",
            "automobile",
            "automotive",
        ],
        description="Khách hàng thuộc phân khúc thị trường sản xuất và phụ tùng ô tô",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="BUILDING",
        aliases=[
            "xây dựng",
            "xay dung",
            "công trình",
            "cong trinh",
            "building",
            "kiến trúc",
        ],
        description="Khách hàng thuộc phân khúc thị trường xây dựng và công trình",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="FURNITURE",
        aliases=[
            "nội thất",
            "noi that",
            "đồ gỗ",
            "do go",
            "bàn ghế",
            "furniture",
        ],
        description="Khách hàng thuộc phân khúc thị trường sản xuất và bán lẻ đồ nội thất",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="HOUSEHOLD",
        aliases=[
            "đồ gia dụng",
            "do gia dung",
            "gia dụng",
            "household",
            "thiết bị gia dụng",
        ],
        description="Khách hàng thuộc phân khúc thiết bị và vật dụng gia đình",
    ),
    CategoricalEntry(
        table="customer",
        column="c_mktsegment",
        value="MACHINERY",
        aliases=[
            "máy móc",
            "may moc",
            "cơ khí",
            "co khi",
            "thiết bị máy",
            "machinery",
            "chế tạo máy",
        ],
        description="Khách hàng thuộc phân khúc máy móc và thiết bị công nghiệp nặng",
    ),
    # -------------------------------------------------------------------------
    # 2. orders.o_orderstatus (Trạng thái đơn hàng)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="orders",
        column="o_orderstatus",
        value="O",
        aliases=["đang xử lý", "dang xu ly", "chưa hoàn tất", "đang mở", "open order"],
        description="Đơn hàng đang trong quá trình xử lý (Open)",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderstatus",
        value="F",
        aliases=["hoàn tất", "hoan tat", "đã xử lý xong", "đã hoàn thành", "fulfilled"],
        description="Đơn hàng đã được xử lý và giao xong (Fulfilled)",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderstatus",
        value="P",
        aliases=["chờ xử lý", "cho xu ly", "tạm dừng", "đang treo", "pending"],
        description="Đơn hàng đang chờ duyệt hoặc thanh toán (Pending)",
    ),
    # -------------------------------------------------------------------------
    # 3. orders.o_orderpriority (Mức độ ưu tiên đơn hàng)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="orders",
        column="o_orderpriority",
        value="1-URGENT",
        aliases=["khẩn cấp", "khan cap", "cực kỳ gấp", "urgent", "1-urgent"],
        description="Đơn hàng có độ ưu tiên khẩn cấp cấp độ 1",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderpriority",
        value="2-HIGH",
        aliases=["ưu tiên cao", "uu tien cao", "rất gấp", "high priority", "2-high"],
        description="Đơn hàng có độ ưu tiên cao cấp độ 2",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderpriority",
        value="3-MEDIUM",
        aliases=[
            "ưu tiên trung bình",
            "uu tien trung binh",
            "medium priority",
            "3-medium",
        ],
        description="Đơn hàng có độ ưu tiên trung bình cấp độ 3",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderpriority",
        value="4-NOT SPECIFIED",
        aliases=["không xác định", "chưa chỉ định", "not specified", "4-not specified"],
        description="Đơn hàng không có mức độ ưu tiên xác định",
    ),
    CategoricalEntry(
        table="orders",
        column="o_orderpriority",
        value="5-LOW",
        aliases=["ưu tiên thấp", "uu tien thap", "không vội", "low priority", "5-low"],
        description="Đơn hàng có độ ưu tiên thấp cấp độ 5",
    ),
    # -------------------------------------------------------------------------
    # 4. lineitem.l_shipmode (Phương thức vận chuyển)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="AIR",
        aliases=[
            "đường hàng không",
            "duong hang khong",
            "máy bay",
            "may bay",
            "hàng không",
            "air",
        ],
        description="Vận chuyển nhanh bằng đường hàng không",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="SHIP",
        aliases=[
            "tàu biển",
            "tau bien",
            "đường biển",
            "duong bien",
            "tàu thủy",
            "tau thuy",
            "đường thủy",
            "ship",
        ],
        description="Vận chuyển đường biển bằng tàu hàng",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="TRUCK",
        aliases=["xe tải", "xe tai", "đường bộ", "duong bo", "truck"],
        description="Vận chuyển đường bộ bằng xe tải",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="RAIL",
        aliases=["đường sắt", "duong sat", "tàu hỏa", "tau hoa", "rail"],
        description="Vận chuyển bằng đường sắt hỏa xa",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="MAIL",
        aliases=["bưu điện", "buu dien", "chuyển phát thư", "mail"],
        description="Vận chuyển qua dịch vụ bưu chính bưu điện",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="FOB",
        aliases=["fob", "giao tại mạn tàu", "free on board"],
        description="Phương thức giao nhận tại cảng xuất FOB",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_shipmode",
        value="REG AIR",
        aliases=["hàng không tiêu chuẩn", "regular air", "reg air"],
        description="Vận chuyển đường hàng không thông thường",
    ),
    # -------------------------------------------------------------------------
    # 5. lineitem.l_returnflag (Cờ hoàn trả hàng)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="lineitem",
        column="l_returnflag",
        value="R",
        aliases=[
            "hoàn hàng",
            "hoan hang",
            "hoàn trả",
            "hoan tra",
            "trả hàng",
            "tra hang",
            "đổi trả",
            "returned",
        ],
        description="Mặt hàng bị khách hàng hoàn trả lại (Returned)",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_returnflag",
        value="A",
        aliases=["chấp nhận", "chap nhan", "đã chấp thuận", "accepted"],
        description="Mặt hàng đã được chấp thuận và giữ lại (Accepted)",
    ),
    CategoricalEntry(
        table="lineitem",
        column="l_returnflag",
        value="N",
        aliases=["chưa xử lý hoàn", "chưa trả", "none"],
        description="Mặt hàng chưa có trạng thái đổi trả (None)",
    ),
    # -------------------------------------------------------------------------
    # 6. region.r_name (5 Châu lục / Khu vực kinh tế)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="region",
        column="r_name",
        value="ASIA",
        aliases=["châu á", "chau a", "khu vực châu á", "asia", "asian"],
        description="Khu vực kinh tế Châu Á",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="EUROPE",
        aliases=["châu âu", "chau au", "khu vực châu âu", "europe", "european"],
        description="Khu vực kinh tế Châu Âu",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="AFRICA",
        aliases=["châu phi", "chau phi", "khu vực châu phi", "africa", "african"],
        description="Khu vực kinh tế Châu Phi",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="AMERICA",
        aliases=["châu mỹ", "chau my", "khu vực châu mỹ", "america", "american"],
        description="Khu vực kinh tế Châu Mỹ",
    ),
    CategoricalEntry(
        table="region",
        column="r_name",
        value="MIDDLE EAST",
        aliases=["trung đông", "trung dong", "khu vực trung đông", "middle east"],
        description="Khu vực kinh tế Trung Đông",
    ),
    # -------------------------------------------------------------------------
    # 7. nation.n_name (Quốc gia tiêu biểu trong 25 quốc gia TPC-H)
    # -------------------------------------------------------------------------
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="VIETNAM",
        aliases=["việt nam", "viet nam", "vietnam"],
        description="Quốc gia Việt Nam",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="JAPAN",
        aliases=["nhật bản", "nhat ban", "japan", "japanese"],
        description="Quốc gia Nhật Bản",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="CHINA",
        aliases=["trung quốc", "trung quoc", "china", "chinese"],
        description="Quốc gia Trung Quốc",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="UNITED STATES",
        aliases=["hoa kỳ", "hoa ky", "nước mỹ", "united states", "usa"],
        description="Quốc gia Hợp chủng quốc Hoa Kỳ",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="GERMANY",
        aliases=["nước đức", "nuoc duc", "germany", "german"],
        description="Quốc gia Cộng hòa Liên bang Đức",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="FRANCE",
        aliases=["nước pháp", "nuoc phap", "france", "french"],
        description="Quốc gia Cộng hòa Pháp",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="UNITED KINGDOM",
        aliases=["vương quốc anh", "nuoc anh", "united kingdom", "uk"],
        description="Quốc gia Vương quốc Anh",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="INDIA",
        aliases=["ấn độ", "an do", "india", "indian"],
        description="Quốc gia Cộng hòa Ấn Độ",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="BRAZIL",
        aliases=["brazil", "bra-xin"],
        description="Quốc gia Brazil",
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
        value="EGYPT",
        aliases=["ai cập", "ai cap", "egypt"],
        description="Quốc gia Ai Cập",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="RUSSIA",
        aliases=["nước nga", "nuoc nga", "russia", "russian"],
        description="Quốc gia Liên bang Nga",
    ),
    CategoricalEntry(
        table="nation",
        column="n_name",
        value="INDONESIA",
        aliases=["indonesia"],
        description="Quốc gia Indonesia",
    ),
]


# ==============================================================================
# 2. CÁC HÀM TIỆN ÍCH TRA CỨU VÀ ĐÓNG GÓI CONTEXT
# ==============================================================================


def _normalize_text(text: str) -> str:
    """Chuẩn hóa chuỗi ký tự: đưa về chữ thường, chuẩn hóa dấu unicode tiếng Việt."""
    if not text:
        return ""
    text = text.lower().strip()
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text


def get_all_categorical_entries() -> list[CategoricalEntry]:
    """Lấy danh sách tất cả các mục giá trị phân loại đã được lập chỉ mục trong TPC-H."""
    return list(CATEGORICAL_REGISTRY)


def find_matching_categorical_values(
    query: str,
    top_k: int = 5,
    min_score: float = 70.0,
) -> list[CategoricalMatch]:
    """Tìm kiếm và ánh xạ các giá trị phân loại có trong câu hỏi của người dùng.

    Thuật toán kết hợp:
    1. Exact keyword / alias substring search (ưu tiên điểm 100).
    2. Fuzzy matching (rapidfuzz token_set_ratio) cho từ khóa gõ sai hoặc biến thể.
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

    # Bước 2: Fuzzy Matching cho các trường hợp còn lại
    for entry in CATEGORICAL_REGISTRY:
        key = (entry.table, entry.column, entry.value)
        if key in matches_map:
            continue

        col_key = (entry.table, entry.column)
        if any(
            m.exact_match for (t, c, _), m in matches_map.items() if (t, c) == col_key
        ):
            continue

        best_score = 0.0
        best_alias = ""
        for alias in entry.aliases:
            norm_alias = _normalize_text(alias)
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

    sorted_matches = sorted(
        matches_map.values(),
        key=lambda m: (m.exact_match, m.similarity_score),
        reverse=True,
    )

    return sorted_matches[:top_k]


def format_categorical_context(matches: list[CategoricalMatch]) -> str:
    """Đóng gói danh sách kết quả tra cứu thành chuỗi Markdown đưa vào prompt."""
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
