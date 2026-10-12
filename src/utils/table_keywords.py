"""Từ điển từ khóa đồng nghĩa ánh xạ 8 bảng TPC-H (Table Keyword Mapping).

Module này lưu trữ danh bạ từ khóa tiếng Việt và tiếng Anh phổ biến để phục vụ việc
nhận diện bảng dữ liệu liên quan từ câu hỏi tự nhiên của người dùng trong Schema Retriever.
"""

from __future__ import annotations

from typing import Final

TABLE_KEYWORD_MAP: Final[dict[str, list[str]]] = {
    "customer": [
        "khách hàng",
        "khach hang",
        "người mua",
        "nguoi mua",
        "người tiêu dùng",
        "nguoi tieu dung",
        "customer",
        "customers",
        "phân khúc khách hàng",
        "số dư khách hàng",
    ],
    "orders": [
        "đơn hàng",
        "don hang",
        "đơn đặt hàng",
        "don dat hang",
        "order",
        "orders",
        "hóa đơn",
        "hoa don",
        "giao dịch",
        "giao dich",
        "ngày đặt hàng",
        "trạng thái đơn",
        "độ ưu tiên đơn",
    ],
    "lineitem": [
        "mặt hàng",
        "mat hang",
        "chi tiết đơn hàng",
        "chi tiet don hang",
        "dòng sản phẩm",
        "dong san pham",
        "dòng hàng",
        "dong hang",
        "lineitem",
        "line item",
        "chi tiết",
        "chi tiet",
        "chiết khấu",
        "chiet khau",
        "vận chuyển",
        "van chuyen",
        "giao hàng",
        "giao hang",
        "hoàn hàng",
        "hoan hang",
        "trả hàng",
        "tra hang",
        "ngày giao",
    ],
    "part": [
        "linh kiện",
        "linh kien",
        "sản phẩm",
        "san pham",
        "phụ tùng",
        "phu tung",
        "part",
        "parts",
        "vật tư",
        "vat tu",
        "nhà sản xuất linh kiện",
        "thương hiệu",
        "thuong hieu",
        "giá bán lẻ",
    ],
    "partsupp": [
        "tồn kho",
        "ton kho",
        "cung ứng",
        "cung ung",
        "hàng tồn",
        "hang ton",
        "khả năng cung cấp",
        "kha nang cung cap",
        "partsupp",
        "chi phí cung ứng",
        "chi phi cung ung",
        "số lượng có sẵn",
    ],
    "supplier": [
        "nhà cung cấp",
        "nha cung cap",
        "nhà phân phối",
        "nha phan phoi",
        "npp",
        "supplier",
        "suppliers",
        "đối tác cung ứng",
        "doi tac cung ung",
        "công nợ nhà cung cấp",
    ],
    "nation": [
        "quốc gia",
        "quoc gia",
        "nước",
        "nuoc",
        "đất nước",
        "dat nuoc",
        "nation",
        "country",
        "việt nam",
        "nhật bản",
        "hoa kỳ",
    ],
    "region": [
        "khu vực",
        "khu vuc",
        "châu lục",
        "chau luc",
        "vùng",
        "vung",
        "region",
        "lãnh thổ",
        "châu á",
        "châu âu",
        "châu mỹ",
    ],
}


def get_table_keywords() -> dict[str, list[str]]:
    """Lấy bản đồ ánh xạ từ khóa của 8 bảng TPC-H."""
    return dict(TABLE_KEYWORD_MAP)


__all__ = ["TABLE_KEYWORD_MAP", "get_table_keywords"]
