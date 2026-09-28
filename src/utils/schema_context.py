"""Từ điển lược đồ dữ liệu ngữ nghĩa & tầng chỉ số nghiệp vụ (Semantic Schema & Metric Layer).

Component 2.1:
- Định nghĩa DDL chi tiết 24 bảng TPC-DS có kèm chú thích tiếng Việt cho từng cột.
- Từ điển quan hệ khóa ngoại (Foreign Key) và quy tắc JOIN chuẩn (Snowflake / Star Schema).
- Định nghĩa các công thức tính toán chỉ số nghiệp vụ chuẩn (dbt Semantic Metrics Layer).
- Hàm kết xuất Markdown Schema Context phục vụ việc xây dựng prompt cho SQL Generator.
"""

from dataclasses import dataclass
from typing import Final

# Danh sách 24 bảng nghiệp vụ TPC-DS (Omnichannel Retail & Supply Chain)
TPCDS_TABLE_NAMES: Final[list[str]] = [
    # Fact & Returns (7 bảng)
    "store_sales",
    "store_returns",
    "catalog_sales",
    "catalog_returns",
    "web_sales",
    "web_returns",
    "inventory",
    # Core Dimensions (5 bảng)
    "item",
    "customer",
    "customer_address",
    "customer_demographics",
    "date_dim",
    # Demographic & Auxiliary Dimensions (7 bảng)
    "household_demographics",
    "income_band",
    "promotion",
    "reason",
    "ship_mode",
    "time_dim",
    "warehouse",
    # Channel Dimensions (5 bảng)
    "store",
    "call_center",
    "catalog_page",
    "web_page",
    "web_site",
]

# Danh sách 8 bảng nghiệp vụ TPC-H (giữ lại phục vụ tương thích ngược cho các module chưa chuyển đổi)
TPCH_TABLE_NAMES: Final[list[str]] = [
    "region",
    "nation",
    "supplier",
    "customer",
    "part",
    "partsupp",
    "orders",
    "lineitem",
]


@dataclass(frozen=True)
class JoinRelationship:
    """Mô tả quan hệ JOIN chuẩn giữa hai bảng trong TPC-DS."""

    from_table: str
    to_table: str
    condition: str
    description: str


@dataclass(frozen=True)
class SemanticMetric:
    """Mô tả chỉ số nghiệp vụ chuẩn hóa (dbt Semantic Metric)."""

    metric_id: str
    vietnamese_name: str
    formula: str
    description: str
    required_tables: list[str]


# ==============================================================================
# 1. DDL CHI TIẾT 24 BẢNG TPC-DS KÈM CHÚ THÍCH TIẾNG VIỆT
# ==============================================================================

