---
name: tpch-analytics
description: Business rules, semantic metrics formulas, categorical values dictionary, and relational join patterns for the TPC-H decision support benchmark schema.
metadata:
  domain: enterprise-supply-chain-analytics
  dataset: tpch-benchmark
---

# TPC-H Enterprise Analytics Domain Skill

Kỹ năng này cung cấp toàn bộ từ điển nghiệp vụ, công thức chỉ số tài chính (Semantic Metrics Layer) và quan hệ dữ liệu của chuẩn phân phối & chuỗi cung ứng **TPC-H (8 bảng)**.

## 1. Danh Mục 8 Bảng & Quan Hệ Khóa (Schema Relations)

```
[region] 1 --- * [nation] 1 --- * [supplier] 1 --- * [partsupp] * --- 1 [part]
                    |                                     |
                    + --- * [customer] 1 --- * [orders] 1 --- * [lineitem]
```

- **`region`** (`r_regionkey`, `r_name`, `r_comment`): 5 đại lục chính (`AFRICA`, `AMERICA`, `ASIA`, `EUROPE`, `MIDDLE EAST`).
- **`nation`** (`n_nationkey`, `n_name`, `n_regionkey`): 25 quốc gia thuộc 5 đại lục.
- **`customer`** (`c_custkey`, `c_name`, `c_address`, `c_nationkey`, `c_phone`, `c_acctbal`, `c_mktsegment`): Khách hàng doanh nghiệp.
- **`orders`** (`o_orderkey`, `o_custkey`, `o_orderstatus`, `o_totalprice`, `o_orderdate`, `o_orderpriority`, `o_clerk`, `o_shippriority`): Đơn đặt hàng (từ năm 1992 đến 1998).
- **`lineitem`** (`l_orderkey`, `l_partkey`, `l_suppkey`, `l_linenumber`, `l_quantity`, `l_extendedprice`, `l_discount`, `l_tax`, `l_returnflag`, `l_linestatus`, `l_shipdate`, `l_commitdate`, `l_receiptdate`, `l_shipinstruct`, `l_shipmode`): Chi tiết từng mặt hàng trong đơn hàng (bảng lớn nhất).
- **`part`** (`p_partkey`, `p_name`, `p_mfgr`, `p_brand`, `p_type`, `p_size`, `p_container`, `p_retailprice`): Danh mục linh kiện/hàng hóa.
- **`supplier`** (`s_suppkey`, `s_name`, `s_address`, `s_nationkey`, `s_phone`, `s_acctbal`): Nhà cung cấp hàng hóa.
- **`partsupp`** (`ps_partkey`, `ps_suppkey`, `ps_availqty`, `ps_supplycost`): Liên kết nguồn cung và giá vốn hàng tồn kho.

---

## 2. Công Thức Chỉ Số Đo Lường Nghiệp Vụ (Semantic Metrics)

Khi người dùng hỏi về các chỉ số tài chính, **bắt buộc tuân thủ đúng công thức chuẩn**, tuyệt đối không tự chế:

| Chỉ số (Metric) | Công thức SQL chuẩn | Ý nghĩa nghiệp vụ |
| :--- | :--- | :--- |
| **Doanh thu thuần (Net Revenue)** | `SUM(l_extendedprice * (1 - l_discount))` | Doanh thu thực tế sau khi đã trừ chiết khấu cho khách hàng. |
| **Doanh thu gộp (Gross Revenue)** | `SUM(l_extendedprice)` | Tổng giá trị hàng bán trước chiết khấu và thuế. |
| **Tổng tiền chiết khấu (Discount Amount)** | `SUM(l_extendedprice * l_discount)` | Tổng số tiền giảm giá ưu đãi. |
| **Doanh thu có thuế (Taxed Revenue)** | `SUM(l_extendedprice * (1 - l_discount) * (1 + l_tax))` | Doanh thu thực nhận sau chiết khấu và cộng thuế VAT/thuế nhập khẩu. |
| **Giá vốn bán hàng (Cost of Goods Sold)** | `SUM(ps_supplycost * l_quantity)` | Chi phí nhập hàng từ nhà cung cấp (khi JOIN với `partsupp`). |
| **Tổng lượng đặt hàng (Total Volume)** | `SUM(l_quantity)` | Tổng số lượng đơn vị sản phẩm được xuất kho. |
| **Số lượng đơn hàng (Order Count)** | `COUNT(DISTINCT o_orderkey)` | Số đơn hàng phát sinh trong kỳ. |

