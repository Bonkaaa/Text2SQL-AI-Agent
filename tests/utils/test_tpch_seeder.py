from pathlib import Path

import duckdb
import pytest

from src.utils.tpch_seeder import (
    TPCH_TABLES,
    get_table_row_counts,
    seed_tpch_data,
    verify_tpch_tables,
)


def test_seed_in_memory_db():
    """Kiểm tra khởi tạo dữ liệu TPC-H trên bộ nhớ RAM (:memory:)."""
    conn = seed_tpch_data(db_path=":memory:", scale_factor=0.01)

    # Đảm bảo connection mở và hợp lệ
    assert conn is not None

    # Kiểm tra đủ 8 bảng
    assert verify_tpch_tables(conn) is True

    # Kiểm tra số lượng bản ghi
    counts = get_table_row_counts(conn)
    assert len(counts) == 8

    # TPC-H quy định cố định số quốc gia và khu vực
    assert counts["nation"] == 25
    assert counts["region"] == 5

    # Các bảng khác phải có dữ liệu (> 0)
    for table in TPCH_TABLES:
        assert counts[table] > 0

    conn.close()


def test_seed_persistent_file_db(tmp_path: Path):
    """Kiểm tra khởi tạo dữ liệu TPC-H lưu thành file trên ổ đĩa."""
    db_file = tmp_path / "test_tpch.duckdb"
    conn = seed_tpch_data(db_path=str(db_file), scale_factor=0.01)
    conn.close()

    assert db_file.exists()

    # Mở lại kết nối từ file đã lưu và kiểm tra tính toàn vẹn
    reopened_conn = duckdb.connect(str(db_file), read_only=True)
    assert verify_tpch_tables(reopened_conn) is True
    counts = get_table_row_counts(reopened_conn)
    assert counts["nation"] == 25
    reopened_conn.close()


def test_invalid_scale_factor():
    """Kiểm tra scale_factor <= 0 phải báo lỗi ValueError."""
    with pytest.raises(ValueError, match="scale_factor"):
        seed_tpch_data(db_path=":memory:", scale_factor=0)

    with pytest.raises(ValueError, match="scale_factor"):
        seed_tpch_data(db_path=":memory:", scale_factor=-0.5)


def test_verify_tpch_tables_missing():
    """Kiểm tra hàm verify_tpch_tables trả về False nếu DB chưa có bảng."""
    empty_conn = duckdb.connect(":memory:")
    assert verify_tpch_tables(empty_conn) is False
    empty_conn.close()