TPCDS_TABLE_SCHEMAS: Final[dict[str, str]] = {
    # -------------------------------------------------------------------------
    # 1. store_sales (Fact Bán hàng tại cửa hàng)
    # -------------------------------------------------------------------------
    "store_sales": """\
-- BẢNG: store_sales (Fact: Giao dịch bán lẻ trực tiếp tại cửa hàng)
CREATE TABLE store_sales (
    ss_sold_date_sk INTEGER,          -- Khóa ngoại tham chiếu date_dim(d_date_sk) - BẮT BUỘC JOIN để lọc ngày/tháng/năm
    ss_sold_time_sk INTEGER,          -- Khóa ngoại tham chiếu time_dim(t_time_sk)
    ss_item_sk INTEGER NOT NULL,      -- Khóa ngoại tham chiếu item(i_item_sk)
    ss_customer_sk INTEGER,          -- Khóa ngoại tham chiếu customer(c_customer_sk)
    ss_cdemo_sk INTEGER,             -- Khóa ngoại tham chiếu customer_demographics(cd_demo_sk)
    ss_hdemo_sk INTEGER,             -- Khóa ngoại tham chiếu household_demographics(hd_demo_sk)
    ss_addr_sk INTEGER,              -- Khóa ngoại tham chiếu customer_address(ca_address_sk)
    ss_store_sk INTEGER,             -- Khóa ngoại tham chiếu store(s_store_sk)
    ss_promo_sk INTEGER,             -- Khóa ngoại tham chiếu promotion(p_promo_sk)
    ss_ticket_number BIGINT NOT NULL, -- Số vé / hóa đơn thanh toán tại quầy
    ss_quantity INTEGER,             -- Số lượng sản phẩm mua
    ss_wholesale_cost DECIMAL(7,2),  -- Giá vốn bán buôn
    ss_list_price DECIMAL(7,2),       -- Giá niêm yết
    ss_sales_price DECIMAL(7,2),      -- Đơn giá bán thực tế cho 1 đơn vị
    ss_ext_discount_amt DECIMAL(7,2), -- Tổng tiền chiết khấu được giảm
    ss_ext_sales_price DECIMAL(7,2),  -- Tổng tiền bán = ss_quantity * ss_sales_price (Doanh thu gộp)
    ss_ext_wholesale_cost DECIMAL(7,2), -- Tổng giá vốn nhập kho
    ss_ext_list_price DECIMAL(7,2),   -- Tổng giá trị theo giá niêm yết
    ss_ext_tax DECIMAL(7,2),          -- Thuế VAT
    ss_coupon_amt DECIMAL(7,2),       -- Tiền giảm qua coupon khuyến mãi
    ss_net_paid DECIMAL(7,2),         -- Tiền thực thu từ khách chưa thuế (Doanh thu thuần)
    ss_net_paid_inc_tax DECIMAL(7,2), -- Tiền thực thu bao gồm thuế
    ss_net_profit DECIMAL(7,2),       -- Lợi nhuận ròng = ss_net_paid - ss_ext_wholesale_cost
    PRIMARY KEY (ss_item_sk, ss_ticket_number)
);""",
    # -------------------------------------------------------------------------
    # 2. store_returns (Fact Đổi trả hàng tại cửa hàng)
    # -------------------------------------------------------------------------
    "store_returns": """\
-- BẢNG: store_returns (Fact: Giao dịch hoàn trả hàng mua tại cửa hàng)
CREATE TABLE store_returns (
    sr_returned_date_sk INTEGER,      -- Khóa ngoại tham chiếu date_dim(d_date_sk)
    sr_return_time_sk INTEGER,        -- Khóa ngoại tham chiếu time_dim(t_time_sk)
    sr_item_sk INTEGER NOT NULL,      -- Khóa ngoại tham chiếu item(i_item_sk)
    sr_customer_sk INTEGER,          -- Khóa ngoại tham chiếu customer(c_customer_sk)
    sr_cdemo_sk INTEGER,             -- Khóa ngoại tham chiếu customer_demographics(cd_demo_sk)
    sr_hdemo_sk INTEGER,             -- Khóa ngoại tham chiếu household_demographics(hd_demo_sk)
    sr_addr_sk INTEGER,              -- Khóa ngoại tham chiếu customer_address(ca_address_sk)
    sr_store_sk INTEGER,             -- Khóa ngoại tham chiếu store(s_store_sk)
    sr_reason_sk INTEGER,            -- Khóa ngoại tham chiếu reason(r_reason_sk) - Lý do trả hàng
    sr_ticket_number BIGINT NOT NULL, -- Số vé / hóa đơn gốc
    sr_return_quantity INTEGER,      -- Số lượng sản phẩm trả lại
    sr_return_amt DECIMAL(7,2),       -- Tổng số tiền hoàn trả lại cho khách
    sr_return_tax DECIMAL(7,2),       -- Thuế hoàn lại
    sr_return_amt_inc_tax DECIMAL(7,2), -- Tổng tiền hoàn trả gồm thuế
    sr_fee DECIMAL(7,2),              -- Phí xử lý đổi trả
    sr_return_ship_cost DECIMAL(7,2), -- Chi phí vận chuyển hoàn hàng
    sr_refunded_cash DECIMAL(7,2),    -- Tiền mặt hoàn trả
    sr_reversed_charge DECIMAL(7,2),  -- Tiền hoàn qua thẻ ngân hàng
    sr_store_credit DECIMAL(7,2),     -- Điểm tích lũy / phiếu mua hàng bù lại
    sr_net_loss DECIMAL(7,2),         -- Tổn thất ròng của doanh nghiệp do đổi trả
    PRIMARY KEY (sr_item_sk, sr_ticket_number)
);""",
    # -------------------------------------------------------------------------
    # 3. web_sales (Fact Bán hàng trực tuyến / Online)
    # -------------------------------------------------------------------------
    "web_sales": """\
-- BẢNG: web_sales (Fact: Giao dịch bán hàng qua website / thương mại điện tử)
CREATE TABLE web_sales (
    ws_sold_date_sk INTEGER,          -- Khóa ngoại tham chiếu date_dim(d_date_sk) - BẮT BUỘC JOIN để lọc ngày
    ws_sold_time_sk INTEGER,          -- Khóa ngoại tham chiếu time_dim(t_time_sk)
    ws_ship_date_sk INTEGER,          -- Khóa ngoại tham chiếu date_dim(d_date_sk) - Ngày giao hàng
    ws_item_sk INTEGER NOT NULL,      -- Khóa ngoại tham chiếu item(i_item_sk)
    ws_bill_customer_sk INTEGER,      -- Khóa ngoại tham chiếu customer(c_customer_sk) - Khách thanh toán
    ws_bill_cdemo_sk INTEGER,         -- Khóa ngoại tham chiếu customer_demographics(cd_demo_sk)
    ws_bill_hdemo_sk INTEGER,         -- Khóa ngoại tham chiếu household_demographics(hd_demo_sk)
    ws_bill_addr_sk INTEGER,          -- Khóa ngoại tham chiếu customer_address(ca_address_sk) - Địa chỉ thanh toán
    ws_ship_customer_sk INTEGER,      -- Khóa ngoại tham chiếu customer(c_customer_sk) - Người nhận
    ws_ship_cdemo_sk INTEGER,
    ws_ship_hdemo_sk INTEGER,
    ws_ship_addr_sk INTEGER,          -- Khóa ngoại tham chiếu customer_address(ca_address_sk) - Địa chỉ giao hàng
    ws_web_page_sk INTEGER,           -- Khóa ngoại tham chiếu web_page(wp_web_page_sk) - Trang web phát sinh đơn
    ws_web_site_sk INTEGER,           -- Khóa ngoại tham chiếu web_site(web_site_sk) - Website bán hàng
    ws_ship_mode_sk INTEGER,          -- Khóa ngoại tham chiếu ship_mode(sm_ship_mode_sk)
    ws_warehouse_sk INTEGER,          -- Khóa ngoại tham chiếu warehouse(w_warehouse_sk) - Kho xuất hàng
    ws_promo_sk INTEGER,              -- Khóa ngoại tham chiếu promotion(p_promo_sk)
    ws_order_number BIGINT NOT NULL,  -- Mã số đơn hàng online
    ws_quantity INTEGER,              -- Số lượng đặt mua
    ws_wholesale_cost DECIMAL(7,2),
    ws_list_price DECIMAL(7,2),
    ws_sales_price DECIMAL(7,2),
    ws_ext_discount_amt DECIMAL(7,2),
    ws_ext_sales_price DECIMAL(7,2),   -- Doanh thu gộp
    ws_ext_wholesale_cost DECIMAL(7,2),
    ws_ext_list_price DECIMAL(7,2),
    ws_ext_tax DECIMAL(7,2),
    ws_coupon_amt DECIMAL(7,2),
    ws_ext_ship_cost DECIMAL(7,2),    -- Phí giao hàng
    ws_net_paid DECIMAL(7,2),         -- Tiền thực thu từ khách (Doanh thu thuần)
    ws_net_paid_inc_tax DECIMAL(7,2),
    ws_net_paid_inc_ship DECIMAL(7,2),
    ws_net_paid_inc_ship_tax DECIMAL(7,2),
    ws_net_profit DECIMAL(7,2),       -- Lợi nhuận ròng
    PRIMARY KEY (ws_item_sk, ws_order_number)
);""",
    # -------------------------------------------------------------------------
    # 4. web_returns (Fact Đổi trả hàng trực tuyến)
    # -------------------------------------------------------------------------
    "web_returns": """\
-- BẢNG: web_returns (Fact: Giao dịch đổi trả hàng mua qua website)
CREATE TABLE web_returns (
    wr_returned_date_sk INTEGER,      -- Khóa ngoại tham chiếu date_dim(d_date_sk)
    wr_returned_time_sk INTEGER,      -- Khóa ngoại tham chiếu time_dim(t_time_sk)
    wr_item_sk INTEGER NOT NULL,      -- Khóa ngoại tham chiếu item(i_item_sk)
    wr_refunded_customer_sk INTEGER,  -- Khách nhận hoàn tiền
    wr_refunded_cdemo_sk INTEGER,
    wr_refunded_hdemo_sk INTEGER,
    wr_refunded_addr_sk INTEGER,
    wr_returning_customer_sk INTEGER, -- Khách gửi hàng hoàn
    wr_returning_cdemo_sk INTEGER,
    wr_returning_hdemo_sk INTEGER,
    wr_returning_addr_sk INTEGER,
    wr_web_page_sk INTEGER,           -- Trang web xử lý đổi trả
    wr_reason_sk INTEGER,             -- Khóa ngoại tham chiếu reason(r_reason_sk)
    wr_order_number BIGINT NOT NULL,  -- Mã đơn hàng online gốc
    wr_return_quantity INTEGER,       -- Số lượng hàng trả lại
    wr_return_amt DECIMAL(7,2),        -- Tiền hoàn trả khách
    wr_return_tax DECIMAL(7,2),
    wr_return_amt_inc_tax DECIMAL(7,2),
    wr_fee DECIMAL(7,2),
    wr_return_ship_cost DECIMAL(7,2),
    wr_refunded_cash DECIMAL(7,2),
    wr_reversed_charge DECIMAL(7,2),
    wr_account_credit DECIMAL(7,2),
    wr_net_loss DECIMAL(7,2),         -- Thiệt hại ròng của công ty
    PRIMARY KEY (wr_item_sk, wr_order_number)
);""",
    # -------------------------------------------------------------------------
    # 5. catalog_sales (Fact Bán hàng qua danh mục / bưu điện)
    # -------------------------------------------------------------------------
    "catalog_sales": """\
-- BẢNG: catalog_sales (Fact: Giao dịch bán hàng qua danh mục ấn phẩm / catalog / bưu điện)
CREATE TABLE catalog_sales (
    cs_sold_date_sk INTEGER,          -- Khóa ngoại tham chiếu date_dim(d_date_sk)
    cs_sold_time_sk INTEGER,          -- Khóa ngoại tham chiếu time_dim(t_time_sk)
    cs_ship_date_sk INTEGER,          -- Khóa ngoại tham chiếu date_dim(d_date_sk)
    cs_bill_customer_sk INTEGER,      -- Khóa ngoại tham chiếu customer(c_customer_sk)
    cs_bill_cdemo_sk INTEGER,
    cs_bill_hdemo_sk INTEGER,
    cs_bill_addr_sk INTEGER,          -- Khóa ngoại tham chiếu customer_address(ca_address_sk)
    cs_ship_customer_sk INTEGER,
    cs_ship_cdemo_sk INTEGER,
    cs_ship_hdemo_sk INTEGER,
    cs_ship_addr_sk INTEGER,
    cs_call_center_sk INTEGER,        -- Khóa ngoại tham chiếu call_center(cc_call_center_sk) - Tổng đài nhận đơn
    cs_catalog_page_sk INTEGER,       -- Khóa ngoại tham chiếu catalog_page(cp_catalog_page_sk) - Trang catalog
    cs_ship_mode_sk INTEGER,          -- Khóa ngoại tham chiếu ship_mode(sm_ship_mode_sk)
    cs_warehouse_sk INTEGER,          -- Khóa ngoại tham chiếu warehouse(w_warehouse_sk)
    cs_item_sk INTEGER NOT NULL,      -- Khóa ngoại tham chiếu item(i_item_sk)
    cs_promo_sk INTEGER,              -- Khóa ngoại tham chiếu promotion(p_promo_sk)
    cs_order_number BIGINT NOT NULL,  -- Số đơn hàng catalog
    cs_quantity INTEGER,
    cs_wholesale_cost DECIMAL(7,2),
    cs_list_price DECIMAL(7,2),
    cs_sales_price DECIMAL(7,2),
    cs_ext_discount_amt DECIMAL(7,2),
    cs_ext_sales_price DECIMAL(7,2),   -- Doanh thu gộp
    cs_ext_wholesale_cost DECIMAL(7,2),
    cs_ext_list_price DECIMAL(7,2),
    cs_ext_tax DECIMAL(7,2),
    cs_coupon_amt DECIMAL(7,2),
    cs_ext_ship_cost DECIMAL(7,2),
    cs_net_paid DECIMAL(7,2),         -- Tiền thực thu (Doanh thu thuần)
    cs_net_paid_inc_tax DECIMAL(7,2),
    cs_net_paid_inc_ship DECIMAL(7,2),
    cs_net_paid_inc_ship_tax DECIMAL(7,2),
    cs_net_profit DECIMAL(7,2),       -- Lợi nhuận ròng
    PRIMARY KEY (cs_item_sk, cs_order_number)
);""",
    # -------------------------------------------------------------------------
    # 6. catalog_returns (Fact Đổi trả hàng catalog)
    # -------------------------------------------------------------------------
    "catalog_returns": """\
-- BẢNG: catalog_returns (Fact: Giao dịch đổi trả hàng mua qua danh mục)
CREATE TABLE catalog_returns (
    cr_returned_date_sk INTEGER,      -- Khóa ngoại tham chiếu date_dim(d_date_sk)
    cr_returned_time_sk INTEGER,      -- Khóa ngoại tham chiếu time_dim(t_time_sk)
    cr_item_sk INTEGER NOT NULL,      -- Khóa ngoại tham chiếu item(i_item_sk)
    cr_refunded_customer_sk INTEGER,
    cr_refunded_cdemo_sk INTEGER,
    cr_refunded_hdemo_sk INTEGER,
    cr_refunded_addr_sk INTEGER,
    cr_returning_customer_sk INTEGER,
    cr_returning_cdemo_sk INTEGER,
    cr_returning_hdemo_sk INTEGER,
    cr_returning_addr_sk INTEGER,
    cr_call_center_sk INTEGER,        -- Khóa ngoại tham chiếu call_center(cc_call_center_sk)
    cr_catalog_page_sk INTEGER,       -- Khóa ngoại tham chiếu catalog_page(cp_catalog_page_sk)
    cr_ship_mode_sk INTEGER,          -- Khóa ngoại tham chiếu ship_mode(sm_ship_mode_sk)
    cr_warehouse_sk INTEGER,          -- Khóa ngoại tham chiếu warehouse(w_warehouse_sk)
    cr_reason_sk INTEGER,             -- Khóa ngoại tham chiếu reason(r_reason_sk)
    cr_order_number BIGINT NOT NULL,  -- Số đơn hàng catalog gốc
    cr_return_quantity INTEGER,
    cr_return_amount DECIMAL(7,2),    -- Tiền hoàn trả khách
    cr_return_tax DECIMAL(7,2),
    cr_return_amt_inc_tax DECIMAL(7,2),
    cr_fee DECIMAL(7,2),
    cr_return_ship_cost DECIMAL(7,2),
    cr_refunded_cash DECIMAL(7,2),
    cr_reversed_charge DECIMAL(7,2),
    cr_store_credit DECIMAL(7,2),
    cr_net_loss DECIMAL(7,2),
    PRIMARY KEY (cr_item_sk, cr_order_number)
);""",
    # -------------------------------------------------------------------------
    # 7. inventory (Fact Tồn kho định kỳ)
    # -------------------------------------------------------------------------
    "inventory": """\
-- BẢNG: inventory (Fact: Số lượng tồn kho sản phẩm theo tuần tại từng kho)
CREATE TABLE inventory (
    inv_date_sk INTEGER NOT NULL,     -- Khóa ngoại tham chiếu date_dim(d_date_sk)
    inv_item_sk INTEGER NOT NULL,     -- Khóa ngoại tham chiếu item(i_item_sk)
    inv_warehouse_sk INTEGER NOT NULL, -- Khóa ngoại tham chiếu warehouse(w_warehouse_sk)
    inv_quantity_on_hand INTEGER,     -- Số lượng sản phẩm còn tồn trong kho
    PRIMARY KEY (inv_date_sk, inv_item_sk, inv_warehouse_sk)
);""",
    # -------------------------------------------------------------------------
    # 8. item (Dimension Sản phẩm / Hàng hóa)
    # -------------------------------------------------------------------------
    "item": """\
-- BẢNG: item (Dimension: Danh mục hàng hóa và sản phẩm)
CREATE TABLE item (
    i_item_sk INTEGER PRIMARY KEY,    -- Khóa chính thay thế của sản phẩm
    i_item_id VARCHAR(16) NOT NULL,   -- Mã sản phẩm tự nhiên (Item Code)
    i_rec_start_date DATE,
    i_rec_end_date DATE,
    i_item_desc VARCHAR(200),         -- Tên / mô tả chi tiết sản phẩm
    i_current_price DECIMAL(7,2),     -- Giá bán hiện tại
    i_wholesale_cost DECIMAL(7,2),    -- Giá nhập hàng từ nhà cung cấp
    i_brand_id INTEGER,               -- Mã thương hiệu
    i_brand VARCHAR(50),              -- Tên thương hiệu (Brand name)
    i_class_id INTEGER,               -- Mã phân lớp hàng hóa
    i_class VARCHAR(50),              -- Phân lớp sản phẩm (dresses, shirts, audio, computers...)
    i_category_id INTEGER,            -- Mã ngành hàng
    i_category VARCHAR(50),           -- Ngành hàng chính (Home, Electronics, Men, Women, Children, Books, Sports...)
    i_manufact_id INTEGER,            -- Mã nhà sản xuất
    i_manufact VARCHAR(50),           -- Tên hãng sản xuất
    i_size VARCHAR(20),               -- Kích cỡ (S, M, L, XL...)
    i_formulation VARCHAR(20),
    i_color VARCHAR(20),              -- Màu sắc
    i_units VARCHAR(10),              -- Đơn vị đóng gói
    i_container VARCHAR(10),          -- Loại bao bì
    i_manager_id INTEGER,             -- Quản lý ngành hàng
    i_product_name VARCHAR(50)        -- Tên thương mại sản phẩm
);""",
    # -------------------------------------------------------------------------
    # 9. customer (Dimension Khách hàng)
    # -------------------------------------------------------------------------
    "customer": """\
-- BẢNG: customer (Dimension: Thông tin khách hàng mua sắm)
CREATE TABLE customer (
    c_customer_sk INTEGER PRIMARY KEY, -- Khóa chính thay thế của khách hàng
    c_customer_id VARCHAR(16) NOT NULL, -- Mã khách hàng tự nhiên (Customer Code)
    c_current_cdemo_sk INTEGER,       -- Khóa ngoại tham chiếu customer_demographics(cd_demo_sk)
    c_current_hdemo_sk INTEGER,       -- Khóa ngoại tham chiếu household_demographics(hd_demo_sk)
    c_current_addr_sk INTEGER,        -- Khóa ngoại tham chiếu customer_address(ca_address_sk) - BẮT BUỘC JOIN để lấy bang/thành phố
    c_first_shipto_date_sk INTEGER,   -- Ngày đầu tiên giao hàng
    c_first_sales_date_sk INTEGER,    -- Ngày mua hàng đầu tiên
    c_salutation VARCHAR(10),         -- Danh xưng (Mr., Mrs., Miss, Dr...)
    c_first_name VARCHAR(20),         -- Tên khách hàng
    c_last_name VARCHAR(30),          -- Họ khách hàng
    c_preferred_cust_flag VARCHAR(1), -- Cờ khách hàng thân thiết / VIP ('Y' hoặc 'N')
    c_birth_day INTEGER,              -- Ngày sinh (PII - CẤM Analyst)
    c_birth_month INTEGER,            -- Tháng sinh (PII - CẤM Analyst)
    c_birth_year INTEGER,             -- Năm sinh (PII - CẤM Analyst)
    c_birth_country VARCHAR(20),      -- Quốc gia sinh
    c_login VARCHAR(13),              -- Tên đăng nhập tài khoản
    c_email_address VARCHAR(50),      -- Địa chỉ email cá nhân (PII - CẤM Analyst)
    c_last_review_date_sk INTEGER
);""",
    # -------------------------------------------------------------------------
    # 10. customer_address (Dimension Địa chỉ)
    # -------------------------------------------------------------------------
    "customer_address": """\
-- BẢNG: customer_address (Dimension: Địa chỉ hành chính của khách hàng)
CREATE TABLE customer_address (
    ca_address_sk INTEGER PRIMARY KEY, -- Khóa chính địa chỉ
    ca_address_id VARCHAR(16) NOT NULL, -- Mã địa chỉ tự nhiên
    ca_street_number VARCHAR(10),     -- Số nhà (PII - CẤM Analyst)
    ca_street_name VARCHAR(60),       -- Tên đường phố (PII - CẤM Analyst)
    ca_street_type VARCHAR(15),       -- Loại đường (St, Ave, Blvd...)
    ca_suite_number VARCHAR(10),      -- Số phòng / căn hộ
    ca_city VARCHAR(60),              -- Tên thành phố
    ca_county VARCHAR(30),            -- Quận / Huyện
    ca_state VARCHAR(2),              -- Mã tiểu bang Hoa Kỳ (CA, TX, NY, FL, IL, CO...)
    ca_zip VARCHAR(10),               -- Mã bưu chính (Zip code)
    ca_country VARCHAR(20),           -- Tên quốc gia (United States)
    ca_gmt_offset DECIMAL(5,2),       -- Múi giờ
    ca_location_type VARCHAR(20)
);""",
    # -------------------------------------------------------------------------
    # 11. customer_demographics (Dimension Nhân khẩu học khách hàng)
    # -------------------------------------------------------------------------
    "customer_demographics": """\
-- BẢNG: customer_demographics (Dimension: Nhân khẩu học cá nhân khách hàng)
CREATE TABLE customer_demographics (
    cd_demo_sk INTEGER PRIMARY KEY,   -- Khóa chính nhân khẩu học
    cd_gender VARCHAR(1),             -- Giới tính ('M': Nam, 'F': Nữ)
    cd_marital_status VARCHAR(1),     -- Tình trạng hôn nhân ('S': Độc thân, 'M': Đã kết hôn, 'D': Ly hôn, 'W': Góa)
    cd_education_status VARCHAR(20),  -- Trình độ học vấn (Primary, Secondary, College, Advanced Degree)
    cd_purchase_estimate INTEGER,     -- Ước tính sức mua
    cd_credit_rating VARCHAR(10),     -- Xếp hạng tín dụng (Good, High Risk, Low Risk)
    cd_dep_count INTEGER,             -- Số người phụ thuộc
    cd_dep_employed_count INTEGER,    -- Số người phụ thuộc đang có việc làm
    cd_dep_college_count INTEGER      -- Số người phụ thuộc đang học đại học
);""",
    # -------------------------------------------------------------------------
    # 12. date_dim (Dimension Ngày tháng / Thời gian lịch)
    # -------------------------------------------------------------------------
    "date_dim": """\
-- BẢNG: date_dim (Dimension: Bảng mốc thời gian lịch chuẩn - QUY TẮC VÀNG: BẮT BUỘC JOIN để lọc thời gian)
CREATE TABLE date_dim (
    d_date_sk INTEGER PRIMARY KEY,    -- Khóa chính thay thế ngày (Surrogate Key kết nối bảng Fact)
    d_date_id VARCHAR(16) NOT NULL,   -- Mã ngày (YYYY-MM-DD)
    d_date DATE,                      -- Giá trị ngày chuẩn DATE
    d_month_seq INTEGER,              -- Thứ tự tháng lũy kế
    d_week_seq INTEGER,               -- Thứ tự tuần lũy kế
    d_quarter_seq INTEGER,            -- Thứ tự quý lũy kế
    d_year INTEGER,                   -- Năm (1998, 1999, 2000, 2001, 2002...)
    d_dow INTEGER,                    -- Thứ trong tuần (0: Chủ nhật, 1: Thứ hai... 6: Thứ bảy)
    d_moy INTEGER,                    -- Tháng trong năm (1-12)
    d_dom INTEGER,                    -- Ngày trong tháng (1-31)
    d_qoy INTEGER,                    -- Quý trong năm (1-4)
    d_fy_year INTEGER,                -- Năm tài chính
    d_fy_quarter_seq INTEGER,
    d_fy_week_seq INTEGER,
    d_day_name VARCHAR(9),            -- Tên ngày trong tuần (Sunday, Monday, Tuesday...)
    d_quarter_name VARCHAR(6),        -- Tên quý ('1998Q1', '2001Q3'...)
    d_holiday VARCHAR(1),             -- Cờ ngày nghỉ lễ ('Y' hoặc 'N')
    d_weekend VARCHAR(1),             -- Cờ ngày cuối tuần ('Y' hoặc 'N')
    d_following_holiday VARCHAR(1),
    d_first_dom INTEGER,
    d_last_dom INTEGER,
    d_same_day_ly INTEGER,
    d_same_day_lq INTEGER,
    d_current_day VARCHAR(1),
    d_current_week VARCHAR(1),
    d_current_month VARCHAR(1),
    d_current_quarter VARCHAR(1),
    d_current_year VARCHAR(1)
);""",
    # -------------------------------------------------------------------------
    # 13. time_dim (Dimension Giờ / Phút / Giây trong ngày)
    # -------------------------------------------------------------------------
    "time_dim": """\
-- BẢNG: time_dim (Dimension: Mốc thời gian chi tiết trong 24 giờ)
CREATE TABLE time_dim (
    t_time_sk INTEGER PRIMARY KEY,    -- Khóa chính thời gian
    t_time_id VARCHAR(16) NOT NULL,
    t_time INTEGER,                   -- Số giây tính từ nửa đêm (0-86399)
    t_hour INTEGER,                   -- Giờ trong ngày (0-23)
    t_minute INTEGER,                 -- Phút (0-59)
    t_second INTEGER,                 -- Giây (0-59)
    t_am_pm VARCHAR(2),               -- Buổi ('AM' hoặc 'PM')
    t_shift VARCHAR(20),              -- Ca làm việc
    t_sub_shift VARCHAR(20),
    t_meal_time VARCHAR(20)           -- Khung giờ ăn uống (breakfast, lunch, dinner)
);""",
    # -------------------------------------------------------------------------
    # 14. store (Dimension Chi nhánh cửa hàng bán lẻ)
    # -------------------------------------------------------------------------
    "store": """\
-- BẢNG: store (Dimension: Chi nhánh và địa điểm cửa hàng bán lẻ trực tiếp)
CREATE TABLE store (
    s_store_sk INTEGER PRIMARY KEY,   -- Khóa chính thay thế cửa hàng
    s_store_id VARCHAR(16) NOT NULL,  -- Mã cửa hàng tự nhiên
    s_rec_start_date DATE,
    s_rec_end_date DATE,
    s_closed_date_sk INTEGER,         -- Ngày đóng cửa (nếu có)
    s_store_name VARCHAR(50),         -- Tên cửa hàng / chi nhánh
    s_number_employees INTEGER,       -- Số lượng nhân viên
    s_floor_space INTEGER,            -- Diện tích mặt sàn kinh doanh (feet vuông)
    s_hours VARCHAR(20),              -- Giờ mở cửa hoạt động
    s_manager VARCHAR(40),            -- Họ tên quản lý cửa hàng
    s_market_id INTEGER,
    s_geography_class VARCHAR(100),
    s_market_desc VARCHAR(100),
    s_market_manager VARCHAR(40),
    s_division_id INTEGER,
    s_division_name VARCHAR(50),
    s_company_id INTEGER,
    s_company_name VARCHAR(50),
    s_street_number VARCHAR(10),
    s_street_name VARCHAR(60),
    s_street_type VARCHAR(15),
    s_suite_number VARCHAR(10),
    s_city VARCHAR(60),               -- Thành phố đặt cửa hàng
    s_county VARCHAR(30),
    s_state VARCHAR(2),               -- Tiểu bang đặt cửa hàng (TN, GA, CO, KY...)
    s_zip VARCHAR(10),
    s_country VARCHAR(20),
    s_gmt_offset DECIMAL(5,2),
    s_tax_percentage DECIMAL(5,2)     -- Tỷ lệ thuế áp dụng tại địa phương
);""",
    # -------------------------------------------------------------------------
    # 15. call_center (Dimension Trung tâm cuộc gọi)
    # -------------------------------------------------------------------------
    "call_center": """\
-- BẢNG: call_center (Dimension: Trung tâm hỗ trợ và bán hàng qua điện thoại)
CREATE TABLE call_center (
    cc_call_center_sk INTEGER PRIMARY KEY, -- Khóa chính trung tâm cuộc gọi
    cc_call_center_id VARCHAR(16) NOT NULL,
    cc_rec_start_date DATE,
    cc_rec_end_date DATE,
    cc_closed_date_sk INTEGER,
    cc_open_date_sk INTEGER,
    cc_name VARCHAR(50),              -- Tên tổng đài
    cc_class VARCHAR(50),
    cc_employees INTEGER,             -- Số nhân viên tổng đài
    cc_sq_ft INTEGER,
    cc_hours VARCHAR(20),
    cc_manager VARCHAR(40),
    cc_mkt_id INTEGER,
    cc_mkt_class VARCHAR(50),
    cc_mkt_desc VARCHAR(100),
    cc_market_manager VARCHAR(40),
    cc_division INTEGER,
    cc_division_name VARCHAR(50),
    cc_company INTEGER,
    cc_company_name VARCHAR(50),
    cc_street_number VARCHAR(10),
    cc_street_name VARCHAR(60),
    cc_street_type VARCHAR(15),
    cc_suite_number VARCHAR(10),
    cc_city VARCHAR(60),
    cc_county VARCHAR(30),
    cc_state VARCHAR(2),              -- Bang đặt trung tâm
    cc_zip VARCHAR(10),
    cc_country VARCHAR(20),
    cc_gmt_offset DECIMAL(5,2),
    cc_tax_percentage DECIMAL(5,2)
);""",
    # -------------------------------------------------------------------------
    # 16. catalog_page (Dimension Trang danh mục catalog)
    # -------------------------------------------------------------------------
    "catalog_page": """\
-- BẢNG: catalog_page (Dimension: Thông tin trang trong ấn phẩm danh mục)
CREATE TABLE catalog_page (
    cp_catalog_page_sk INTEGER PRIMARY KEY, -- Khóa chính trang catalog
    cp_catalog_page_id VARCHAR(16) NOT NULL,
    cp_start_date_sk INTEGER,         -- Ngày bắt đầu hiệu lực
    cp_end_date_sk INTEGER,           -- Ngày kết thúc hiệu lực
    cp_department VARCHAR(50),        -- Bộ phận phụ trách danh mục
    cp_catalog_number INTEGER,        -- Số kỳ phát hành catalog
    cp_catalog_page_number INTEGER,   -- Số trang trong quyển catalog
    cp_description VARCHAR(100),      -- Mô tả trang
    cp_type VARCHAR(100)              -- Thể loại catalog (monthly, bi-annual, seasonal)
);""",
    # -------------------------------------------------------------------------
    # 17. web_page (Dimension Trang web bán hàng)
    # -------------------------------------------------------------------------
    "web_page": """\
-- BẢNG: web_page (Dimension: Trang web cụ thể trên cổng thương mại điện tử)
CREATE TABLE web_page (
    wp_web_page_sk INTEGER PRIMARY KEY, -- Khóa chính trang web
    wp_web_page_id VARCHAR(16) NOT NULL,
    wp_rec_start_date DATE,
    wp_rec_end_date DATE,
    wp_creation_date_sk INTEGER,
    wp_access_date_sk INTEGER,
    wp_autogen_flag VARCHAR(1),
    wp_customer_sk INTEGER,
    wp_url VARCHAR(100),              -- Đường dẫn URL của trang web
    wp_type VARCHAR(50),              -- Loại trang (product, checkout, category, welcome)
    wp_char_count INTEGER,
    wp_link_count INTEGER,
    wp_image_count INTEGER,
    wp_max_ad_count INTEGER
);""",
    # -------------------------------------------------------------------------
    # 18. web_site (Dimension Website công ty)
    # -------------------------------------------------------------------------
    "web_site": """\
-- BẢNG: web_site (Dimension: Cổng thông tin / website bán hàng điện tử)
CREATE TABLE web_site (
    web_site_sk INTEGER PRIMARY KEY,  -- Khóa chính website
    web_site_id VARCHAR(16) NOT NULL,
    web_rec_start_date DATE,
    web_rec_end_date DATE,
    web_name VARCHAR(50),             -- Tên website
    web_open_date_sk INTEGER,
    web_close_date_sk INTEGER,
    web_class VARCHAR(50),
    web_manager VARCHAR(40),
    web_mkt_id INTEGER,
    web_mkt_class VARCHAR(50),
    web_mkt_desc VARCHAR(100),
    web_market_manager VARCHAR(40),
    web_company_id INTEGER,
    web_company_name VARCHAR(50),
    web_street_number VARCHAR(10),
    web_street_name VARCHAR(60),
    web_street_type VARCHAR(15),
    web_suite_number VARCHAR(10),
    web_city VARCHAR(60),
    web_county VARCHAR(30),
    web_state VARCHAR(2),
    web_zip VARCHAR(10),
    web_country VARCHAR(20),
    web_gmt_offset DECIMAL(5,2),
    web_tax_percentage DECIMAL(5,2)
);""",
    # -------------------------------------------------------------------------
    # 19. warehouse (Dimension Nhà kho lưu trữ)
    # -------------------------------------------------------------------------
    "warehouse": """\
-- BẢNG: warehouse (Dimension: Tổng kho và trung tâm hoàn tất đơn hàng)
CREATE TABLE warehouse (
    w_warehouse_sk INTEGER PRIMARY KEY, -- Khóa chính nhà kho
    w_warehouse_id VARCHAR(16) NOT NULL,
    w_warehouse_name VARCHAR(20),     -- Tên kho
    w_warehouse_sq_ft INTEGER,        -- Diện tích nhà kho (feet vuông)
    w_street_number VARCHAR(10),
    w_street_name VARCHAR(60),
    w_street_type VARCHAR(15),
    w_suite_number VARCHAR(10),
    w_city VARCHAR(60),               -- Thành phố đặt kho
    w_county VARCHAR(30),
    w_state VARCHAR(2),               -- Bang đặt kho
    w_zip VARCHAR(10),
    w_country VARCHAR(20),
    w_gmt_offset DECIMAL(5,2)
);""",
    # -------------------------------------------------------------------------
    # 20. ship_mode (Dimension Phương thức giao hàng)
    # -------------------------------------------------------------------------
    "ship_mode": """\
-- BẢNG: ship_mode (Dimension: Hình thức và đơn vị vận chuyển hàng hóa)
CREATE TABLE ship_mode (
    sm_ship_mode_sk INTEGER PRIMARY KEY, -- Khóa chính phương thức vận chuyển
    sm_ship_mode_id VARCHAR(16) NOT NULL,
    sm_type VARCHAR(30),              -- Loại hình (EXPRESS, NEXT DAY, OVERNIGHT, TWO DAY, REGULAR, LIBRARY)
    sm_code VARCHAR(10),
    sm_carrier VARCHAR(20),           -- Đơn vị vận chuyển (UPS, FedEx, USPS...)
    sm_contract VARCHAR(20)
);""",
    # -------------------------------------------------------------------------
    # 21. promotion (Dimension Chiến dịch khuyến mãi)
    # -------------------------------------------------------------------------
    "promotion": """\
-- BẢNG: promotion (Dimension: Chiến dịch ưu đãi, giảm giá và tiếp thị)
CREATE TABLE promotion (
    p_promo_sk INTEGER PRIMARY KEY,   -- Khóa chính khuyến mãi
    p_promo_id VARCHAR(16) NOT NULL,
    p_start_date_sk INTEGER,          -- Ngày bắt đầu chương trình
    p_end_date_sk INTEGER,            -- Ngày kết thúc chương trình
    p_item_sk INTEGER,                -- Mặt hàng được khuyến mãi
    p_cost DECIMAL(7,2),              -- Chi phí tổ chức chiến dịch
    p_response_target INTEGER,
    p_promo_name VARCHAR(50),         -- Tên chương trình ưu đãi
    p_channel_dmail VARCHAR(1),
    p_channel_email VARCHAR(1),       -- Kênh email marketing
    p_channel_catalog VARCHAR(1),
    p_channel_tv VARCHAR(1),          -- Kênh quảng cáo truyền hình
    p_channel_radio VARCHAR(1),
    p_channel_press VARCHAR(1),
    p_channel_event VARCHAR(1),
    p_channel_demo VARCHAR(1),
    p_channel_details VARCHAR(100),
    p_purpose VARCHAR(15),            -- Mục đích khuyến mãi
    p_discount_active VARCHAR(1)      -- Cờ trạng thái đang áp dụng giảm giá ('Y' hoặc 'N')
);""",
    # -------------------------------------------------------------------------
    # 22. reason (Dimension Lý do đổi trả)
    # -------------------------------------------------------------------------
    "reason": """\
-- BẢNG: reason (Dimension: Lý do khách hàng hoàn trả sản phẩm)
CREATE TABLE reason (
    r_reason_sk INTEGER PRIMARY KEY,  -- Khóa chính lý do hoàn trả
    r_reason_id VARCHAR(16) NOT NULL,
    r_reason_desc VARCHAR(100)        -- Diễn giải lý do (Hàng lỗi, sai kích cỡ, không vừa ý...)
);""",
    # -------------------------------------------------------------------------
    # 23. household_demographics (Dimension Hộ gia đình)
    # -------------------------------------------------------------------------
    "household_demographics": """\
-- BẢNG: household_demographics (Dimension: Đặc điểm và quy mô hộ gia đình của khách)
CREATE TABLE household_demographics (
    hd_demo_sk INTEGER PRIMARY KEY,   -- Khóa chính hộ gia đình
    hd_income_band_sk INTEGER,        -- Khóa ngoại tham chiếu income_band(ib_income_band_sk)
    hd_buy_potential VARCHAR(15),     -- Tiềm năng chi tiêu của hộ (1001-5000, 5001-10000...)
    hd_dep_count INTEGER,             -- Số người phụ thuộc trong gia đình
    hd_vehicle_count INTEGER          -- Số lượng xe hơi sở hữu
);""",
    # -------------------------------------------------------------------------
    # 24. income_band (Dimension Khung thu nhập)
    # -------------------------------------------------------------------------
    "income_band": """\
-- BẢNG: income_band (Dimension: Các dải phân mức thu nhập hàng năm)
CREATE TABLE income_band (
    ib_income_band_sk INTEGER PRIMARY KEY, -- Khóa chính khung thu nhập
    ib_lower_bound INTEGER,           -- Ngưỡng thu nhập tối thiểu (USD/năm - PII)
    ib_upper_bound INTEGER            -- Ngưỡng thu nhập tối đa (USD/năm - PII)
);""",
}

