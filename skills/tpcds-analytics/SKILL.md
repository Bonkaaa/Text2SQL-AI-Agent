---
name: tpcds-analytics
description: Business rules, semantic metrics formulas, categorical values dictionary, relational snowflake join patterns, and date_dim join rules for the TPC-DS decision support benchmark schema.
metadata:
  domain: omnichannel-retail-analytics
  dataset: tpcds-benchmark
---

# TPC-DS Enterprise Omnichannel Retail Analytics Domain Skill

Kỹ năng này cung cấp toàn bộ từ điển nghiệp vụ, công thức chỉ số tài chính bán lẻ (Semantic Metrics Layer), quan hệ phân cấp Snowflake Schema và các quy tắc sinh truy vấn SQL chuẩn mực cho cơ sở dữ liệu **TPC-DS (24 bảng)**.

---

## 1. Cấu Trúc 24 Bảng & Mô Hình Đa Kênh (Omnichannel Retail Architecture)

Cơ sở dữ liệu TPC-DS mô phỏng một tập đoàn bán lẻ đa kênh với 3 kênh bán hàng độc lập, 3 kênh đổi trả hàng và tổng kho lưu trữ:

```
[store_sales]   <---> [store_returns]     (Kênh Cửa hàng Bán lẻ - Store Channel)
[web_sales]     <---> [web_returns]       (Kênh Trực tuyến - Web E-Commerce Channel)
[catalog_sales] <---> [catalog_returns]   (Kênh Đặt hàng Danh mục - Catalog Mail-Order)
[inventory]                               (Kho hàng & Tồn kho sản phẩm)
```

### Chi tiết 24 bảng trong lược đồ:
1. **Fact Bán hàng (Sales Facts)**:
   - `store_sales`: Giao dịch bán hàng trực tiếp tại quầy cửa hàng (`ss_sold_date_sk`, `ss_item_sk`, `ss_customer_sk`, `ss_store_sk`, `ss_net_paid`, `ss_net_profit`...).
   - `web_sales`: Giao dịch mua sắm trực tuyến trên website (`ws_sold_date_sk`, `ws_item_sk`, `ws_bill_customer_sk`, `ws_web_site_sk`, `ws_net_paid`...).
   - `catalog_sales`: Giao dịch đặt hàng qua ấn phẩm bưu điện (`cs_sold_date_sk`, `cs_item_sk`, `cs_bill_customer_sk`, `cs_catalog_page_sk`, `cs_net_paid`...).
2. **Fact Đổi trả (Returns Facts)**:
   - `store_returns`: Khách hoàn trả hàng tại cửa hàng (`sr_returned_date_sk`, `sr_return_amt`, `sr_net_loss`...).
   - `web_returns`: Hoàn trả đơn hàng online (`wr_returned_date_sk`, `wr_return_amt`, `wr_net_loss`...).
   - `catalog_returns`: Hoàn trả đơn qua catalog (`cr_returned_date_sk`, `cr_return_amount`, `cr_net_loss`...).
3. **Fact Tồn kho (Inventory Fact)**:
   - `inventory`: Kiểm kê hàng lưu kho định kỳ (`inv_date_sk`, `inv_item_sk`, `inv_warehouse_sk`, `inv_quantity_on_hand`).
4. **Dimension Khách hàng & Nhân khẩu học (Snowflake Customer Hierarchy)**:
   - `customer`: Khách hàng trung tâm (`c_customer_sk`, `c_customer_id`, `c_first_name`, `c_last_name`, `c_preferred_cust_flag`...).
   - `customer_address`: Địa chỉ cư trú (`ca_address_sk`, `ca_state`, `ca_city`, `ca_county`, `ca_country`...).
   - `customer_demographics`: Đặc tính nhân khẩu học cá nhân (`cd_demo_sk`, `cd_gender`, `cd_marital_status`, `cd_education_status`, `cd_credit_rating`...).
   - `household_demographics`: Nhân khẩu học hộ gia đình (`hd_demo_sk`, `hd_income_band_sk`, `hd_buy_potential`, `hd_vehicle_count`...).
   - `income_band`: Khung thu nhập hàng năm (`ib_income_band_sk`, `ib_lower_bound`, `ib_upper_bound`).
