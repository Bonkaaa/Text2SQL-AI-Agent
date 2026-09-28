"""Script dòng lệnh (CLI) khởi tạo cơ sở dữ liệu DuckDB với bộ dữ liệu chuẩn TPC-DS (24 bảng).

Sử dụng:
    python scripts/init_db.py [--sf SCALE_FACTOR] [--db-path DATABASE_PATH]
"""

import argparse
import sys
from pathlib import Path

# Đảm bảo import được src khi chạy script trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_settings
from src.utils.tpcds_seeder import (
    TPCDS_TABLES,
    get_table_row_counts,
    seed_tpcds_data,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Khởi tạo cơ sở dữ liệu DuckDB với bộ dữ liệu chuẩn TPC-DS (24 bảng)."
    )
    parser.add_argument(
        "--sf",
        type=float,
        default=0.01,
        help="Scale factor dữ liệu TPC-DS (mặc định 0.01 cho dev/test ~15MB, 0.1 cho demo ~120MB)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Đường dẫn file DuckDB (mặc định lấy từ cấu hình DUCKDB_PATH)",
    )
    args = parser.parse_args()

    settings = get_settings()
    target_path = args.db_path or settings.duckdb_path

    print(f"[*] Bắt đầu khởi tạo dữ liệu TPC-DS (scale_factor={args.sf})...")
    print(f"[*] Đường dẫn cơ sở dữ liệu: {target_path}")

    conn = seed_tpcds_data(db_path=target_path, scale_factor=args.sf)
    row_counts = get_table_row_counts(conn)
    conn.close()

    print(f"\n[+] Khởi tạo thành công {len(row_counts)} bảng TPC-DS!")
    print("=" * 50)
    print(f"{'Tên bảng':<30} {'Số dòng':>15}")
    print("-" * 50)

    # In theo thứ tự danh mục TPCDS_TABLES
    total_rows = 0
    for table in TPCDS_TABLES:
        count = row_counts.get(table, 0)
        total_rows += count
        print(f"  - {table:<26}: {count:>15,}")

    print("=" * 50)
    print(f"{'TỔNG CỘNG TẤT CẢ CÁC BẢNG:':<28} {total_rows:>18,}")
    print("=" * 50)


if __name__ == "__main__":
    main()