_LEGACY_TPCH_SCHEMAS: Final[dict[str, str]] = {
    "region": """\\
-- BẢNG: region (Khu vực địa lý thế giới)
CREATE TABLE region (
    r_regionkey INTEGER PRIMARY KEY, -- Mã khu vực (0: AFRICA, 1: AMERICA, 2: ASIA, 3: EUROPE, 4: MIDDLE EAST)
    r_name VARCHAR(25) NOT NULL,      -- Tên khu vực
    r_comment VARCHAR(152)           -- Ghi chú khu vực
);""",
    "nation": """\\
-- BẢNG: nation (Quốc gia)
CREATE TABLE nation (
    n_nationkey INTEGER PRIMARY KEY,   -- Mã quốc gia (0-24)
    n_name VARCHAR(25) NOT NULL,        -- Tên quốc gia (VIETNAM, JAPAN, UNITED STATES, GERMANY...)
    n_regionkey INTEGER NOT NULL,       -- Khóa ngoại tham chiếu region(r_regionkey)
    n_comment VARCHAR(152)             -- Ghi chú quốc gia
);""",
    "supplier": """\\
-- BẢNG: supplier (Nhà cung cấp hàng hóa)
CREATE TABLE supplier (
    s_suppkey INTEGER PRIMARY KEY,      -- Mã nhà cung cấp
    s_name VARCHAR(25) NOT NULL,        -- Tên nhà cung cấp (Supplier#000000001)
    s_address VARCHAR(40) NOT NULL,     -- Địa chỉ trụ sở/kho
    s_nationkey INTEGER NOT NULL,       -- Khóa ngoại tham chiếu nation(n_nationkey)
    s_phone VARCHAR(15) NOT NULL,       -- Số điện thoại (PII - CẤM Analyst)
    s_acctbal DECIMAL(15, 2) NOT NULL,  -- Số dư tài khoản đối tác (Tài chính - CẤM Analyst)
    s_comment VARCHAR(101)             -- Đánh giá/khiếu nại nhà cung cấp
);""",
    "customer": """\\
-- BẢNG: customer (Khách hàng)
CREATE TABLE customer (
    c_custkey INTEGER PRIMARY KEY,      -- Mã khách hàng
    c_name VARCHAR(25) NOT NULL,        -- Tên khách hàng (Customer#000000001)
    c_address VARCHAR(40) NOT NULL,     -- Địa chỉ cá nhân (PII - CẤM Analyst)
    c_nationkey INTEGER NOT NULL,       -- Khóa ngoại tham chiếu nation(n_nationkey)
    c_phone VARCHAR(15) NOT NULL,       -- Số điện thoại (PII - CẤM Analyst)
    c_acctbal DECIMAL(15, 2) NOT NULL,  -- Số dư tài khoản khách hàng (Tài chính - CẤM Analyst)
    c_mktsegment VARCHAR(10) NOT NULL,  -- Phân khúc thị trường (AUTOMOBILE, BUILDING, FURNITURE, HOUSEHOLD, MACHINERY)
    c_comment VARCHAR(117)             -- Ghi chú khách hàng
);""",
    "part": """\\
-- BẢNG: part (Danh mục linh kiện / mặt hàng)
CREATE TABLE part (
    p_partkey INTEGER PRIMARY KEY,      -- Mã mặt hàng/linh kiện
    p_name VARCHAR(55) NOT NULL,        -- Tên mặt hàng
    p_mfgr VARCHAR(25) NOT NULL,        -- Nhà sản xuất (Manufacturer#1...)
    p_brand VARCHAR(10) NOT NULL,       -- Thương hiệu (Brand#11...)
    p_type VARCHAR(25) NOT NULL,        -- Loại linh kiện (ECONOMY ANODIZED STEEL, PROMO POLISHED BRASS...)
    p_size INTEGER NOT NULL,            -- Kích cỡ linh kiện (1-50)
    p_container VARCHAR(10) NOT NULL,   -- Quy cách đóng gói (SM CASE, JUMBO BOX, MED BAG...)
    p_retailprice DECIMAL(15, 2) NOT NULL, -- Giá bán lẻ niêm yết (USD)
    p_comment VARCHAR(23)              -- Mô tả chi tiết
);""",
    "partsupp": """\\
-- BẢNG: partsupp (Mối quan hệ cung ứng - Tồn kho mặt hàng từ nhà cung cấp)
CREATE TABLE partsupp (
    ps_partkey INTEGER NOT NULL,        -- Khóa ngoại tham chiếu part(p_partkey)
    ps_suppkey INTEGER NOT NULL,        -- Khóa ngoại tham chiếu supplier(s_suppkey)
    ps_availqty INTEGER NOT NULL,       -- Số lượng tồn kho sẵn sàng cung cấp
    ps_supplycost DECIMAL(15, 2) NOT NULL, -- Đơn giá chi phí nhập hàng từ nhà cung cấp
    ps_comment VARCHAR(199),           -- Ghi chú tồn kho
    PRIMARY KEY (ps_partkey, ps_suppkey)
);""",
    "orders": """\\
-- BẢNG: orders (Đơn đặt hàng)
CREATE TABLE orders (
    o_orderkey INTEGER PRIMARY KEY,     -- Mã đơn đặt hàng
    o_custkey INTEGER NOT NULL,         -- Khóa ngoại tham chiếu customer(c_custkey)
    o_orderstatus VARCHAR(1) NOT NULL,  -- Trạng thái đơn (O: Đang xử lý, F: Đã hoàn tất, P: Chờ duyệt)
    o_totalprice DECIMAL(15, 2) NOT NULL, -- Tổng tiền đơn hàng
    o_orderdate DATE NOT NULL,          -- Ngày đặt hàng (Định dạng: YYYY-MM-DD)
    o_orderpriority VARCHAR(15) NOT NULL, -- Mức độ ưu tiên (1-URGENT, 2-HIGH, 3-MEDIUM, 4-NOT SPECIFIED, 5-LOW)
    o_clerk VARCHAR(15) NOT NULL,       -- Nhân viên phụ trách (Clerk#000000001)
    o_shippriority INTEGER NOT NULL,    -- Thứ tự ưu tiên vận chuyển
    o_comment VARCHAR(79)              -- Ghi chú đơn hàng
);""",
    "lineitem": """\\
-- BẢNG: lineitem (Chi tiết từng dòng sản phẩm trong đơn hàng - Bảng sự kiện chính)
CREATE TABLE lineitem (
    l_orderkey INTEGER NOT NULL,        -- Khóa ngoại tham chiếu orders(o_orderkey)
    l_partkey INTEGER NOT NULL,         -- Khóa ngoại tham chiếu part(p_partkey)
    l_suppkey INTEGER NOT NULL,         -- Khóa ngoại tham chiếu supplier(s_suppkey)
    l_linenumber INTEGER NOT NULL,      -- Số thứ tự dòng hàng trong đơn
    l_quantity DECIMAL(15, 2) NOT NULL, -- Số lượng đặt mua
    l_extendedprice DECIMAL(15, 2) NOT NULL, -- Giá gốc = l_quantity * p_retailprice
    l_discount DECIMAL(15, 2) NOT NULL, -- Tỷ lệ chiết khấu (0.00 đến 0.10, tức 0% - 10%)
    l_tax DECIMAL(15, 2) NOT NULL,      -- Tỷ lệ thuế VAT (0.00 đến 0.08, tức 0% - 8%)
    l_returnflag VARCHAR(1) NOT NULL,   -- Cờ hoàn trả (R: Hoàn hàng, A: Chấp nhận, N: Chưa xử lý)
    l_linestatus VARCHAR(1) NOT NULL,   -- Trạng thái dòng hàng (O: Mở, F: Đã xuất xong)
    l_shipdate DATE NOT NULL,           -- Ngày giao hàng xuất kho
    l_commitdate DATE NOT NULL,         -- Ngày cam kết giao cho khách
    l_receiptdate DATE NOT NULL,        -- Ngày khách thực nhận hàng
    l_shipinstruct VARCHAR(25) NOT NULL, -- Hướng dẫn giao (DELIVER IN PERSON, TAKE BACK RETURN, NONE)
    l_shipmode VARCHAR(10) NOT NULL,    -- Phương thức vận chuyển (AIR, FOB, MAIL, RAIL, REG AIR, SHIP, TRUCK)
    l_comment VARCHAR(44),             -- Ghi chú dòng hàng
    PRIMARY KEY (l_orderkey, l_linenumber)
);""",
}