5. **Dimension Sản phẩm, Thời gian & Vận hành**:
   - `item`: Danh mục sản phẩm (`i_item_sk`, `i_item_id`, `i_item_desc`, `i_category`, `i_class`, `i_brand`, `i_current_price`...).
   - `date_dim`: Chi tiết ngày/tháng/năm/quý (`d_date_sk`, `d_year`, `d_moy`, `d_quarter_name`, `d_date`...).
   - `time_dim`: Giờ/phút/ca làm việc (`t_time_sk`, `t_hour`, `t_minute`, `t_am_pm`, `t_shift`...).
   - `promotion`: Chương trình khuyến mãi & coupon (`p_promo_sk`, `p_promo_name`, `p_channel_email`, `p_discount_active`...).
   - `reason`: Lý do hoàn trả hàng (`r_reason_sk`, `r_reason_desc`).
   - `ship_mode`: Phương thức vận chuyển (`sm_ship_mode_sk`, `sm_type`, `sm_carrier`, `sm_code`).
   - `warehouse`: Trung tâm hoàn tất đơn & nhà kho (`w_warehouse_sk`, `w_warehouse_name`, `w_state`, `w_sq_ft`...).
6. **Dimension Kênh bán hàng (Channel Entities)**:
   - `store`: Cửa hàng thực tế (`s_store_sk`, `s_store_name`, `s_state`, `s_market_manager`...).
   - `call_center`: Tổng đài hỗ trợ bán catalog (`cc_call_center_sk`, `cc_name`, `cc_class`...).
   - `catalog_page`: Trang ấn phẩm danh mục (`cp_catalog_page_sk`, `cp_department`, `cp_page_number`...).
   - `web_site`: Cổng thương mại điện tử (`web_site_sk`, `web_name`, `web_company_name`...).
   - `web_page`: Trang web cụ thể (`wp_web_page_sk`, `wp_url`, `wp_type`...).

---

## 2. BA QUY TẮC VÀNG BẮT BUỘC SINH SQL TRÊN TPC-DS (GOLDEN SQL RULES)

### Quy Tắc 1: Bắt buộc JOIN với `date_dim` khi lọc thời gian
- **Thực tế cơ sở dữ liệu**: Các bảng Fact (`store_sales`, `web_sales`, `inventory`...) **KHÔNG CÓ CỘT DATE**. Thời gian được lưu dưới dạng khóa ngoại nguyên (`ss_sold_date_sk`, `ws_sold_date_sk`, `inv_date_sk`...).
- **Quy tắc**: Khi câu hỏi có yếu tố thời gian (năm 2001, quý 2, tháng 8), **BẮT BUỘC JOIN với `date_dim`**:
  ```sql
  -- CHÍNH XÁC:
  SELECT i.i_category, SUM(ss.ss_net_paid) AS total_revenue
  FROM store_sales ss
  JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk
  JOIN item i ON ss.ss_item_sk = i.i_item_sk
  WHERE d.d_year = 2001 AND d.d_moy = 8
  GROUP BY i.i_category;

  -- TUYỆT ĐỐI KHÔNG VIẾT (Sẽ lập tức báo lỗi cột không tồn tại):
  SELECT ... FROM store_sales WHERE ss_sold_date = '2001-08-01';
  ```

### Quy Tắc 2: Điều hướng kênh bán hàng chính xác (Channel Routing)
- "Doanh số bán lẻ / tại quầy / tại cửa hàng" $\to$ Bảng `store_sales`.
- "Doanh số trực tuyến / trên website / online" $\to$ Bảng `web_sales`.
- "Doanh số qua danh mục / qua bưu điện / catalog" $\to$ Bảng `catalog_sales`.
- "Đổi trả tại quầy" $\to$ `store_returns`; "Đổi trả trực tuyến" $\to$ `web_returns`.
- Khi câu hỏi yêu cầu **"Tổng doanh thu toàn công ty / đa kênh"** $\to$ Bắt buộc kết hợp cả 3 kênh bán (`store_sales`, `web_sales`, `catalog_sales`) thông qua phép `UNION ALL` hoặc biểu thức cộng `COALESCE`:
  ```sql
  SELECT
      COALESCE(s.store_rev, 0) + COALESCE(w.web_rev, 0) + COALESCE(c.catalog_rev, 0) AS total_company_revenue
  FROM
      (SELECT SUM(ss_net_paid) AS store_rev FROM store_sales JOIN date_dim ON ss_sold_date_sk = d_date_sk WHERE d_year = 2001) s,
      (SELECT SUM(ws_net_paid) AS web_rev FROM web_sales JOIN date_dim ON ws_sold_date_sk = d_date_sk WHERE d_year = 2001) w,
      (SELECT SUM(cs_net_paid) AS catalog_rev FROM catalog_sales JOIN date_dim ON cs_sold_date_sk = d_date_sk WHERE d_year = 2001) c;
  ```

