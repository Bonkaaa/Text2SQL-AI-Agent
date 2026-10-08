export interface TPCDSTableMeta {
  name: string;
  label: string;
  description: string;
  category: "sales" | "returns" | "inventory" | "customer" | "dimension";
  primaryKey: string[];
  dateKey?: string;
  commonJoins?: string[];
}

export interface TPCDSDomainCategory {
  id: "sales" | "returns" | "inventory" | "customer" | "dimension";
  name: string;
  iconName: string;
  description: string;
  tables: TPCDSTableMeta[];
}

export const TPCDS_DOMAINS: TPCDSDomainCategory[] = [
  {
    id: "sales",
    name: "Kênh Bán Hàng (Sales Facts)",
    iconName: "ShoppingBag",
    description: "Các bảng sự kiện giao dịch bán hàng đa kênh Omnichannel",
    tables: [
      {
        name: "store_sales",
        label: "Bán tại Cửa hàng",
        description: "Giao dịch bán lẻ trực tiếp tại các cửa hàng vật lý",
        category: "sales",
        primaryKey: ["ss_item_sk", "ss_ticket_number"],
        dateKey: "ss_sold_date_sk",
        commonJoins: ["date_dim", "store", "item", "customer"],
      },
      {
        name: "web_sales",
        label: "Bán qua Web/Online",
        description: "Giao dịch bán lẻ qua sàn thương mại điện tử trực tuyến",
        category: "sales",
        primaryKey: ["ws_item_sk", "ws_order_number"],
        dateKey: "ws_sold_date_sk",
        commonJoins: ["date_dim", "web_site", "web_page", "item", "customer"],
      },
      {
        name: "catalog_sales",
        label: "Bán qua Catalog",
        description: "Giao dịch bán hàng qua thư chào hàng/catalog giấy",
        category: "sales",
        primaryKey: ["cs_item_sk", "cs_order_number"],
        dateKey: "cs_sold_date_sk",
        commonJoins: ["date_dim", "catalog_page", "call_center", "item", "customer"],
      },
    ],
  },
  {
    id: "returns",
    name: "Kênh Hoàn Hàng (Returns Facts)",
    iconName: "Undo2",
    description: "Sự kiện trả hàng và hoàn tiền đa kênh",
    tables: [
      {
        name: "store_returns",
        label: "Hoàn hàng Cửa hàng",
        description: "Giao dịch khách hàng trả hàng tại cửa hàng",
        category: "returns",
        primaryKey: ["sr_item_sk", "sr_ticket_number"],
        dateKey: "sr_returned_date_sk",
        commonJoins: ["date_dim", "store", "item", "customer", "reason"],
      },
      {
        name: "web_returns",
        label: "Hoàn hàng Web",
        description: "Giao dịch hoàn trả đơn mua qua website",
        category: "returns",
        primaryKey: ["wr_item_sk", "wr_order_number"],
        dateKey: "wr_returned_date_sk",
        commonJoins: ["date_dim", "web_page", "item", "customer", "reason"],
      },
      {
        name: "catalog_returns",
        label: "Hoàn hàng Catalog",
        description: "Giao dịch hoàn trả đơn mua qua catalog",
        category: "returns",
        primaryKey: ["cr_item_sk", "cr_order_number"],
        dateKey: "cr_returned_date_sk",
        commonJoins: ["date_dim", "catalog_page", "item", "customer", "reason"],
      },
    ],
  },
  {
    id: "inventory",
    name: "Kho & Tồn Kho (Inventory)",
    iconName: "Warehouse",
    description: "Số lượng tồn kho theo tuần và các trung tâm phân phối",
    tables: [
      {
        name: "inventory",
        label: "Tồn kho Hàng tuần",
        description: "Ảnh chụp lượng tồn kho theo từng mặt hàng và kho",
        category: "inventory",
        primaryKey: ["inv_date_sk", "inv_item_sk", "inv_warehouse_sk"],
        dateKey: "inv_date_sk",
        commonJoins: ["date_dim", "item", "warehouse"],
      },
      {
        name: "warehouse",
        label: "Danh mục Kho hàng",
        description: "Thông tin vị trí, kích thước kho phân phối",
        category: "inventory",
        primaryKey: ["w_warehouse_sk"],
      },
    ],
  },
  {
    id: "customer",
    name: "Khách Hàng & Nhân Sự",
    iconName: "Users",
    description: "Hồ sơ khách hàng, nhân khẩu học và địa chỉ liên lạc",
    tables: [
      {
        name: "customer",
        label: "Khách hàng",
        description: "Thông tin cá nhân (chứa các cột PII được bảo vệ)",
        category: "customer",
        primaryKey: ["c_customer_sk"],
        commonJoins: ["customer_address", "customer_demographics", "household_demographics"],
      },
      {
        name: "customer_address",
        label: "Địa chỉ Khách hàng",
        description: "Bang, thành phố, hạt, mã bưu chính",
        category: "customer",
        primaryKey: ["ca_address_sk"],
      },
      {
        name: "customer_demographics",
        label: "Nhân khẩu học",
        description: "Giới tính, tình trạng hôn nhân, trình độ học vấn",
        category: "customer",
        primaryKey: ["cd_demo_sk"],
      },
      {
        name: "household_demographics",
        label: "Nhân khẩu Hộ gia đình",
        description: "Quy mô hộ, khoảng thu nhập, số lượng phương tiện",
        category: "customer",
        primaryKey: ["hd_demo_sk"],
        commonJoins: ["income_band"],
      },
    ],
  },
  {
    id: "dimension",
    name: "Chiều Bán Lẻ & Thời Gian",
    iconName: "Calendar",
    description: "Các bảng chiều (Dimensions) phục vụ cắt lát số liệu phân tích",
    tables: [
      {
        name: "date_dim",
        label: "Chiều Ngày tháng",
        description: "Năm, quý, tháng, tuần, ngày trong tuần, ngày lễ",
        category: "dimension",
        primaryKey: ["d_date_sk"],
      },
      {
        name: "time_dim",
        label: "Chiều Giờ giấc",
        description: "Giờ, phút, giây, ca bán hàng",
        category: "dimension",
        primaryKey: ["t_time_sk"],
      },
      {
        name: "item",
        label: "Sản phẩm / Mặt hàng",
        description: "Mã SKU, danh mục (Category), nhóm hàng (Class), thương hiệu",
        category: "dimension",
        primaryKey: ["i_item_sk"],
      },
      {
        name: "store",
        label: "Cửa hàng bán lẻ",
        description: "Thông tin cửa hàng, diện tích, người quản lý, địa lý",
        category: "dimension",
        primaryKey: ["s_store_sk"],
      },
      {
        name: "promotion",
        label: "Chương trình Khuyến mãi",
        description: "Tên chiến dịch, hình thức giảm giá, thời gian hiệu lực",
        category: "dimension",
        primaryKey: ["p_promo_sk"],
      },
      {
        name: "call_center",
        label: "Trung tâm Cuộc gọi",
        description: "Call center phụ trách bán hàng catalog",
        category: "dimension",
        primaryKey: ["cc_call_center_sk"],
      },
      {
        name: "catalog_page",
        label: "Trang Catalog",
        description: "Số trang catalog, loại catalog",
        category: "dimension",
        primaryKey: ["cp_catalog_page_sk"],
      },
      {
        name: "web_site",
        label: "Trang Web Bán lẻ",
        description: "Cổng thương mại điện tử, múi giờ",
        category: "dimension",
        primaryKey: ["web_site_sk"],
      },
      {
        name: "web_page",
        label: "Trang con Web",
        description: "Trang sản phẩm, trang checkout",
        category: "dimension",
        primaryKey: ["wp_web_page_sk"],
      },
      {
        name: "ship_mode",
        label: "Phương thức Vận chuyển",
        description: "Đơn vị vận chuyển, loại dịch vụ",
        category: "dimension",
        primaryKey: ["sm_ship_mode_sk"],
      },
      {
        name: "reason",
        label: "Lý do Trả hàng",
        description: "Mô tả lý do đổi trả hàng của khách",
        category: "dimension",
        primaryKey: ["r_reason_sk"],
      },
      {
        name: "income_band",
        label: "Khoảng Thu nhập",
        description: "Mức thu nhập thấp nhất - cao nhất",
        category: "dimension",
        primaryKey: ["ib_income_band_sk"],
      },
    ],
  },
];