# Giữ alias cho tương thích ngược
TPCH_TABLE_SCHEMAS: Final[dict[str, str]] = {
    **_LEGACY_TPCH_SCHEMAS,
    **TPCDS_TABLE_SCHEMAS,
}


# ==============================================================================
# 2. DANH MỤC CỘT TƯƠNG ỨNG 24 BẢNG TPC-DS (CHO WILDCARD VÀ VALIDATION)
# ==============================================================================

TPCDS_TABLE_COLUMNS: Final[dict[str, list[str]]] = {
    "call_center": [
        "cc_call_center_sk",
        "cc_call_center_id",
        "cc_rec_start_date",
        "cc_rec_end_date",
        "cc_closed_date_sk",
        "cc_open_date_sk",
        "cc_name",
        "cc_class",
        "cc_employees",
        "cc_sq_ft",
        "cc_hours",
        "cc_manager",
        "cc_mkt_id",
        "cc_mkt_class",
        "cc_mkt_desc",
        "cc_market_manager",
        "cc_division",
        "cc_division_name",
        "cc_company",
        "cc_company_name",
        "cc_street_number",
        "cc_street_name",
        "cc_street_type",
        "cc_suite_number",
        "cc_city",
        "cc_county",
        "cc_state",
        "cc_zip",
        "cc_country",
        "cc_gmt_offset",
        "cc_tax_percentage",
    ],
    "catalog_page": [
        "cp_catalog_page_sk",
        "cp_catalog_page_id",
        "cp_start_date_sk",
        "cp_end_date_sk",
        "cp_department",
        "cp_catalog_number",
        "cp_catalog_page_number",
        "cp_description",
        "cp_type",
    ],
    "catalog_returns": [
        "cr_returned_date_sk",
        "cr_returned_time_sk",
        "cr_item_sk",
        "cr_refunded_customer_sk",
        "cr_refunded_cdemo_sk",
        "cr_refunded_hdemo_sk",
        "cr_refunded_addr_sk",
        "cr_returning_customer_sk",
        "cr_returning_cdemo_sk",
        "cr_returning_hdemo_sk",
        "cr_returning_addr_sk",
        "cr_call_center_sk",
        "cr_catalog_page_sk",
        "cr_ship_mode_sk",
        "cr_warehouse_sk",
        "cr_reason_sk",
        "cr_order_number",
        "cr_return_quantity",
        "cr_return_amount",
        "cr_return_tax",
        "cr_return_amt_inc_tax",
        "cr_fee",
        "cr_return_ship_cost",
        "cr_refunded_cash",
        "cr_reversed_charge",
        "cr_store_credit",
        "cr_net_loss",
    ],
    "catalog_sales": [
        "cs_sold_date_sk",
        "cs_sold_time_sk",
        "cs_ship_date_sk",
        "cs_bill_customer_sk",
        "cs_bill_cdemo_sk",
        "cs_bill_hdemo_sk",
        "cs_bill_addr_sk",
        "cs_ship_customer_sk",
        "cs_ship_cdemo_sk",
        "cs_ship_hdemo_sk",
        "cs_ship_addr_sk",
        "cs_call_center_sk",
        "cs_catalog_page_sk",
        "cs_ship_mode_sk",
        "cs_warehouse_sk",
        "cs_item_sk",
        "cs_promo_sk",
        "cs_order_number",
        "cs_quantity",
        "cs_wholesale_cost",
        "cs_list_price",
        "cs_sales_price",
        "cs_ext_discount_amt",
        "cs_ext_sales_price",
        "cs_ext_wholesale_cost",
        "cs_ext_list_price",
        "cs_ext_tax",
        "cs_coupon_amt",
        "cs_ext_ship_cost",
        "cs_net_paid",
        "cs_net_paid_inc_tax",
        "cs_net_paid_inc_ship",
        "cs_net_paid_inc_ship_tax",
        "cs_net_profit",
    ],
    "customer": [
        "c_customer_sk",
        "c_customer_id",
        "c_current_cdemo_sk",
        "c_current_hdemo_sk",
        "c_current_addr_sk",
        "c_first_shipto_date_sk",
        "c_first_sales_date_sk",
        "c_salutation",
        "c_first_name",
        "c_last_name",
        "c_preferred_cust_flag",
        "c_birth_day",
        "c_birth_month",
        "c_birth_year",
        "c_birth_country",
        "c_login",
        "c_email_address",
        "c_last_review_date_sk",
    ],
    "customer_address": [
        "ca_address_sk",
        "ca_address_id",
        "ca_street_number",
        "ca_street_name",
        "ca_street_type",
        "ca_suite_number",
        "ca_city",
        "ca_county",
        "ca_state",
        "ca_zip",
        "ca_country",
        "ca_gmt_offset",
        "ca_location_type",
    ],
    "customer_demographics": [
        "cd_demo_sk",
        "cd_gender",
        "cd_marital_status",
        "cd_education_status",
        "cd_purchase_estimate",
        "cd_credit_rating",
        "cd_dep_count",
        "cd_dep_employed_count",
        "cd_dep_college_count",
    ],
    "date_dim": [
        "d_date_sk",
        "d_date_id",
        "d_date",
        "d_month_seq",
        "d_week_seq",
        "d_quarter_seq",
        "d_year",
        "d_dow",
        "d_moy",
        "d_dom",
        "d_qoy",
        "d_fy_year",
        "d_fy_quarter_seq",
        "d_fy_week_seq",
        "d_day_name",
        "d_quarter_name",
        "d_holiday",
        "d_weekend",
        "d_following_holiday",
        "d_first_dom",
        "d_last_dom",
        "d_same_day_ly",
        "d_same_day_lq",
        "d_current_day",
        "d_current_week",
        "d_current_month",
        "d_current_quarter",
        "d_current_year",
    ],
    "household_demographics": [
        "hd_demo_sk",
        "hd_income_band_sk",
        "hd_buy_potential",
        "hd_dep_count",
        "hd_vehicle_count",
    ],
    "income_band": [
        "ib_income_band_sk",
        "ib_lower_bound",
        "ib_upper_bound",
    ],
    "inventory": [
        "inv_date_sk",
        "inv_item_sk",
        "inv_warehouse_sk",
        "inv_quantity_on_hand",
    ],
    "item": [
        "i_item_sk",
        "i_item_id",
        "i_rec_start_date",
        "i_rec_end_date",
        "i_item_desc",
        "i_current_price",
        "i_wholesale_cost",
        "i_brand_id",
        "i_brand",
        "i_class_id",
        "i_class",
        "i_category_id",
        "i_category",
        "i_manufact_id",
        "i_manufact",
        "i_size",
        "i_formulation",
        "i_color",
        "i_units",
        "i_container",
        "i_manager_id",
        "i_product_name",
    ],
    "promotion": [
        "p_promo_sk",
        "p_promo_id",
        "p_start_date_sk",
        "p_end_date_sk",
        "p_item_sk",
        "p_cost",
        "p_response_target",
        "p_promo_name",
        "p_channel_dmail",
        "p_channel_email",
        "p_channel_catalog",
        "p_channel_tv",
        "p_channel_radio",
        "p_channel_press",
        "p_channel_event",
        "p_channel_demo",
        "p_channel_details",
        "p_purpose",
        "p_discount_active",
    ],
    "reason": [
        "r_reason_sk",
        "r_reason_id",
        "r_reason_desc",
    ],
    "ship_mode": [
        "sm_ship_mode_sk",
        "sm_ship_mode_id",
        "sm_type",
        "sm_code",
        "sm_carrier",
        "sm_contract",
    ],
    "store": [
        "s_store_sk",
        "s_store_id",
        "s_rec_start_date",
        "s_rec_end_date",
        "s_closed_date_sk",
        "s_store_name",
        "s_number_employees",
        "s_floor_space",
        "s_hours",
        "s_manager",
        "s_market_id",
        "s_geography_class",
        "s_market_desc",
        "s_market_manager",
        "s_division_id",
        "s_division_name",
        "s_company_id",
        "s_company_name",
        "s_street_number",
        "s_street_name",
        "s_street_type",
        "s_suite_number",
        "s_city",
        "s_county",
        "s_state",
        "s_zip",
        "s_country",
        "s_gmt_offset",
        "s_tax_percentage",
    ],
    "store_returns": [
        "sr_returned_date_sk",
        "sr_return_time_sk",
        "sr_item_sk",
        "sr_customer_sk",
        "sr_cdemo_sk",
        "sr_hdemo_sk",
        "sr_addr_sk",
        "sr_store_sk",
        "sr_reason_sk",
        "sr_ticket_number",
        "sr_return_quantity",
        "sr_return_amt",
        "sr_return_tax",
        "sr_return_amt_inc_tax",
        "sr_fee",
        "sr_return_ship_cost",
        "sr_refunded_cash",
        "sr_reversed_charge",
        "sr_store_credit",
        "sr_net_loss",
    ],
    "store_sales": [
        "ss_sold_date_sk",
        "ss_sold_time_sk",
        "ss_item_sk",
        "ss_customer_sk",
        "ss_cdemo_sk",
        "ss_hdemo_sk",
        "ss_addr_sk",
        "ss_store_sk",
        "ss_promo_sk",
        "ss_ticket_number",
        "ss_quantity",
        "ss_wholesale_cost",
        "ss_list_price",
        "ss_sales_price",
        "ss_ext_discount_amt",
        "ss_ext_sales_price",
        "ss_ext_wholesale_cost",
        "ss_ext_list_price",
        "ss_ext_tax",
        "ss_coupon_amt",
        "ss_net_paid",
        "ss_net_paid_inc_tax",
        "ss_net_profit",
    ],
    "time_dim": [
        "t_time_sk",
        "t_time_id",
        "t_time",
        "t_hour",
        "t_minute",
        "t_second",
        "t_am_pm",
        "t_shift",
        "t_sub_shift",
        "t_meal_time",
    ],
    "warehouse": [
        "w_warehouse_sk",
        "w_warehouse_id",
        "w_warehouse_name",
        "w_warehouse_sq_ft",
        "w_street_number",
        "w_street_name",
        "w_street_type",
        "w_suite_number",
        "w_city",
        "w_county",
        "w_state",
        "w_zip",
        "w_country",
        "w_gmt_offset",
    ],
    "web_page": [
        "wp_web_page_sk",
        "wp_web_page_id",
        "wp_rec_start_date",
        "wp_rec_end_date",
        "wp_creation_date_sk",
        "wp_access_date_sk",
        "wp_autogen_flag",
        "wp_customer_sk",
        "wp_url",
        "wp_type",
        "wp_char_count",
        "wp_link_count",
        "wp_image_count",
        "wp_max_ad_count",
    ],
    "web_returns": [
        "wr_returned_date_sk",
        "wr_returned_time_sk",
        "wr_item_sk",
        "wr_refunded_customer_sk",
        "wr_refunded_cdemo_sk",
        "wr_refunded_hdemo_sk",
        "wr_refunded_addr_sk",
        "wr_returning_customer_sk",
        "wr_returning_cdemo_sk",
        "wr_returning_hdemo_sk",
        "wr_returning_addr_sk",
        "wr_web_page_sk",
        "wr_reason_sk",
        "wr_order_number",
        "wr_return_quantity",
        "wr_return_amt",
        "wr_return_tax",
        "wr_return_amt_inc_tax",
        "wr_fee",
        "wr_return_ship_cost",
        "wr_refunded_cash",
        "wr_reversed_charge",
        "wr_account_credit",
        "wr_net_loss",
    ],
    "web_sales": [
        "ws_sold_date_sk",
        "ws_sold_time_sk",
        "ws_ship_date_sk",
        "ws_item_sk",
        "ws_bill_customer_sk",
        "ws_bill_cdemo_sk",
        "ws_bill_hdemo_sk",
        "ws_bill_addr_sk",
        "ws_ship_customer_sk",
        "ws_ship_cdemo_sk",
        "ws_ship_hdemo_sk",
        "ws_ship_addr_sk",
        "ws_web_page_sk",
        "ws_web_site_sk",
        "ws_ship_mode_sk",
        "ws_warehouse_sk",
        "ws_promo_sk",
        "ws_order_number",
        "ws_quantity",
        "ws_wholesale_cost",
        "ws_list_price",
        "ws_sales_price",
        "ws_ext_discount_amt",
        "ws_ext_sales_price",
        "ws_ext_wholesale_cost",
        "ws_ext_list_price",
        "ws_ext_tax",
        "ws_coupon_amt",
        "ws_ext_ship_cost",
        "ws_net_paid",
        "ws_net_paid_inc_tax",
        "ws_net_paid_inc_ship",
        "ws_net_paid_inc_ship_tax",
        "ws_net_profit",
    ],
    "web_site": [
        "web_site_sk",
        "web_site_id",
        "web_rec_start_date",
        "web_rec_end_date",
        "web_name",
        "web_open_date_sk",
        "web_close_date_sk",
        "web_class",
        "web_manager",
        "web_mkt_id",
        "web_mkt_class",
        "web_mkt_desc",
        "web_market_manager",
        "web_company_id",
        "web_company_name",
        "web_street_number",
        "web_street_name",
        "web_street_type",
        "web_suite_number",
        "web_city",
        "web_county",
        "web_state",
        "web_zip",
        "web_country",
        "web_gmt_offset",
        "web_tax_percentage",
    ],
}

