from pathlib import Path
from typing import Final

import duckdb

TPCH_TABLES: Final[tuple[str, ...]] = (
    "customer",
    "orders",
    "lineitem",
    "part",
    "partsupp",
    "supplier",
    "nation",
    "region",
)


def verify_tpch_tables(conn: duckdb.DuckDBPyConnection) -> bool:
    """Kiểm tra sự tồn tại đầy đủ của 8 bảng chuẩn TPC-H trong database."""
    tables_result = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    existing_tables = {row[0].lower() for row in tables_result}
    return all(table.lower() in existing_tables for table in TPCH_TABLES)


def get_table_row_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Đếm và trả về số lượng bản ghi của từng bảng TPC-H."""
    counts: dict[str, int] = {}
    for table in TPCH_TABLES:
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            counts[table] = result[0] if result else 0
        except duckdb.Error:
            counts[table] = 0
    return counts


def seed_tpch_data(
    db_path: str = ":memory:",
    scale_factor: float = 0.01,
) -> duckdb.DuckDBPyConnection:
    """Khởi tạo database DuckDB và sinh dữ liệu chuẩn TPC-H bằng extension có sẵn.

    Args:
        db_path: Đường dẫn file DuckDB hoặc ':memory:' để chạy trên RAM.
        scale_factor: Tỷ lệ quy mô dữ liệu (0.01 cho unit test, 0.1 cho dev/demo).

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

    # Cài đặt và tải extension TPC-H tích hợp sẵn của DuckDB
    conn.execute("INSTALL tpch;")
    conn.execute("LOAD tpch;")

    # Sinh dữ liệu TPC-H với scale factor tương ứng
    conn.execute(f"CALL dbgen(sf={scale_factor});")

    return conn
