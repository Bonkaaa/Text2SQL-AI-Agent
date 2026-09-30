---
name: duckdb-sql
description: Syntax conventions, date-time arithmetic, aggregation functions, QUALIFY window filtering, and analytical optimization guidelines for DuckDB OLAP database engine.
metadata:
  domain: sql-optimization
  engine: duckdb
---

# DuckDB Dialect & Optimization Guidelines

Kỹ năng này cung cấp hướng dẫn cú pháp chuẩn xác và các quy tắc tối ưu hóa dành riêng cho engine cơ sở dữ liệu phân tích **DuckDB (v1.2+)** trong hệ thống phân tích kho dữ liệu đa kênh TPC-DS.

---

## 1. Quy Tắc Xử Lý Kiểu Ngày Tháng (Date/Time Literals)

DuckDB là hệ thống kiểm tra kiểu dữ liệu nghiêm ngặt (strongly-typed). **Tuyệt đối không so sánh ngày tháng dưới dạng chuỗi thông thường**.

### Cú pháp chuẩn:
- **Khai báo literal**: Dùng `DATE 'YYYY-MM-DD'` (ví dụ: `DATE '2001-01-01'`).
- **Khoảng thời gian (Interval)**: Sử dụng cú pháp `INTERVAL '<number>' <UNIT>`:
  - `d_date + INTERVAL '1' YEAR`
  - `d_date - INTERVAL '30' DAY`
  - `d_date + INTERVAL '3' MONTH`
- **Trích xuất thành phần**:
  - `EXTRACT(YEAR FROM d_date)` hoặc `YEAR(d_date)`
  - `EXTRACT(MONTH FROM d_date)` hoặc `MONTH(d_date)`
  - `DATE_TRUNC('month', d_date)`
- **Lưu ý TPC-DS**:
  - Bảng Fact (`store_sales`, `web_sales`, `catalog_sales`) sử dụng surrogate key nguyên (`ss_sold_date_sk`). **Bắt buộc JOIN với `date_dim d ON ss_sold_date_sk = d.d_date_sk`** để lọc ngày thay vì ép kiểu `ss_sold_date_sk`.

---

## 2. Quy Tắc Phân Biệt Hoa Thường & Xử Lý Chuỗi (String Filtering)

- DuckDB mặc định **phân biệt hoa thường (case-sensitive)** khi so sánh chuỗi bằng toán tử `=`.
- Đối với dữ liệu TPC-DS:
  - Các mã định danh (`ca_state`, `cd_gender`, `cd_marital_status`, `sm_type`) được chuẩn hóa in hoa hoặc PascalCase (ví dụ: `'CA'`, `'M'`, `'EXPRESS'`).
  - Danh mục ngành hàng `item.i_category` được lưu dạng Title Case (ví dụ: `'Electronics'`, `'Women'`, `'Home'`).
- Khi tìm kiếm văn bản tự do, mô tả sản phẩm có thể có biến thể:
  - Dùng toán tử không phân biệt hoa thường: `i_item_desc ILIKE '%shirt%'`
  - Hoặc chuẩn hóa bằng hàm: `LOWER(i_item_desc) LIKE '%shirt%'`

---

## 3. Gom Nhóm & Xếp Hạng Nâng Cao (Aggregation & QUALIFY Clause)

### A. Tự động gom nhóm với `GROUP BY ALL`
DuckDB hỗ trợ `GROUP BY ALL` giúp tự động nhận diện tất cả các cột không nằm trong aggregate function. Điều này giúp câu lệnh gọn hơn và tránh lỗi liệt kê thiếu cột:
```sql
SELECT 
    i.i_category,
    d.d_year,
    COUNT(DISTINCT ss.ss_ticket_number) AS total_orders,
    ROUND(SUM(ss.ss_net_paid), 2) AS total_revenue
FROM store_sales ss
JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk
JOIN item i ON ss.ss_item_sk = i.i_item_sk
WHERE d.d_year = 2001
GROUP BY ALL
ORDER BY total_revenue DESC
LIMIT 10;
```

### B. Lọc Hàm Cửa Sổ Bằng Mệnh Đề `QUALIFY` (Tránh Viết CTE Dài Dòng)
DuckDB hỗ trợ mệnh đề **`QUALIFY`** cho phép lọc trực tiếp kết quả của Window Functions (`DENSE_RANK`, `ROW_NUMBER`, `RANK`) ngay sau `GROUP BY`, không cần phải lồng Subquery hoặc bọc CTE:
```sql
-- Tìm Top 3 mặt hàng có doanh thu cao nhất trong từng ngành hàng (Top-N per Category)
SELECT 
    i.i_category,
    i.i_item_desc,
    ROUND(SUM(ss.ss_net_paid), 2) AS item_revenue,
    DENSE_RANK() OVER (
        PARTITION BY i.i_category 
        ORDER BY SUM(ss.ss_net_paid) DESC
    ) AS category_rank
FROM store_sales ss
JOIN item i ON ss.ss_item_sk = i.i_item_sk
WHERE ss.ss_net_paid IS NOT NULL
GROUP BY ALL
QUALIFY category_rank <= 3
ORDER BY i.i_category, category_rank;
```

---

## 4. Quy Chuẩn Tính Toán Tài Chính & An Toàn Dữ Liệu (OLAP Calculations)

1. **Phòng chống chia cho 0 (`NULLIF` Zero-Division Protection)**:
   - Khi tính toán các tỷ lệ phần trăm (biên lợi nhuận, tỷ lệ hoàn trả), luôn bọc mẫu số bằng `NULLIF(..., 0)` để tránh lỗi runtime hoặc giá trị `NaN`/`Infinity`:
     ```sql
     ROUND(SUM(ss.ss_net_profit) / NULLIF(SUM(ss.ss_net_paid), 0) * 100, 2) AS profit_margin_pct
     ```
2. **Làm tròn tiền tệ & định dạng chuẩn (`ROUND` & `COALESCE`)**:
   - Mọi biểu thức tổng tiền tệ bắt buộc bọc `ROUND(..., 2)` và `COALESCE(..., 0)`:
     ```sql
     ROUND(COALESCE(SUM(ss.ss_net_paid), 0), 2) AS net_revenue
     ```
3. **Ép kiểu an toàn (`TRY_CAST`)**:
   - Khi cần chuyển đổi kiểu từ các cột có khả năng chứa dữ liệu bẩn, ưu tiên dùng `TRY_CAST(col AS INTEGER)` thay vì `CAST(...)` để tránh crash cả pipeline truy vấn.

---

## 5. Ràng Buộc An Toàn Tuyệt Đối (Safety Guardrails)

1. **CHỈ CHO PHÉP TRUY VẤN ĐỌC (`SELECT` ONLY)**:
   - Nghiêm cấm tuyệt đối mọi câu lệnh thay đổi cấu trúc hoặc dữ liệu: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`.
2. **LUÔN GIỚI HẠN SỐ DÒNG (CLAMP LIMIT)**:
   - Mọi câu lệnh SQL truy vấn danh sách bắt buộc có mệnh đề `LIMIT` (mặc định $\le 1000$).
3. **KHÔNG DÙNG MULTIPLE STATEMENTS**:
   - Chỉ sinh duy nhất một câu lệnh SQL đơn lẻ, không nối nhiều câu lệnh bằng dấu chấm phẩy `;` để tránh nguy cơ SQL Injection.