# Danh mục các cột tương ứng 8 bảng TPC-H (giữ lại để đảm bảo tương thích ngược cho AST Sanitizer và RBAC)
TPCH_TABLE_COLUMNS: Final[dict[str, list[str]]] = {
    **TPCDS_TABLE_COLUMNS,
    "region": ["r_regionkey", "r_name", "r_comment"],
    "nation": ["n_nationkey", "n_name", "n_regionkey", "n_comment"],
    "supplier": [
        "s_suppkey",
        "s_name",
        "s_address",
        "s_nationkey",
        "s_phone",
        "s_acctbal",
        "s_comment",
    ],
    "customer": [
        "c_custkey",
        "c_name",
        "c_address",
        "c_nationkey",
        "c_phone",
        "c_acctbal",
        "c_mktsegment",
        "c_comment",
        "c_customer_sk",
        "c_customer_id",
        "c_current_cdemo_sk",
        "c_current_hdemo_sk",
        "c_current_addr_sk",
        "c_first_shipto_date_sk",
        "c_first_sales_date_sk",
        "c_salutation",
        "c_first_name",
        "c_last_name",
        "c_preferred_cust_flag",
        "c_birth_day",
        "c_birth_month",
        "c_birth_year",
        "c_birth_country",
        "c_login",
        "c_email_address",
        "c_last_review_date_sk",
    ],
    "part": [
        "p_partkey",
        "p_name",
        "p_mfgr",
        "p_brand",
        "p_type",
        "p_size",
        "p_container",
        "p_retailprice",
        "p_comment",
    ],
    "partsupp": [
        "ps_partkey",
        "ps_suppkey",
        "ps_availqty",
        "ps_supplycost",
        "ps_comment",
    ],
    "orders": [
        "o_orderkey",
        "o_custkey",
        "o_orderstatus",
        "o_totalprice",
        "o_orderdate",
        "o_orderpriority",
        "o_clerk",
        "o_shippriority",
        "o_comment",
    ],
    "lineitem": [
        "l_orderkey",
        "l_partkey",
        "l_suppkey",
        "l_linenumber",
        "l_quantity",
        "l_extendedprice",
        "l_discount",
        "l_tax",
        "l_returnflag",
        "l_linestatus",
        "l_shipdate",
        "l_commitdate",
        "l_receiptdate",
        "l_shipinstruct",
        "l_shipmode",
        "l_comment",
    ],
}


