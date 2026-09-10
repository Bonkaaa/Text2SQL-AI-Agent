import argparse
import sys
from pathlib import Path

# Đảm bảo import được src khi chạy script trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_settings
from src.utils.tpch_seeder import get_table_row_counts, seed_tpch_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Khởi tạo cơ sở dữ liệu DuckDB với bộ dữ liệu chuẩn TPC-H."
    )
    parser.add_argument(
        "--sf",
        type=float,
        default=0.01,
        help="Scale factor dữ liệu TPC-H (mặc định 0.01 cho dev/test, 0.1 cho demo)",
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

    print(f"[*] Bắt đầu khởi tạo dữ liệu TPC-H (scale_factor={args.sf})...")
    print(f"[*] Đường dẫn cơ sở dữ liệu: {target_path}")

    conn = seed_tpch_data(db_path=target_path, scale_factor=args.sf)
    row_counts = get_table_row_counts(conn)
    conn.close()

    print("\n[+] Khởi tạo thành công 8 bảng TPC-H!")
    print("----------------------------------------")
    for table, count in row_counts.items():
        print(f"  - {table:12}: {count:,} dòng")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
