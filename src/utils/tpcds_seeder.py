"""Module khởi tạo và nạp dữ liệu chuẩn TPC-DS Benchmark (24 bảng) vào DuckDB.

Cung cấp:
- Danh mục 24 bảng TPC-DS (Fact, Dimension, Channel, Demographics).
- Hàm kiểm tra tính toàn vẹn và sự hiện diện của 24 bảng.
- Hàm thống kê số lượng bản ghi của từng bảng.
- Hàm sinh dữ liệu TPC-DS tự động qua DuckDB extension `tpcds`.
"""

from pathlib import Path
from typing import Final

import duckdb

TPCDS_TABLES: Final[tuple[str, ...]] = (
    # Fact & Returns (7 bảng)
    "store_sales",
    "store_returns",
    "catalog_sales",
    "catalog_returns",
    "web_sales",
    "web_returns",
    "inventory",
    # Core Business Dimensions (5 bảng)
    "item",
    "customer",
    "customer_address",
    "customer_demographics",
    "date_dim",
    # Demographic & Auxiliary Dimensions (7 bảng)
    "household_demographics",
    "income_band",
    "promotion",
    "reason",
    "ship_mode",
    "time_dim",
    "warehouse",
    # Channel Dimensions (5 bảng)
    "store",
    "call_center",
    "catalog_page",
    "web_page",
    "web_site",
)


def verify_tpcds_tables(conn: duckdb.DuckDBPyConnection) -> bool:
    """Kiểm tra sự tồn tại đầy đủ của 24 bảng chuẩn TPC-DS trong database.

    Args:
        conn: Kết nối DuckDB đang mở.

    Returns:
        bool: True nếu toàn bộ 24 bảng đều tồn tại trong schema 'main', ngược lại False.
    """
    tables_result = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    existing_tables = {row[0].lower() for row in tables_result}
    return all(table.lower() in existing_tables for table in TPCDS_TABLES)


def get_table_row_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Đếm và trả về số lượng bản ghi của từng bảng trong 24 bảng TPC-DS.

    Args:
        conn: Kết nối DuckDB đang mở.

    Returns:
        dict[str, int]: Từ điển ánh xạ {tên_bảng: số_dòng}.
    """
    counts: dict[str, int] = {}
    for table in TPCDS_TABLES:
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = result[0] if result else 0
        except duckdb.Error:
            counts[table] = 0
    return counts


def seed_tpcds_data(
    db_path: str = ":memory:",
    scale_factor: float = 0.01,
) -> duckdb.DuckDBPyConnection:
    """Khởi tạo database DuckDB và sinh dữ liệu chuẩn TPC-DS bằng extension có sẵn.

    Args:
        db_path: Đường dẫn file DuckDB hoặc ':memory:' để chạy trên RAM.
        scale_factor: Tỷ lệ quy mô dữ liệu (0.01 cho unit test/dev ~15MB, 0.1 cho demo ~120MB).

    Returns:
        duckdb.DuckDBPyConnection: Kết nối tới database đã sinh dữ liệu.

    Raises:
        ValueError: Nếu scale_factor nhỏ hơn hoặc bằng 0.
    """
    if scale_factor <= 0:
        raise ValueError(
            f"scale_factor phải là số thực dương > 0, nhận được: {scale_factor}"
        )

    # Nếu lưu thành file, đảm bảo thư mục cha đã tồn tại
    if db_path != ":memory:":
        file_path = Path(db_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(db_path)

    # Cài đặt và tải extension TPC-DS tích hợp sẵn của DuckDB
    conn.execute("INSTALL tpcds;")
    conn.execute("LOAD tpcds;")

    # Sinh dữ liệu TPC-DS với scale factor tương ứng
    conn.execute(f"CALL dsdgen(sf={scale_factor});")

    return conn
