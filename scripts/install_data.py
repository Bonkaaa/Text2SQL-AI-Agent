import duckdb

con = duckdb.connect()

# Kích hoạt module TPC-H
con.execute("INSTALL tpch; LOAD tpch;")

# Sinh dữ liệu: sf = 0.1 (~100MB để test) hoặc sf = 1 (~1GB dữ liệu chuẩn)
con.execute("CALL dbgen(sf = 0.1);")

# # Xuất toàn bộ 8 bảng thành file CSV vào thư mục 'tpch_csv'
# con.execute("EXPORT DATABASE 'tpch_csv' (FORMAT CSV, HEADER TRUE);")

# Hoặc xuất ra định dạng PARQUET nếu muốn nạp nhanh vào kho dữ liệu
con.execute("EXPORT DATABASE 'data' (FORMAT PARQUET);")

print("Đã tạo xong 8 bảng dữ liệu TPC-H!")