---

## 3. Từ Điển Giá Trị Danh Mục (Categorical Values Dictionary)

Ánh xạ các từ khóa tiếng Việt tự nhiên sang giá trị thực tế trong cơ sở dữ liệu:

### A. Phân khúc thị trường (`customer.c_mktsegment`)
- "Ô tô", "xe hơi", "phương tiện" $\rightarrow$ `'AUTOMOBILE'`
- "Xây dựng", "công trình", "nhà ở" $\rightarrow$ `'BUILDING'`
- "Nội thất", "bàn ghế", "gia dụng gỗ" $\rightarrow$ `'FURNITURE'`
- "Gia dụng", "đồ dùng gia đình" $\rightarrow$ `'HOUSEHOLD'`
- "Máy móc", "cơ khí", "thiết bị công nghiệp" $\rightarrow$ `'MACHINERY'`

### B. Trạng thái đơn hàng (`orders.o_orderstatus`)
- "Đã hoàn thành", "hoàn tất", "đã giao xong" $\rightarrow$ `'F'` (Fulfilled)
- "Đang mở", "chờ xử lý", "chưa giao" $\rightarrow$ `'O'` (Open)
- "Một phần", "giao dở dang" $\rightarrow$ `'P'` (Partial)

### C. Mức độ ưu tiên đơn hàng (`orders.o_orderpriority`)
- "Khẩn cấp", "gấp nhất" $\rightarrow$ `'1-URGENT'`
- "Ưu tiên cao", "quan trọng" $\rightarrow$ `'2-HIGH'`
- "Trung bình" $\rightarrow$ `'3-MEDIUM'`
- "Không xác định" $\rightarrow$ `'4-NOT SPECIFIED'`
- "Thấp", "không gấp" $\rightarrow$ `'5-LOW'`

### D. Phương thức vận chuyển (`lineitem.l_shipmode`)
- "Đường hàng không" $\rightarrow$ `'AIR'`, `'REG AIR'`
- "Đường biển", "tàu thủy" $\rightarrow$ `'SHIP'`
- "Đường bộ", "xe tải" $\rightarrow$ `'TRUCK'`
- "Đường sắt", "tàu hỏa" $\rightarrow$ `'RAIL'`
- "Bưu điện" $\rightarrow$ `'MAIL'`
- "Giao tại mạn tàu" $\rightarrow$ `'FOB'`

### E. Cờ đổi trả hàng (`lineitem.l_returnflag`)
- "Đã trả lại", "hoàn hàng" $\rightarrow$ `'R'` (Returned)
- "Đã chấp nhận", "hàng tốt" $\rightarrow$ `'A'` (Accepted)
- "Bình thường", "không đổi trả" $\rightarrow$ `'N'` (None)

---

## 4. Các Mẫu Truy Vấn JOIN Điển Hình (Golden Join Patterns)

1. **Doanh thu theo Khách hàng và Quốc gia**:
   ```sql
   SELECT c.c_name, n.n_name, r.r_name, SUM(l.l_extendedprice * (1 - l.l_discount)) AS net_revenue
   FROM customer c
   JOIN orders o ON c.c_custkey = o.o_custkey
   JOIN lineitem l ON o.o_orderkey = l.l_orderkey
   JOIN nation n ON c.c_nationkey = n.n_nationkey
   JOIN region r ON n.n_regionkey = r.r_regionkey
   GROUP BY c.c_name, n.n_name, r.r_name
   ```

2. **Hiệu suất Nhà cung cấp & Doanh thu theo Nhà phân phối**:
   ```sql
   SELECT s.s_name, n.n_name, SUM(l.l_extendedprice * (1 - l.l_discount)) AS revenue
   FROM supplier s
   JOIN lineitem l ON s.s_suppkey = l.l_suppkey
   JOIN nation n ON s.s_nationkey = n.n_nationkey
   GROUP BY s.s_name, n.n_name
   ```
