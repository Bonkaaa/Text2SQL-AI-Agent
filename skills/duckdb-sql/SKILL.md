---
name: duckdb-sql
description: Syntax conventions, date-time arithmetic, aggregation functions, and analytical optimization guidelines for DuckDB OLAP database engine.
metadata:
  domain: sql-optimization
  engine: duckdb
---

# DuckDB Dialect & Optimization Guidelines

Kỹ năng này cung cấp hướng dẫn cú pháp chuẩn xác và các quy tắc tối ưu hóa dành riêng cho engine cơ sở dữ liệu phân tích **DuckDB (v1.2+)**.

## 1. Quy Tắc Xử Lý Kiểu Ngày Tháng (Date/Time Literals)

DuckDB là hệ thống kiểm tra kiểu dữ liệu nghiêm ngặt (strongly-typed). **Tuyệt đối không so sánh ngày tháng dưới dạng chuỗi thông thường**.

### Cú pháp chuẩn:
- **Khai báo literal**: Dùng `DATE 'YYYY-MM-DD'` (ví dụ: `DATE '1995-01-01'`).
- **Khoảng thời gian (Interval)**: Sử dụng cú pháp `INTERVAL '<number>' <UNIT>`:
  - `DATE '1995-01-01' + INTERVAL '1' YEAR`
  - `o_orderdate + INTERVAL '3' MONTH`
  - `l_shipdate - INTERVAL '7' DAY`
- **Trích xuất thành phần**:
  - `EXTRACT(YEAR FROM o_orderdate)` hoặc `YEAR(o_orderdate)`
  - `EXTRACT(MONTH FROM o_orderdate)` hoặc `MONTH(o_orderdate)`
  - `DATE_TRUNC('month', o_orderdate)`

---

## 2. Quy Tắc Phân Biệt Hoa Thường & Xử Lý Chuỗi (String Filtering)

- DuckDB mặc định **phân biệt hoa thường (case-sensitive)** khi so sánh chuỗi bằng toán tử `=`.
- Đối với dữ liệu TPC-H, hầu hết các mã danh mục (`c_mktsegment`, `r_name`, `o_orderstatus`, `l_shipmode`) được lưu dưới dạng **IN HOA** (ví dụ: `'BUILDING'`, `'ASIA'`, `'AIR'`).
- Khi tìm kiếm văn bản tự do hoặc tên có thể có biến thể:
  - Dùng toán tử không phân biệt hoa thường: `ILIKE '%steel%'`
  - Hoặc chuẩn hóa bằng hàm: `LOWER(p_name) LIKE '%steel%'`

---

## 3. Gom Nhóm & Xếp Hạng Nâng Cao (Aggregation & Window Functions)

### A. Gom nhóm (GROUP BY)
- Trong DuckDB, có thể dùng `GROUP BY ALL` để tự động gom nhóm tất cả các cột không phải aggregate, hoặc liệt kê tường minh các cột select:
  ```sql
  SELECT c_name, n_name, SUM(l_extendedprice) AS total_spent
  FROM customer JOIN orders ON c_custkey = o_custkey JOIN lineitem ON o_orderkey = l_orderkey JOIN nation ON c_nationkey = n_nationkey
  GROUP BY c_name, n_name
  ORDER BY total_spent DESC
  LIMIT 10;
  ```

### B. Hàm Cửa Sổ (Window Functions)
- Để tìm Top-N trong từng nhóm (ví dụ: Top 3 khách hàng chi tiêu nhiều nhất trong mỗi quốc gia):
  ```sql
  WITH ranked_customers AS (
      SELECT 
          c.c_name,
          n.n_name,
          SUM(l.l_extendedprice * (1 - l.l_discount)) AS rev,
          DENSE_RANK() OVER (PARTITION BY n.n_name ORDER BY SUM(l.l_extendedprice * (1 - l.l_discount)) DESC) AS rk
      FROM customer c
      JOIN orders o ON c.c_custkey = o.o_custkey
      JOIN lineitem l ON o.o_orderkey = l.l_orderkey
      JOIN nation n ON c.c_nationkey = n.n_nationkey
      GROUP BY c.c_name, n.n_name
  )
  SELECT c_name, n_name, rev
  FROM ranked_customers
  WHERE rk <= 3
  ORDER BY n_name, rev DESC;
  ```

---

## 4. Ràng Buộc An Toàn Tuyệt Đối (Safety Guardrails)

1. **CHỈ CHO PHÉP TRUY VẤN ĐỌC (`SELECT` ONLY)**:
   - Nghiêm cấm tuyệt đối mọi câu lệnh thay đổi cấu trúc hoặc dữ liệu: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`.
2. **LUÔN GIỚI HẠN SỐ DÒNG (CLAMP LIMIT)**:
   - Mọi câu lệnh SQL truy vấn danh sách bắt buộc có mệnh đề `LIMIT` (mặc định $\le 1000$).
3. **KHÔNG DÙNG MULTIPLE STATEMENTS**:
   - Chỉ sinh duy nhất một câu lệnh SQL đơn lẻ, không nối nhiều câu lệnh bằng dấu chấm phẩy `;` để tránh nguy cơ SQL Injection.