export const TOTAL_TPCDS_TABLES_COUNT = 24;

export interface TPCDSColumnMeta {
  name: string;
  type: string;
  description: string;
  isPrimaryKey?: boolean;
  isForeignKey?: boolean;
  references?: string;
  isPii?: boolean;
}

// Bảng từ điển cột chi tiết cho các bảng TPC-DS phổ biến
const TABLE_COLUMNS_MAP: Record<string, TPCDSColumnMeta[]> = {
  store_sales: [
    { name: "ss_item_sk", type: "INTEGER", description: "Mã định danh mặt hàng (SKU)", isPrimaryKey: true, isForeignKey: true, references: "item.i_item_sk" },
    { name: "ss_ticket_number", type: "BIGINT", description: "Số vé hóa đơn bán lẻ", isPrimaryKey: true },
    { name: "ss_sold_date_sk", type: "INTEGER", description: "Khóa ngày bán hàng", isForeignKey: true, references: "date_dim.d_date_sk" },
    { name: "ss_customer_sk", type: "INTEGER", description: "Khóa khách hàng", isForeignKey: true, references: "customer.c_customer_sk" },
    { name: "ss_store_sk", type: "INTEGER", description: "Khóa cửa hàng", isForeignKey: true, references: "store.s_store_sk" },
    { name: "ss_quantity", type: "INTEGER", description: "Số lượng mặt hàng bán ra" },
    { name: "ss_sales_price", type: "DECIMAL(7,2)", description: "Đơn giá bán thực tế" },
    { name: "ss_net_paid", type: "DECIMAL(7,2)", description: "Doanh thu thuần đã trừ giảm giá" },
    { name: "ss_net_profit", type: "DECIMAL(7,2)", description: "Lợi nhuận ròng sau chi phí" },
  ],
  web_sales: [
    { name: "ws_item_sk", type: "INTEGER", description: "Mã mặt hàng trực tuyến", isPrimaryKey: true, isForeignKey: true, references: "item.i_item_sk" },
    { name: "ws_order_number", type: "BIGINT", description: "Số đơn hàng trực tuyến", isPrimaryKey: true },
    { name: "ws_sold_date_sk", type: "INTEGER", description: "Khóa ngày bán web", isForeignKey: true, references: "date_dim.d_date_sk" },
    { name: "ws_bill_customer_sk", type: "INTEGER", description: "Khách hàng thanh toán", isForeignKey: true, references: "customer.c_customer_sk" },
    { name: "ws_web_page_sk", type: "INTEGER", description: "Khóa trang web", isForeignKey: true, references: "web_page.wp_web_page_sk" },
    { name: "ws_net_paid", type: "DECIMAL(7,2)", description: "Doanh thu thuần kênh Web" },
    { name: "ws_net_profit", type: "DECIMAL(7,2)", description: "Lợi nhuận ròng kênh Web" },
  ],
  catalog_sales: [
    { name: "cs_item_sk", type: "INTEGER", description: "Mã mặt hàng catalog", isPrimaryKey: true, isForeignKey: true, references: "item.i_item_sk" },
    { name: "cs_order_number", type: "BIGINT", description: "Số đơn hàng catalog", isPrimaryKey: true },
    { name: "cs_sold_date_sk", type: "INTEGER", description: "Khóa ngày bán catalog", isForeignKey: true, references: "date_dim.d_date_sk" },
    { name: "cs_bill_customer_sk", type: "INTEGER", description: "Khách hàng đặt hàng", isForeignKey: true, references: "customer.c_customer_sk" },
    { name: "cs_net_paid", type: "DECIMAL(7,2)", description: "Doanh thu thuần kênh Catalog" },
    { name: "cs_net_profit", type: "DECIMAL(7,2)", description: "Lợi nhuận ròng kênh Catalog" },
  ],
  customer: [
    { name: "c_customer_sk", type: "INTEGER", description: "Khóa chính khách hàng", isPrimaryKey: true },
    { name: "c_customer_id", type: "CHAR(16)", description: "Mã định danh khách hàng tự nhiên" },
    { name: "c_first_name", type: "VARCHAR(20)", description: "Tên khách hàng", isPii: true },
    { name: "c_last_name", type: "VARCHAR(30)", description: "Họ và tên đệm khách hàng", isPii: true },
    { name: "c_email_address", type: "VARCHAR(50)", description: "Địa chỉ thư điện tử cá nhân", isPii: true },
    { name: "c_birth_year", type: "INTEGER", description: "Năm sinh" },
    { name: "c_current_addr_sk", type: "INTEGER", description: "Khóa địa chỉ", isForeignKey: true, references: "customer_address.ca_address_sk" },
  ],
  customer_address: [
    { name: "ca_address_sk", type: "INTEGER", description: "Khóa chính địa chỉ", isPrimaryKey: true },
    { name: "ca_street_number", type: "CHAR(10)", description: "Số nhà", isPii: true },
    { name: "ca_street_name", type: "VARCHAR(60)", description: "Tên đường phố", isPii: true },
    { name: "ca_city", type: "VARCHAR(60)", description: "Thành phố" },
    { name: "ca_state", type: "CHAR(2)", description: "Mã tiểu bang" },
    { name: "ca_zip", type: "CHAR(10)", description: "Mã bưu chính" },
  ],
  date_dim: [
    { name: "d_date_sk", type: "INTEGER", description: "Khóa chính ngày tháng", isPrimaryKey: true },
    { name: "d_date_id", type: "CHAR(16)", description: "Chuỗi ngày định dạng YYYY-MM-DD" },
    { name: "d_date", type: "DATE", description: "Giá trị ngày thực tế" },
    { name: "d_year", type: "INTEGER", description: "Năm tài chính / dương lịch (VD: 1998 - 2002)" },
    { name: "d_moy", type: "INTEGER", description: "Tháng trong năm (1 - 12)" },
    { name: "d_qoy", type: "INTEGER", description: "Quý trong năm (1 - 4)" },
    { name: "d_weekend", type: "CHAR(1)", description: "Cờ ngày cuối tuần (Y/N)" },
  ],
  item: [
    { name: "i_item_sk", type: "INTEGER", description: "Khóa chính sản phẩm", isPrimaryKey: true },
    { name: "i_item_id", type: "CHAR(16)", description: "Mã SKU sản phẩm" },
    { name: "i_item_desc", type: "VARCHAR(200)", description: "Mô tả chi tiết sản phẩm" },
    { name: "i_current_price", type: "DECIMAL(7,2)", description: "Giá niêm yết hiện tại" },
    { name: "i_category", type: "VARCHAR(50)", description: "Danh mục ngành hàng (Electronics, Books...)" },
    { name: "i_class", type: "VARCHAR(50)", description: "Nhóm phân loại sản phẩm" },
    { name: "i_brand", type: "VARCHAR(50)", description: "Thương hiệu sản xuất" },
  ],
  store: [
    { name: "s_store_sk", type: "INTEGER", description: "Khóa chính cửa hàng", isPrimaryKey: true },
    { name: "s_store_id", type: "CHAR(16)", description: "Mã cửa hàng" },
    { name: "s_store_name", type: "VARCHAR(50)", description: "Tên chi nhánh cửa hàng" },
    { name: "s_number_employees", type: "INTEGER", description: "Số lượng nhân viên" },
    { name: "s_city", type: "VARCHAR(60)", description: "Thành phố đặt cửa hàng" },
    { name: "s_state", type: "CHAR(2)", description: "Tiểu bang" },
  ],
};

/**
 * Lấy toàn bộ thông tin chi tiết của một bảng TPC-DS kèm danh sách cột
 */
export function getTableDetails(tableName: string): (TPCDSTableMeta & { columns: TPCDSColumnMeta[] }) | null {
  for (const domain of TPCDS_DOMAINS) {
    const found = domain.tables.find((t) => t.name.toLowerCase() === tableName.toLowerCase());
    if (found) {
      const columns = TABLE_COLUMNS_MAP[found.name] || [
        {
          name: `${found.name.slice(0, 3)}_sk`,
          type: "INTEGER",
          description: `Khóa chính bảng ${found.name}`,
          isPrimaryKey: true,
        },
      ];
      return {
        ...found,
        columns,
      };
    }
  }
  return null;
}