### Quy Tắc 3: Phân cấp Snowflake Hierarchy cho Khách hàng & Địa chỉ
- Khách hàng không lưu trực tiếp địa chỉ bang/thành phố trong `customer`.
- Phải nối qua bảng cầu nối `customer_address`:
  ```sql
  FROM customer c
  JOIN customer_address ca ON c.c_current_addr_sk = ca.ca_address_sk
  WHERE ca.ca_state = 'CA'
  ```
- Nối qua đặc tính nhân khẩu học (giới tính, hôn nhân):
  ```sql
  FROM customer c
  JOIN customer_demographics cd ON c.c_current_cdemo_sk = cd.cd_demo_sk
  WHERE cd.cd_gender = 'M' AND cd.cd_marital_status = 'M'
  ```

---

## 3. Công Thức Chỉ Số Đo Lường Nghiệp Vụ Chuẩn (dbt Semantic Metrics)

| Chỉ số (Metric) | Công thức SQL chuẩn | Ý nghĩa nghiệp vụ | Bảng bắt buộc |
| :--- | :--- | :--- | :--- |
| **Doanh thu thuần cửa hàng (`store_net_sales`)** | `SUM(ss_net_paid)` | Tiền thực nhận sau chiết khấu tại quầy | `store_sales` |
| **Doanh thu thuần trực tuyến (`web_net_sales`)** | `SUM(ws_net_paid)` | Doanh thu thực nhận sau chiết khấu online | `web_sales` |
| **Doanh thu thuần catalog (`catalog_net_sales`)** | `SUM(cs_net_paid)` | Doanh thu qua đặt hàng bưu điện | `catalog_sales` |
| **Tổng doanh thu thuần (`total_net_sales`)** | `COALESCE(SUM(ss_net_paid), 0) + COALESCE(SUM(ws_net_paid), 0) + COALESCE(SUM(cs_net_paid), 0)` | Doanh thu toàn công ty trên cả 3 kênh bán | Cả 3 Fact sales |
| **Doanh thu gộp (`gross_sales`)** | `SUM(ss_ext_sales_price)` | Tổng giá trị hàng bán theo đơn giá niêm yết | `store_sales` |
| **Lợi nhuận ròng cửa hàng (`net_profit`)** | `SUM(ss_net_profit)` | Tiền thực thu trừ tổng giá vốn nhập kho | `store_sales` |
| **Tổng tiền đổi trả cửa hàng (`store_returns_amt`)** | `SUM(sr_return_amt)` | Tổng giá trị hàng hóa khách trả lại tại quầy | `store_returns` |
| **Số lượng tồn kho (`inventory_quantity`)** | `SUM(inv_quantity_on_hand)` | Khối lượng hàng sẵn sàng xuất tại kho | `inventory` |

---

## 4. Từ Điển Giá Trị Danh Mục Phân Loại (Categorical Values Dictionary)

### A. Ngành hàng sản phẩm (`item.i_category`)
- "Điện tử", "thiết bị số", "công nghệ" $\to$ `'Electronics'`
- "Thời trang nữ", "quần áo nữ" $\to$ `'Women'`
- "Thời trang nam", "nam giới" $\to$ `'Men'`
- "Đồ gia dụng", "nội thất", "nhà cửa" $\to$ `'Home'`
- "Trẻ em", "đồ chơi trẻ em" $\to$ `'Children'`
- "Thể thao", "dụng cụ thể thao" $\to$ `'Sports'`
- "Sách", "ấn phẩm" $\to$ `'Books'`
- "Giày dép" $\to$ `'Shoes'`
- "Âm nhạc", "đĩa nhạc" $\to$ `'Music'`
- "Trang sức", "vàng bạc đá quý" $\to$ `'Jewelry'`

