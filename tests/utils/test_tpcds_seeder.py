from pathlib import Path

import duckdb
import pytest

from src.utils.tpcds_seeder import (
    TPCDS_TABLES,
    get_table_row_counts,
    seed_tpcds_data,
    verify_tpcds_tables,
)


def test_seed_in_memory_db():
    """Kiểm tra khởi tạo dữ liệu TPC-DS trên bộ nhớ RAM (:memory:)."""
    conn = seed_tpcds_data(db_path=":memory:", scale_factor=0.01)

    # Đảm bảo connection mở và hợp lệ
    assert conn is not None

    # Kiểm tra đủ 24 bảng TPC-DS
    assert verify_tpcds_tables(conn) is True

    # Kiểm tra số lượng bảng trả về trong thống kê
    counts = get_table_row_counts(conn)
    assert len(counts) == 24

    # Kiểm tra bảng thời gian chuẩn TPC-DS
    # date_dim trong chuẩn TPC-DS có cố định 73,049 ngày (200 năm)
    assert counts["date_dim"] == 73049
    # time_dim có cố định 86,400 giây (24 giờ)
    assert counts["time_dim"] == 86400

    # Kiểm tra các bảng Fact & Dimension chính đều có dữ liệu (> 0)
    assert counts["store_sales"] > 0
    assert counts["customer"] > 0
    assert counts["item"] > 0

    conn.close()


def test_seed_persistent_file_db(tmp_path: Path):
    """Kiểm tra khởi tạo dữ liệu TPC-DS lưu thành file trên ổ đĩa."""
    db_file = tmp_path / "test_tpcds.duckdb"
    conn = seed_tpcds_data(db_path=str(db_file), scale_factor=0.01)
    conn.close()

    assert db_file.exists()

    # Mở lại kết nối từ file đã lưu và kiểm tra tính toàn vẹn
    reopened_conn = duckdb.connect(str(db_file), read_only=True)
    assert verify_tpcds_tables(reopened_conn) is True
    counts = get_table_row_counts(reopened_conn)
    assert counts["date_dim"] == 73049
    assert counts["store_sales"] > 0
    reopened_conn.close()


def test_invalid_scale_factor():
    """Kiểm tra scale_factor <= 0 phải báo lỗi ValueError."""
    with pytest.raises(ValueError, match="scale_factor"):
        seed_tpcds_data(db_path=":memory:", scale_factor=0)

    with pytest.raises(ValueError, match="scale_factor"):
        seed_tpcds_data(db_path=":memory:", scale_factor=-0.5)


def test_verify_tpcds_tables_missing():
    """Kiểm tra hàm verify_tpcds_tables trả về False nếu DB chưa có bảng."""
    empty_conn = duckdb.connect(":memory:")
    assert verify_tpcds_tables(empty_conn) is False
    empty_conn.close()


def test_tpcds_omnichannel_tables():
    """Kiểm tra sự hiện diện đầy đủ của cả 3 kênh bán hàng và 3 bảng đổi trả (Omnichannel)."""
    conn = seed_tpcds_data(db_path=":memory:", scale_factor=0.01)
    counts = get_table_row_counts(conn)

    # 3 kênh bán hàng
    assert counts["store_sales"] > 0
    assert counts["catalog_sales"] > 0
    assert counts["web_sales"] > 0

    # 3 kênh đổi trả
    assert counts["store_returns"] > 0
    assert counts["catalog_returns"] > 0
    assert counts["web_returns"] > 0

    # Tất cả 24 bảng đều thuộc danh mục TPCDS_TABLES
    for table in TPCDS_TABLES:
        assert table in counts
        assert counts[table] >= 0

    conn.close()
