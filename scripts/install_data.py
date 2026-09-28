import duckdb

con = duckdb.connect()

# Kích hoạt module TPC-DS
con.execute("INSTALL tpcds; LOAD tpcds;")

# Sinh dữ liệu: sf = 0.01 (~15MB dev/test), sf = 0.1 (~120MB demo), hoặc sf = 1 (~1GB dữ liệu chuẩn)
con.execute("CALL dsdgen(sf = 0.1);")

# Xuất dữ liệu ra định dạng PARQUET vào thư mục 'data' để nạp nhanh vào kho dữ liệu khi cần
con.execute("EXPORT DATABASE 'data' (FORMAT PARQUET);")

print("Đã tạo xong 24 bảng dữ liệu TPC-DS dạng PARQUET trong thư mục 'data'!")