# ==============================================================================
# 3. ĐỒ THỊ QUAN HỆ KHÓA NGOẠI 24 BẢNG (SNOWFLAKE SCHEMA JOIN GRAPH CHO BFS)
# ==============================================================================

TPCDS_JOIN_RELATIONSHIPS: Final[list[JoinRelationship]] = [
    # --- 1. store_sales Relationships ---
    JoinRelationship(
        from_table="store_sales",
        to_table="date_dim",
        condition="store_sales.ss_sold_date_sk = date_dim.d_date_sk",
        description="Giao dịch bán tại quầy liên kết ngày tháng (bắt buộc để lọc năm/tháng/quý)",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="time_dim",
        condition="store_sales.ss_sold_time_sk = time_dim.t_time_sk",
        description="Giao dịch bán tại quầy liên kết khung giờ",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="item",
        condition="store_sales.ss_item_sk = item.i_item_sk",
        description="Sản phẩm được mua tại cửa hàng",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="customer",
        condition="store_sales.ss_customer_sk = customer.c_customer_sk",
        description="Khách hàng thực hiện mua tại cửa hàng",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="store",
        condition="store_sales.ss_store_sk = store.s_store_sk",
        description="Chi nhánh cửa hàng phát sinh giao dịch",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="customer_address",
        condition="store_sales.ss_addr_sk = customer_address.ca_address_sk",
        description="Địa chỉ khách mua hàng tại cửa hàng",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="customer_demographics",
        condition="store_sales.ss_cdemo_sk = customer_demographics.cd_demo_sk",
        description="Đặc điểm nhân khẩu học của khách mua tại quầy",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="household_demographics",
        condition="store_sales.ss_hdemo_sk = household_demographics.hd_demo_sk",
        description="Đặc điểm hộ gia đình của khách mua tại quầy",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="promotion",
        condition="store_sales.ss_promo_sk = promotion.p_promo_sk",
        description="Chương trình ưu đãi áp dụng cho giao dịch tại quầy",
    ),
    JoinRelationship(
        from_table="store_sales",
        to_table="store_returns",
        condition="store_sales.ss_ticket_number = store_returns.sr_ticket_number AND store_sales.ss_item_sk = store_returns.sr_item_sk",
        description="Đơn bán lẻ liên kết với giao dịch đổi trả tương ứng",
    ),
    # --- 2. store_returns Relationships ---
    JoinRelationship(
        from_table="store_returns",
        to_table="date_dim",
        condition="store_returns.sr_returned_date_sk = date_dim.d_date_sk",
        description="Giao dịch đổi trả tại quầy liên kết ngày tháng",
    ),
    JoinRelationship(
        from_table="store_returns",
        to_table="item",
        condition="store_returns.sr_item_sk = item.i_item_sk",
        description="Sản phẩm bị trả lại tại cửa hàng",
    ),
    JoinRelationship(
        from_table="store_returns",
        to_table="customer",
        condition="store_returns.sr_customer_sk = customer.c_customer_sk",
        description="Khách hàng mang hàng đến trả",
    ),
    JoinRelationship(
        from_table="store_returns",
        to_table="store",
        condition="store_returns.sr_store_sk = store.s_store_sk",
        description="Cửa hàng tiếp nhận hàng trả lại",
    ),
    JoinRelationship(
        from_table="store_returns",
        to_table="reason",
        condition="store_returns.sr_reason_sk = reason.r_reason_sk",
        description="Lý do hoàn trả hàng tại cửa hàng",
    ),
    # --- 3. web_sales Relationships ---
    JoinRelationship(
        from_table="web_sales",
        to_table="date_dim",
        condition="web_sales.ws_sold_date_sk = date_dim.d_date_sk",
        description="Đơn hàng online liên kết ngày đặt (bắt buộc để lọc năm/tháng/quý)",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="item",
        condition="web_sales.ws_item_sk = item.i_item_sk",
        description="Sản phẩm bán qua kênh trực tuyến",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="customer",
        condition="web_sales.ws_bill_customer_sk = customer.c_customer_sk",
        description="Khách hàng thanh toán đơn trực tuyến",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="customer_address",
        condition="web_sales.ws_bill_addr_sk = customer_address.ca_address_sk",
        description="Địa chỉ thanh toán của khách online",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="web_page",
        condition="web_sales.ws_web_page_sk = web_page.wp_web_page_sk",
        description="Trang web phát sinh giao dịch bán hàng",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="web_site",
        condition="web_sales.ws_web_site_sk = web_site.web_site_sk",
        description="Website thương mại điện tử phát sinh đơn",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="ship_mode",
        condition="web_sales.ws_ship_mode_sk = ship_mode.sm_ship_mode_sk",
        description="Phương thức vận chuyển đơn hàng trực tuyến",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="warehouse",
        condition="web_sales.ws_warehouse_sk = warehouse.w_warehouse_sk",
        description="Kho xuất hàng cho đơn online",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="promotion",
        condition="web_sales.ws_promo_sk = promotion.p_promo_sk",
        description="Chương trình ưu đãi áp dụng cho đơn online",
    ),
    JoinRelationship(
        from_table="web_sales",
        to_table="web_returns",
        condition="web_sales.ws_order_number = web_returns.wr_order_number AND web_sales.ws_item_sk = web_returns.wr_item_sk",
        description="Đơn online liên kết với giao dịch đổi trả trực tuyến",
    ),
    # --- 4. web_returns Relationships ---
    JoinRelationship(
        from_table="web_returns",
        to_table="date_dim",
        condition="web_returns.wr_returned_date_sk = date_dim.d_date_sk",
        description="Giao dịch đổi trả trực tuyến liên kết ngày tháng",
    ),
    JoinRelationship(
        from_table="web_returns",
        to_table="item",
        condition="web_returns.wr_item_sk = item.i_item_sk",
        description="Sản phẩm đổi trả trực tuyến",
    ),
    JoinRelationship(
        from_table="web_returns",
        to_table="customer",
        condition="web_returns.wr_refunded_customer_sk = customer.c_customer_sk",
        description="Khách hàng được hoàn tiền đơn online",
    ),
    JoinRelationship(
        from_table="web_returns",
        to_table="web_page",
        condition="web_returns.wr_web_page_sk = web_page.wp_web_page_sk",
        description="Trang web xử lý hoàn trả đơn online",
    ),
    JoinRelationship(
        from_table="web_returns",
        to_table="reason",
        condition="web_returns.wr_reason_sk = reason.r_reason_sk",
        description="Lý do hoàn trả đơn online",
    ),
    # --- 5. catalog_sales Relationships ---
    JoinRelationship(
        from_table="catalog_sales",
        to_table="date_dim",
        condition="catalog_sales.cs_sold_date_sk = date_dim.d_date_sk",
        description="Đơn hàng catalog liên kết ngày đặt",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="item",
        condition="catalog_sales.cs_item_sk = item.i_item_sk",
        description="Sản phẩm đặt mua qua catalog",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="customer",
        condition="catalog_sales.cs_bill_customer_sk = customer.c_customer_sk",
        description="Khách hàng thanh toán đơn qua catalog",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="customer_address",
        condition="catalog_sales.cs_bill_addr_sk = customer_address.ca_address_sk",
        description="Địa chỉ nhận hóa đơn catalog",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="call_center",
        condition="catalog_sales.cs_call_center_sk = call_center.cc_call_center_sk",
        description="Tổng đài chăm sóc khách hàng tiếp nhận đơn catalog",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="catalog_page",
        condition="catalog_sales.cs_catalog_page_sk = catalog_page.cp_catalog_page_sk",
        description="Trang ấn phẩm catalog chứa mặt hàng",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="ship_mode",
        condition="catalog_sales.cs_ship_mode_sk = ship_mode.sm_ship_mode_sk",
        description="Phương thức gửi hàng catalog",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="warehouse",
        condition="catalog_sales.cs_warehouse_sk = warehouse.w_warehouse_sk",
        description="Kho xuất hàng cho đơn catalog",
    ),
    JoinRelationship(
        from_table="catalog_sales",
        to_table="catalog_returns",
        condition="catalog_sales.cs_order_number = catalog_returns.cr_order_number AND catalog_sales.cs_item_sk = catalog_returns.cr_item_sk",
        description="Đơn catalog liên kết với giao dịch đổi trả",
    ),
    # --- 6. catalog_returns Relationships ---
    JoinRelationship(
        from_table="catalog_returns",
        to_table="date_dim",
        condition="catalog_returns.cr_returned_date_sk = date_dim.d_date_sk",
        description="Giao dịch đổi trả catalog liên kết ngày tháng",
    ),
    JoinRelationship(
        from_table="catalog_returns",
        to_table="item",
        condition="catalog_returns.cr_item_sk = item.i_item_sk",
        description="Sản phẩm catalog bị trả lại",
    ),
    JoinRelationship(
        from_table="catalog_returns",
        to_table="customer",
        condition="catalog_returns.cr_refunded_customer_sk = customer.c_customer_sk",
        description="Khách hàng được hoàn trả tiền đơn catalog",
    ),
    JoinRelationship(
        from_table="catalog_returns",
        to_table="reason",
        condition="catalog_returns.cr_reason_sk = reason.r_reason_sk",
        description="Lý do đổi trả đơn catalog",
    ),
    # --- 7. inventory Relationships ---
    JoinRelationship(
        from_table="inventory",
        to_table="date_dim",
        condition="inventory.inv_date_sk = date_dim.d_date_sk",
        description="Thời điểm kiểm kê tồn kho",
    ),
    JoinRelationship(
        from_table="inventory",
        to_table="item",
        condition="inventory.inv_item_sk = item.i_item_sk",
        description="Sản phẩm tồn kho",
    ),
    JoinRelationship(
        from_table="inventory",
        to_table="warehouse",
        condition="inventory.inv_warehouse_sk = warehouse.w_warehouse_sk",
        description="Nhà kho lưu trữ sản phẩm",
    ),
    # --- 8. Snowflake Dimension Hierarchies ---
    JoinRelationship(
        from_table="customer",
        to_table="customer_address",
        condition="customer.c_current_addr_sk = customer_address.ca_address_sk",
        description="Khách hàng liên kết địa chỉ cư trú hiện tại (tiểu bang, thành phố)",
    ),
    JoinRelationship(
        from_table="customer",
        to_table="customer_demographics",
        condition="customer.c_current_cdemo_sk = customer_demographics.cd_demo_sk",
        description="Khách hàng liên kết đặc tính nhân khẩu học (giới tính, hôn nhân)",
    ),
    JoinRelationship(
        from_table="customer",
        to_table="household_demographics",
        condition="customer.c_current_hdemo_sk = household_demographics.hd_demo_sk",
        description="Khách hàng liên kết đặc tính hộ gia đình",
    ),
    JoinRelationship(
        from_table="household_demographics",
        to_table="income_band",
        condition="household_demographics.hd_income_band_sk = income_band.ib_income_band_sk",
        description="Hộ gia đình liên kết khung thu nhập tài chính",
    ),
]

