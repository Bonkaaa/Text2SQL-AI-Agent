import { TableMetadata, TableCategory } from "@/types/schema";

export const TPCH_TABLES: TableMetadata[] = [
  // 1. Transactions (2)
  {
    name: "orders",
    displayName: "Orders (Đơn hàng)",
    category: "transactions",
    categoryLabel: "Giao dịch & Đơn hàng",
    rowCountEstimate: 1500000,
    description: "Lưu trữ thông tin đơn đặt hàng của khách hàng, bao gồm ngày đặt, tổng tiền, trạng thái và mức độ ưu tiên xử lý.",
    primaryKey: ["o_orderkey"],
    sampleQuestions: [
      "Tổng số đơn hàng được đặt theo từng năm?",
      "Top 5 đơn hàng có tổng giá trị lớn nhất trong năm 1995?",
      "Thống kê số lượng đơn hàng theo từng trạng thái đơn hàng (order status)?",
    ],
    columns: [
      { name: "o_orderkey", type: "BIGINT", nullable: false, isPrimaryKey: true, description: "Khóa chính định danh đơn hàng" },
      { name: "o_custkey", type: "BIGINT", nullable: false, isForeignKey: true, references: "customer.c_custkey", description: "Khóa ngoại khách hàng đặt hàng" },
      { name: "o_orderstatus", type: "CHAR(1)", nullable: false, description: "Trạng thái đơn hàng: O (Open), F (Fulfilled), P (Pending)" },
      { name: "o_totalprice", type: "DECIMAL(15,2)", nullable: false, description: "Tổng giá trị đơn hàng tính cả thuế và chiết khấu" },
      { name: "o_orderdate", type: "DATE", nullable: false, description: "Ngày khách hàng tạo đơn hàng" },
      { name: "o_orderpriority", type: "VARCHAR(15)", nullable: false, description: "Mức độ ưu tiên: 1-URGENT, 2-HIGH, 3-MEDIUM, 4-NOT SPECIFIED, 5-LOW" },
      { name: "o_clerk", type: "VARCHAR(15)", nullable: false, description: "Mã định danh nhân viên phụ trách lập đơn hàng" },
      { name: "o_shippriority", type: "INTEGER", nullable: false, description: "Mức độ ưu tiên giao hàng" },
      { name: "o_comment", type: "VARCHAR(79)", nullable: false, description: "Ghi chú bổ sung về đơn đặt hàng" },
    ],
  },
  {
    name: "lineitem",
    displayName: "Lineitem (Chi tiết mặt hàng đơn hàng)",
    category: "transactions",
    categoryLabel: "Giao dịch & Đơn hàng",
    rowCountEstimate: 6000000,
    description: "Bảng chi tiết chứa từng dòng mặt hàng trong đơn hàng, ngày xuất xưởng, cam kết giao, nhận hàng, chiết khấu và thuế.",
    primaryKey: ["l_orderkey", "l_linenumber"],
    sampleQuestions: [
      "Tổng doanh thu thuần (extendedprice * (1 - discount)) của toàn bộ hệ thống?",
      "Số lượng đơn hàng bị trễ hạn giao (receiptdate > commitdate)?",
      "Doanh thu thuần của các mặt hàng được giao bằng tàu biển (shipmode = 'SHIP')?",
    ],
    columns: [
      { name: "l_orderkey", type: "BIGINT", nullable: false, isPrimaryKey: true, isForeignKey: true, references: "orders.o_orderkey", description: "Khóa ngoại đơn hàng tương ứng" },
      { name: "l_partkey", type: "BIGINT", nullable: false, isForeignKey: true, references: "part.p_partkey", description: "Khóa ngoại linh kiện sản phẩm" },
      { name: "l_suppkey", type: "BIGINT", nullable: false, isForeignKey: true, references: "supplier.s_suppkey", description: "Khóa ngoại nhà cung cấp cung ứng" },
      { name: "l_linenumber", type: "INTEGER", nullable: false, isPrimaryKey: true, description: "Số thứ tự dòng sản phẩm trong đơn hàng" },
      { name: "l_quantity", type: "DECIMAL(15,2)", nullable: false, description: "Số lượng sản phẩm đặt mua" },
      { name: "l_extendedprice", type: "DECIMAL(15,2)", nullable: false, description: "Tổng giá niêm yết chưa áp dụng chiết khấu" },
      { name: "l_discount", type: "DECIMAL(15,2)", nullable: false, description: "Tỷ lệ chiết khấu giảm giá (0.00 đến 1.00)" },
      { name: "l_tax", type: "DECIMAL(15,2)", nullable: false, description: "Tỷ lệ thuế giá trị gia tăng áp dụng" },
      { name: "l_returnflag", type: "CHAR(1)", nullable: false, description: "Trạng thái hoàn trả: R (Returned), A (Accepted), N (None)" },
      { name: "l_linestatus", type: "CHAR(1)", nullable: false, description: "Trạng thái xử lý dòng đơn hàng: O (Open), F (Fulfilled)" },
      { name: "l_shipdate", type: "DATE", nullable: false, description: "Ngày linh kiện thực tế xuất kho vận chuyển" },
      { name: "l_commitdate", type: "DATE", nullable: false, description: "Ngày nhà cung cấp cam kết giao hàng tới khách" },
      { name: "l_receiptdate", type: "DATE", nullable: false, description: "Ngày khách hàng thực tế ký nhận hàng" },
      { name: "l_shipinstruct", type: "VARCHAR(25)", nullable: false, description: "Chỉ dẫn đặc biệt trong khâu vận chuyển hàng" },
      { name: "l_shipmode", type: "VARCHAR(10)", nullable: false, description: "Phương thức vận chuyển: AIR, REG AIR, SHIP, TRUCK, RAIL, MAIL, FOB" },
      { name: "l_comment", type: "VARCHAR(44)", nullable: false, description: "Ghi chú điều khoản vận chuyển dòng hàng" },
    ],
  },

  // 2. Products & Inventory (2)
  {
    name: "part",
    displayName: "Part (Linh kiện & Sản phẩm)",
    category: "products_inventory",
    categoryLabel: "Sản phẩm & Tồn kho",
    rowCountEstimate: 200000,
    description: "Danh mục linh kiện thiết bị trong chuỗi cung ứng, phân loại theo nhà sản xuất, nhãn hàng, quy cách và giá bán lẻ niêm yết.",
    primaryKey: ["p_partkey"],
    sampleQuestions: [
      "Giá bán lẻ trung bình của linh kiện theo từng nhà sản xuất (mfgr)?",
      "Top 5 thương hiệu linh kiện (brand) có nhiều sản phẩm nhất?",
      "Số lượng linh kiện có kích thước (size) lớn hơn 40?",
    ],
    columns: [
      { name: "p_partkey", type: "BIGINT", nullable: false, isPrimaryKey: true, description: "Khóa chính linh kiện" },
      { name: "p_name", type: "VARCHAR(55)", nullable: false, description: "Tên thương mại linh kiện" },
      { name: "p_mfgr", type: "VARCHAR(25)", nullable: false, description: "Nhà sản xuất gia công linh kiện" },
      { name: "p_brand", type: "VARCHAR(10)", nullable: false, description: "Thương hiệu sản phẩm" },
      { name: "p_type", type: "VARCHAR(25)", nullable: false, description: "Loại linh kiện và chất liệu cấu thành" },
      { name: "p_size", type: "INTEGER", nullable: false, description: "Kích thước linh kiện" },
      { name: "p_container", type: "VARCHAR(10)", nullable: false, description: "Quy cách đóng gói bao bì vận chuyển: SM CASE, JUMBO BOX, ..." },
      { name: "p_retailprice", type: "DECIMAL(15,2)", nullable: false, description: "Giá bán lẻ tiêu chuẩn của linh kiện" },
      { name: "p_comment", type: "VARCHAR(23)", nullable: false, description: "Ghi chú bổ sung thông số linh kiện" },
    ],
  },
  {
    name: "partsupp",
    displayName: "PartSupp (Tồn kho & Cung ứng)",
    category: "products_inventory",
    categoryLabel: "Sản phẩm & Tồn kho",
    rowCountEstimate: 800000,
    description: "Mối quan hệ liên kết linh kiện và nhà cung cấp, phản ánh số lượng tồn kho khả dụng và đơn giá vốn cung ứng.",
    primaryKey: ["ps_partkey", "ps_suppkey"],
    sampleQuestions: [
      "Tổng số lượng linh kiện có sẵn (availqty) trong kho của tất cả nhà cung cấp?",
      "Top 5 nhà cung cấp có tổng giá trị hàng tồn kho (availqty * supplycost) lớn nhất?",
      "Giá vốn cung ứng trung bình theo từng linh kiện?",
    ],
    columns: [
      { name: "ps_partkey", type: "BIGINT", nullable: false, isPrimaryKey: true, isForeignKey: true, references: "part.p_partkey", description: "Khóa ngoại linh kiện" },
      { name: "ps_suppkey", type: "BIGINT", nullable: false, isPrimaryKey: true, isForeignKey: true, references: "supplier.s_suppkey", description: "Khóa ngoại nhà cung cấp" },
      { name: "ps_availqty", type: "INTEGER", nullable: false, description: "Số lượng linh kiện thực tế còn trong kho khả dụng" },
      { name: "ps_supplycost", type: "DECIMAL(15,2)", nullable: false, description: "Giá vốn nhà cung cấp chào bán cho một đơn vị linh kiện" },
      { name: "ps_comment", type: "VARCHAR(199)", nullable: false, description: "Ghi chú hợp đồng cung ứng và năng lực kho bãi" },
    ],
  },

  // 3. Partners & Customers (2)
  {
    name: "customer",
    displayName: "Customer (Khách hàng)",
    category: "partners_customers",
    categoryLabel: "Đối tác & Khách hàng",
    rowCountEstimate: 150000,
    description: "Hồ sơ đối tác khách hàng thương mại B2B/B2C, phân khúc thị trường hoạt động, quốc gia cư trú và số dư công nợ.",
    primaryKey: ["c_custkey"],
    sampleQuestions: [
      "Số lượng khách hàng theo từng phân khúc thị trường (mktsegment)?",
      "Danh sách 5 quốc gia có nhiều khách hàng nhất?",
      "Top 5 khách hàng có tổng chi tiêu đơn hàng lớn nhất?",
    ],
    columns: [
      { name: "c_custkey", type: "BIGINT", nullable: false, isPrimaryKey: true, description: "Khóa chính định danh khách hàng" },
      { name: "c_name", type: "VARCHAR(25)", nullable: false, description: "Tên pháp nhân hoặc tên khách hàng (Cột PII)" },
      { name: "c_address", type: "VARCHAR(40)", nullable: false, description: "Địa chỉ trụ sở khách hàng (Cột PII)" },
      { name: "c_nationkey", type: "BIGINT", nullable: false, isForeignKey: true, references: "nation.n_nationkey", description: "Khóa ngoại quốc gia cư trú" },
      { name: "c_phone", type: "VARCHAR(15)", nullable: false, description: "Số điện thoại liên lạc khách hàng (Cột PII)" },
      { name: "c_acctbal", type: "DECIMAL(15,2)", nullable: false, description: "Số dư tài khoản công nợ của khách hàng" },
      { name: "c_mktsegment", type: "VARCHAR(10)", nullable: false, description: "Phân khúc thị trường: AUTOMOBILE, BUILDING, FURNITURE, HOUSEHOLD, MACHINERY" },
      { name: "c_comment", type: "VARCHAR(117)", nullable: false, description: "Ghi chú lịch sử giao dịch và đánh giá tín dụng" },
    ],
  },
  {
    name: "supplier",
    displayName: "Supplier (Nhà cung cấp)",
    category: "partners_customers",
    categoryLabel: "Đối tác & Khách hàng",
    rowCountEstimate: 10000,
    description: "Thông tin mạng lưới nhà cung cấp nguyên vật liệu và linh kiện cơ khí, số dư thanh toán công nợ và địa chỉ liên lạc.",
    primaryKey: ["s_suppkey"],
    sampleQuestions: [
      "Số lượng nhà cung cấp theo từng quốc gia?",
      "Top 5 nhà cung cấp có số dư tài khoản (acctbal) cao nhất?",
      "Số lượng nhà cung cấp tại từng khu vực (region)?",
    ],
    columns: [
      { name: "s_suppkey", type: "BIGINT", nullable: false, isPrimaryKey: true, description: "Khóa chính định danh nhà cung cấp" },
      { name: "s_name", type: "VARCHAR(25)", nullable: false, description: "Tên thương mại của nhà cung cấp" },
      { name: "s_address", type: "VARCHAR(40)", nullable: false, description: "Địa chỉ xưởng sản xuất hoặc văn phòng (Cột PII)" },
      { name: "s_nationkey", type: "BIGINT", nullable: false, isForeignKey: true, references: "nation.n_nationkey", description: "Khóa ngoại quốc gia đặt nhà máy" },
      { name: "s_phone", type: "VARCHAR(15)", nullable: false, description: "Số điện thoại liên hệ nhà cung cấp (Cột PII)" },
      { name: "s_acctbal", type: "DECIMAL(15,2)", nullable: false, description: "Số dư công nợ phải trả cho nhà cung cấp" },
      { name: "s_comment", type: "VARCHAR(101)", nullable: false, description: "Ghi chú đánh giá độ tin cậy và tiến độ giao hàng" },
    ],
  },

  // 4. Geography (2)
  {
    name: "nation",
    displayName: "Nation (Quốc gia)",
    category: "geography",
    categoryLabel: "Khu vực Địa lý",
    rowCountEstimate: 25,
    description: "Bảng danh mục 25 quốc gia thành viên trong mạng lưới chuỗi cung ứng toàn cầu, thuộc các khu vực kinh tế lớn.",
    primaryKey: ["n_nationkey"],
    sampleQuestions: [
      "Danh sách 25 quốc gia trong hệ thống?",
      "Số lượng khách hàng và nhà cung cấp ở từng quốc gia?",
      "Tổng doanh thu bán hàng của khách hàng tại quốc gia 'GERMANY'?",
    ],
    columns: [
      { name: "n_nationkey", type: "BIGINT", nullable: false, isPrimaryKey: true, description: "Khóa chính định danh quốc gia" },
      { name: "n_name", type: "VARCHAR(25)", nullable: false, description: "Tên quốc gia (ví dụ: VIETNAM, CHINA, JAPAN, GERMANY, UNITED STATES)" },
      { name: "n_regionkey", type: "BIGINT", nullable: false, isForeignKey: true, references: "region.r_regionkey", description: "Khóa ngoại liên kết tới khu vực/châu lục" },
      { name: "n_comment", type: "VARCHAR(152)", nullable: false, description: "Mô tả đặc điểm kinh tế và chính sách hải quan quốc gia" },
    ],
  },
  {
    name: "region",
    displayName: "Region (Khu vực / Châu lục)",
    category: "geography",
    categoryLabel: "Khu vực Địa lý",
    rowCountEstimate: 5,
    description: "5 khu vực kinh tế và địa lý lớn trên thế giới: AFRICA, AMERICA, ASIA, EUROPE, MIDDLE EAST.",
    primaryKey: ["r_regionkey"],
    sampleQuestions: [
      "Doanh thu bán hàng theo từng khu vực (region)?",
      "Số lượng khách hàng tại từng khu vực (region)?",
      "Tổng doanh thu bán hàng cho khách hàng tại khu vực 'ASIA'?",
    ],
    columns: [
      { name: "r_regionkey", type: "BIGINT", nullable: false, isPrimaryKey: true, description: "Khóa chính định danh khu vực địa lý" },
      { name: "r_name", type: "VARCHAR(25)", nullable: false, description: "Tên khu vực: AFRICA, AMERICA, ASIA, EUROPE, MIDDLE EAST" },
      { name: "r_comment", type: "VARCHAR(152)", nullable: false, description: "Ghi chú chiến lược phát triển thị trường theo khu vực" },
    ],
  },
];

export function getTablesByCategory(category: TableCategory): TableMetadata[] {
  return TPCH_TABLES.filter((t) => t.category === category);
}

export function searchTables(query: string): TableMetadata[] {
  const q = query.trim().toLowerCase();
  if (!q) return TPCH_TABLES;

  return TPCH_TABLES.filter(
    (t) =>
      t.name.toLowerCase().includes(q) ||
      t.displayName.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.categoryLabel.toLowerCase().includes(q) ||
      t.columns.some((c) => c.name.toLowerCase().includes(q) || c.description.toLowerCase().includes(q))
  );
}

export function getTableByName(name: string): TableMetadata | undefined {
  return TPCH_TABLES.find((t) => t.name.toLowerCase() === name.toLowerCase());
}