### B. Giới tính & Hôn nhân (`customer_demographics`)
- "Nam", "nam giới", "đàn ông" $\to$ `cd_gender = 'M'`
- "Nữ", "phụ nữ", "chị em" $\to$ `cd_gender = 'F'`
- "Đã kết hôn", "có gia đình" $\to$ `cd_marital_status = 'M'`
- "Độc thân", "chưa kết hôn" $\to$ `cd_marital_status = 'S'`
- "Ly hôn", "ly dị" $\to$ `cd_marital_status = 'D'`
- "Góa bụa" $\to$ `cd_marital_status = 'W'`

### C. Phương thức vận chuyển (`ship_mode.sm_type`)
- "Hỏa tốc", "giao nhanh" $\to$ `'EXPRESS'`
- "Giao qua đêm", "nhận hôm sau" $\to$ `'OVERNIGHT'`
- "Tiêu chuẩn", "thông thường" $\to$ `'REGULAR'`
- "Hàng không", "máy bay" $\to$ `'AIR'`

### D. Tiểu bang Hoa Kỳ (`customer_address.ca_state`)
- "California" $\to$ `'CA'`, "Texas" $\to$ `'TX'`, "New York" $\to$ `'NY'`, "Florida" $\to$ `'FL'`, "Illinois" $\to$ `'IL'`, "Washington" $\to$ `'WA'`.

---

## 5. Mẫu Truy Vấn JOIN Điển Hình Chuẩn DuckDB (Golden Join Patterns)

### 1. Doanh thu theo Ngành hàng trong Năm 2001 (Store Sales + date_dim + item):
```sql
SELECT
    i.i_category,
    COUNT(DISTINCT ss.ss_ticket_number) AS total_orders,
    SUM(ss.ss_quantity) AS units_sold,
    ROUND(SUM(ss.ss_net_paid), 2) AS net_revenue
FROM store_sales ss
JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk
JOIN item i ON ss.ss_item_sk = i.i_item_sk
WHERE d.d_year = 2001
GROUP BY i.i_category
ORDER BY net_revenue DESC;
```

### 2. So sánh Doanh số Bán lẻ tại Quầy và Doanh số Trực tuyến theo Tháng năm 2002:
```sql
WITH store_monthly AS (
    SELECT d.d_moy AS month_num, SUM(ss.ss_net_paid) AS store_revenue
    FROM store_sales ss
    JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk
    WHERE d.d_year = 2002
    GROUP BY d.d_moy
),
web_monthly AS (
    SELECT d.d_moy AS month_num, SUM(ws.ws_net_paid) AS web_revenue
    FROM web_sales ws
    JOIN date_dim d ON ws.ws_sold_date_sk = d.d_date_sk
    WHERE d.d_year = 2002
    GROUP BY d.d_moy
)
SELECT
    COALESCE(s.month_num, w.month_num) AS month_num,
    ROUND(COALESCE(s.store_revenue, 0), 2) AS store_revenue,
    ROUND(COALESCE(w.web_revenue, 0), 2) AS web_revenue,
    ROUND(COALESCE(s.store_revenue, 0) + COALESCE(w.web_revenue, 0), 2) AS total_revenue
FROM store_monthly s
FULL OUTER JOIN web_monthly w ON s.month_num = w.month_num
ORDER BY month_num;
```

### 3. Top 10 Khách hàng Chi tiêu nhiều nhất tại Bang California (Snowflake Join):
```sql
SELECT
    c.c_customer_sk,
    c.c_first_name,
    c.c_last_name,
    ca.ca_state,
    ROUND(SUM(ss.ss_net_paid), 2) AS total_spent
FROM store_sales ss
JOIN customer c ON ss.ss_customer_sk = c.c_customer_sk
JOIN customer_address ca ON c.c_current_addr_sk = ca.ca_address_sk
WHERE ca.ca_state = 'CA'
GROUP BY c.c_customer_sk, c.c_first_name, c.c_last_name, ca.ca_state
ORDER BY total_spent DESC
LIMIT 10;
```