# Quan hệ JOIN TPC-H legacy phục vụ tương thích ngược cho Metadata Tools BFS
_LEGACY_TPCH_JOINS: Final[list[JoinRelationship]] = [
    JoinRelationship(
        from_table="lineitem",
        to_table="orders",
        condition="lineitem.l_orderkey = orders.o_orderkey",
        description="Dòng hàng thuộc đơn hàng",
    ),
    JoinRelationship(
        from_table="orders",
        to_table="customer",
        condition="orders.o_custkey = customer.c_custkey",
        description="Đơn hàng được đặt bởi khách hàng",
    ),
    JoinRelationship(
        from_table="lineitem",
        to_table="part",
        condition="lineitem.l_partkey = part.p_partkey",
        description="Mặt hàng được đặt mua trong dòng hàng",
    ),
    JoinRelationship(
        from_table="lineitem",
        to_table="supplier",
        condition="lineitem.l_suppkey = supplier.s_suppkey",
        description="Nhà cung cấp xuất mặt hàng",
    ),
    JoinRelationship(
        from_table="partsupp",
        to_table="part",
        condition="partsupp.ps_partkey = part.p_partkey",
        description="Linh kiện tồn kho liên kết danh mục mặt hàng",
    ),
    JoinRelationship(
        from_table="partsupp",
        to_table="supplier",
        condition="partsupp.ps_suppkey = supplier.s_suppkey",
        description="Nhà cung cấp cung ứng linh kiện này",
    ),
    JoinRelationship(
        from_table="customer",
        to_table="nation",
        condition="customer.c_nationkey = nation.n_nationkey",
        description="Khách hàng thuộc quốc gia",
    ),
    JoinRelationship(
        from_table="supplier",
        to_table="nation",
        condition="supplier.s_nationkey = nation.n_nationkey",
        description="Nhà cung cấp thuộc quốc gia",
    ),
    JoinRelationship(
        from_table="nation",
        to_table="region",
        condition="nation.n_regionkey = region.r_regionkey",
        description="Quốc gia thuộc khu vực địa lý",
    ),
    JoinRelationship(
        from_table="lineitem",
        to_table="partsupp",
        condition="lineitem.l_partkey = partsupp.ps_partkey AND lineitem.l_suppkey = partsupp.ps_suppkey",
        description="Dòng hàng liên kết chi phí nhập tồn kho của nhà cung cấp",
    ),
]
TPCH_JOIN_RELATIONSHIPS: Final[list[JoinRelationship]] = _LEGACY_TPCH_JOINS


# ==============================================================================
# 4. CHỈ SỐ NGHIỆP VỤ BÁN LẺ CHUẨN (dbt SEMANTIC METRICS)
# ==============================================================================

TPCDS_SEMANTIC_METRICS: Final[dict[str, SemanticMetric]] = {
    "store_net_sales": SemanticMetric(
        metric_id="store_net_sales",
        vietnamese_name="Doanh thu thuần cửa hàng",
        formula="SUM(ss_net_paid)",
        description="Doanh thu thực tế sau chiết khấu từ kênh bán lẻ tại cửa hàng",
        required_tables=["store_sales"],
    ),
    "web_net_sales": SemanticMetric(
        metric_id="web_net_sales",
        vietnamese_name="Doanh thu thuần trực tuyến",
        formula="SUM(ws_net_paid)",
        description="Doanh thu thực tế sau chiết khấu từ kênh bán hàng trên website",
        required_tables=["web_sales"],
    ),
    "catalog_net_sales": SemanticMetric(
        metric_id="catalog_net_sales",
        vietnamese_name="Doanh thu thuần catalog",
        formula="SUM(cs_net_paid)",
        description="Doanh thu thực tế sau chiết khấu từ kênh bán hàng qua danh mục",
        required_tables=["catalog_sales"],
    ),
    "total_net_sales": SemanticMetric(
        metric_id="total_net_sales",
        vietnamese_name="Tổng doanh thu thuần đa kênh",
        formula="COALESCE(SUM(ss_net_paid), 0) + COALESCE(SUM(ws_net_paid), 0) + COALESCE(SUM(cs_net_paid), 0)",
        description="Tổng hợp doanh thu thuần toàn công ty trên cả 3 kênh (Store + Web + Catalog)",
        required_tables=["store_sales", "web_sales", "catalog_sales"],
    ),
    "gross_sales": SemanticMetric(
        metric_id="gross_sales",
        vietnamese_name="Doanh thu gộp",
        formula="SUM(ss_ext_sales_price)",
        description="Tổng giá trị hàng hóa theo giá niêm yết bán tại cửa hàng",
        required_tables=["store_sales"],
    ),
    "net_profit": SemanticMetric(
        metric_id="net_profit",
        vietnamese_name="Lợi nhuận ròng cửa hàng",
        formula="SUM(ss_net_profit)",
        description="Lợi nhuận ròng thực tế từ các đơn hàng tại cửa hàng",
        required_tables=["store_sales"],
    ),
    "returns_amount": SemanticMetric(
        metric_id="returns_amount",
        vietnamese_name="Tổng tiền hoàn trả",
        formula="SUM(sr_return_amt)",
        description="Tổng số tiền hoàn trả lại cho khách mua tại cửa hàng",
        required_tables=["store_returns"],
    ),
    "return_rate": SemanticMetric(
        metric_id="return_rate",
        vietnamese_name="Tỷ lệ hoàn trả",
        formula="SUM(sr_return_amt) * 100.0 / NULLIF(SUM(ss_net_paid), 0)",
        description="Tỷ lệ phần trăm giá trị đổi trả so với doanh thu bán hàng tại quầy",
        required_tables=["store_sales", "store_returns"],
    ),
    "inventory_quantity": SemanticMetric(
        metric_id="inventory_quantity",
        vietnamese_name="Số lượng tồn kho",
        formula="SUM(inv_quantity_on_hand)",
        description="Tổng số lượng sản phẩm tồn kho sẵn sàng cung cấp",
        required_tables=["inventory"],
    ),
}

# Giữ chỉ số TPC-H legacy cho tương thích ngược
_LEGACY_TPCH_METRICS: Final[dict[str, SemanticMetric]] = {
    "net_revenue": SemanticMetric(
        metric_id="net_revenue",
        vietnamese_name="Doanh thu thuần",
        formula="SUM(l_extendedprice * (1 - l_discount))",
        description="Doanh thu thực tế sau khi trừ chiết khấu",
        required_tables=["lineitem"],
    ),
    "gross_revenue": SemanticMetric(
        metric_id="gross_revenue",
        vietnamese_name="Doanh thu gộp",
        formula="SUM(l_extendedprice)",
        description="Tổng giá trị hàng hóa theo giá niêm yết chưa trừ chiết khấu",
        required_tables=["lineitem"],
    ),
    "gross_profit": SemanticMetric(
        metric_id="gross_profit",
        vietnamese_name="Lợi nhuận gộp ước tính",
        formula="SUM(l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity)",
        description="Doanh thu thực tế trừ đi chi phí nhập kho của nhà cung cấp",
        required_tables=["lineitem", "partsupp"],
    ),
}

TPCH_SEMANTIC_METRICS: Final[dict[str, SemanticMetric]] = {
    **_LEGACY_TPCH_METRICS,
    **TPCDS_SEMANTIC_METRICS,
}


# ==============================================================================
# 5. CÁC HÀM TIỆN ÍCH TRUY XUẤT VÀ RENDER SCHEMA CONTEXT
# ==============================================================================


def get_table_schema(table_name: str) -> str | None:
    """Lấy định nghĩa DDL kèm chú thích tiếng Việt cho một bảng cụ thể."""
    return TPCDS_TABLE_SCHEMAS.get(table_name.lower())


def get_all_table_schemas() -> dict[str, str]:
    """Lấy từ điển DDL của toàn bộ 24 bảng TPC-DS."""
    return dict(TPCDS_TABLE_SCHEMAS)


def get_join_relationships() -> list[JoinRelationship]:
    """Lấy danh sách tất cả các quan hệ JOIN chuẩn trong TPC-DS."""
    return list(TPCDS_JOIN_RELATIONSHIPS)


def get_semantic_metrics() -> dict[str, SemanticMetric]:
    """Lấy từ điển tất cả các chỉ số nghiệp vụ chuẩn (Semantic Metrics)."""
    return dict(TPCDS_SEMANTIC_METRICS)


def render_schema_context(selected_tables: list[str] | None = None) -> str:
    """Kết xuất ngữ cảnh lược đồ dữ liệu (Markdown) đưa vào prompt cho SQL Generator.

    Args:
        selected_tables: Danh sách bảng liên quan cần trích xuất (None = toàn bộ 24 bảng).

    Returns:
        Chuỗi Markdown chứa DDL, các điều kiện JOIN chuẩn và công thức tính toán.
    """
    tables_to_render = (
        [t.lower() for t in selected_tables if t.lower() in TPCDS_TABLE_SCHEMAS]
        if selected_tables
        else TPCDS_TABLE_NAMES
    )

    lines: list[str] = [
        "### NGỮ CẢNH LƯỢC ĐỒ CƠ SỞ DỮ LIỆU TPC-DS (24 BẢNG):",
        "> QUY TẮC BẮT BUỘC: Khi lọc điều kiện thời gian (năm, quý, tháng), BẮT BUỘC phải JOIN với bảng date_dim qua cột khóa ngày (vd: ss_sold_date_sk = d_date_sk).",
        "",
    ]

    # 1. DDL các bảng
    lines.append("#### 1. CẤU TRÚC CÁC BẢNG (DDL):")
    for tbl in tables_to_render:
        schema = TPCDS_TABLE_SCHEMAS.get(tbl)
        if schema:
            lines.append(f"```sql\n{schema}\n```\n")

    # 2. Điều kiện JOIN chuẩn giữa các bảng được chọn
    table_set = set(tables_to_render)
    relevant_joins = [
        j
        for j in TPCDS_JOIN_RELATIONSHIPS
        if j.from_table in table_set and j.to_table in table_set
    ]

    lines.append("#### 2. QUAN HỆ JOIN CHUẨN GIỮA CÁC BẢNG:")
    if relevant_joins:
        for j in relevant_joins:
            lines.append(
                f"- **{j.from_table} JOIN {j.to_table}**: `{j.condition}` ({j.description})"
            )
    else:
        for j in TPCDS_JOIN_RELATIONSHIPS:
            if j.from_table in table_set or j.to_table in table_set:
                lines.append(
                    f"- **{j.from_table} JOIN {j.to_table}**: `{j.condition}` ({j.description})"
                )
    lines.append("")

    # 3. Chỉ số nghiệp vụ chuẩn (dbt Semantic Metrics)
    lines.append("#### 3. CÔNG THỨC CHUẨN NGHIỆP VỤ BÁN LẺ (dbt SEMANTIC METRICS):")
    for metric in TPCDS_SEMANTIC_METRICS.values():
        lines.append(
            f"- **{metric.vietnamese_name}** (`{metric.metric_id}`): `{metric.formula}` — {metric.description}"
        )

    return "\n".join(lines)


__all__ = [
    "TPCDS_JOIN_RELATIONSHIPS",
    "TPCDS_SEMANTIC_METRICS",
    "TPCDS_TABLE_COLUMNS",
    "TPCDS_TABLE_NAMES",
    "TPCDS_TABLE_SCHEMAS",
    "TPCH_JOIN_RELATIONSHIPS",
    "TPCH_SEMANTIC_METRICS",
    "TPCH_TABLE_COLUMNS",
    "TPCH_TABLE_NAMES",
    "TPCH_TABLE_SCHEMAS",
    "JoinRelationship",
    "SemanticMetric",
    "get_all_table_schemas",
    "get_join_relationships",
    "get_semantic_metrics",
    "get_table_schema",
    "render_schema_context",
]
