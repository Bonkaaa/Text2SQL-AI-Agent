/**
 * Metadata từ điển dữ liệu chuẩn TPC-H Benchmark (8 bảng) và Semantic Metrics.
 * Phục vụ tra cứu cho người dùng nghiệp vụ và nhà phân tích dữ liệu.
 */

export interface ColumnDefinition {
  name: string;
  type: string;
  description: string;
  isPk?: boolean;
  isFk?: boolean;
  fkTarget?: string;
  isPii?: boolean;
}

export interface TableDefinition {
  name: string;
  displayName: string;
  description: string;
  estimatedRows: string;
  columns: ColumnDefinition[];
}

export interface MetricDefinition {
  id: string;
  name: string;
  businessMeaning: string;
  formulaSql: string;
  tablesUsed: string[];
}

export const TPCH_TABLES: TableDefinition[] = [
  {
    name: "lineitem",
    displayName: "Chi Tiết Dòng Hàng",
    description: "Bảng dữ liệu giao dịch lớn nhất, ghi nhận chi tiết từng dòng sản phẩm trong đơn đặt hàng, chiết khấu và thuế.",
    estimatedRows: "~60,000 dòng (SF-0.01) / ~6M dòng (SF-1)",
    columns: [
      { name: "l_orderkey", type: "INTEGER", description: "Mã đơn hàng", isPk: true, isFk: true, fkTarget: "orders.o_orderkey" },
      { name: "l_partkey", type: "INTEGER", description: "Mã linh kiện/sản phẩm", isPk: true, isFk: true, fkTarget: "part.p_partkey" },
      { name: "l_suppkey", type: "INTEGER", description: "Mã nhà cung cấp", isPk: true, isFk: true, fkTarget: "supplier.s_suppkey" },
      { name: "l_linenumber", type: "INTEGER", description: "Số thứ tự dòng trong đơn hàng", isPk: true },
      { name: "l_quantity", type: "DECIMAL(15,2)", description: "Số lượng sản phẩm đặt mua" },
      { name: "l_extendedprice", type: "DECIMAL(15,2)", description: "Tổng giá niêm yết (chưa trừ chiết khấu)" },
      { name: "l_discount", type: "DECIMAL(15,2)", description: "Tỷ lệ chiết khấu (ví dụ: 0.05 = 5%)" },
      { name: "l_tax", type: "DECIMAL(15,2)", description: "Tỷ lệ thuế áp dụng" },
      { name: "l_returnflag", type: "CHAR(1)", description: "Cờ trạng thái hoàn hàng (R: Returned, A: Accepted, N: Normal)" },
      { name: "l_linestatus", type: "CHAR(1)", description: "Trạng thái dòng đơn hàng (O: Open, F: Fulfilled)" },
      { name: "l_shipdate", type: "DATE", description: "Ngày xuất hàng" },
      { name: "l_commitdate", type: "DATE", description: "Ngày cam kết giao hàng" },
      { name: "l_receiptdate", type: "DATE", description: "Ngày khách hàng thực tế nhận hàng" },
      { name: "l_shipinstruct", type: "VARCHAR(25)", description: "Chỉ dẫn giao hàng đặc biệt" },
      { name: "l_shipmode", type: "VARCHAR(10)", description: "Phương thức vận chuyển (AIR, REG AIR, SHIP, TRUCK, MAIL...)" },
    ],
  },
  {
    name: "orders",
    displayName: "Đơn Đặt Hàng",
    description: "Lưu trữ thông tin tổng quan của từng đơn đặt hàng từ khách hàng, ngày đặt và độ ưu tiên đơn hàng.",
    estimatedRows: "~15,000 dòng (SF-0.01) / ~1.5M dòng (SF-1)",
    columns: [
      { name: "o_orderkey", type: "INTEGER", description: "Mã định danh đơn đặt hàng", isPk: true },
      { name: "o_custkey", type: "INTEGER", description: "Mã khách hàng đặt đơn", isFk: true, fkTarget: "customer.c_custkey" },
      { name: "o_orderstatus", type: "CHAR(1)", description: "Trạng thái đơn hàng (F: Đã xong, O: Đang mở, P: Đang xử lý)" },
      { name: "o_totalprice", type: "DECIMAL(15,2)", description: "Tổng giá trị thanh toán của đơn hàng" },
      { name: "o_orderdate", type: "DATE", description: "Ngày tạo đơn đặt hàng" },
      { name: "o_orderpriority", type: "VARCHAR(15)", description: "Độ ưu tiên đơn (1-URGENT, 2-HIGH, 3-MEDIUM...)" },
      { name: "o_clerk", type: "VARCHAR(15)", description: "Mã nhân viên xử lý đơn" },
      { name: "o_shippriority", type: "INTEGER", description: "Thứ tự ưu tiên vận chuyển" },
    ],
  },
  {
    name: "customer",
    displayName: "Khách Hàng",
    description: "Danh sách khách hàng thương mại, phân khúc thị trường và thông tin liên hệ.",
    estimatedRows: "~1,500 dòng (SF-0.01) / ~150K dòng (SF-1)",
    columns: [
      { name: "c_custkey", type: "INTEGER", description: "Mã định danh khách hàng", isPk: true },
      { name: "c_name", type: "VARCHAR(25)", description: "Tên khách hàng" },
      { name: "c_address", type: "VARCHAR(40)", description: "Địa chỉ trụ sở khách hàng" },
      { name: "c_nationkey", type: "INTEGER", description: "Mã quốc gia", isFk: true, fkTarget: "nation.n_nationkey" },
      { name: "c_phone", type: "VARCHAR(15)", description: "Số điện thoại liên hệ", isPii: true },
      { name: "c_acctbal", type: "DECIMAL(15,2)", description: "Số dư tài khoản tín dụng", isPii: true },
      { name: "c_mktsegment", type: "VARCHAR(10)", description: "Phân khúc thị trường (AUTOMOBILE, BUILDING, FURNITURE, MACHINERY, HOUSEHOLD)" },
    ],
  },
  {
    name: "part",
    displayName: "Danh Mục Sản Phẩm",
    description: "Thông tin quy cách, vật liệu và giá bán lẻ niêm yết của các linh kiện/mặt hàng.",
    estimatedRows: "~2,000 dòng (SF-0.01) / ~200K dòng (SF-1)",
    columns: [
      { name: "p_partkey", type: "INTEGER", description: "Mã định danh sản phẩm", isPk: true },
      { name: "p_name", type: "VARCHAR(55)", description: "Tên mô tả sản phẩm" },
      { name: "p_mfgr", type: "VARCHAR(25)", description: "Tên nhà sản xuất" },
      { name: "p_brand", type: "VARCHAR(10)", description: "Nhãn hiệu sản phẩm" },
      { name: "p_type", type: "VARCHAR(25)", description: "Loại vật liệu / danh mục" },
      { name: "p_size", type: "INTEGER", description: "Kích cỡ quy chuẩn" },
      { name: "p_container", type: "VARCHAR(10)", description: "Hình thức đóng gói (JUMBO BOX, SM PKG...)" },
      { name: "p_retailprice", type: "DECIMAL(15,2)", description: "Giá bán lẻ niêm yết" },
    ],
  },
  {
    name: "partsupp",
    displayName: "Liên Kết Tồn Kho & Cung Ứng",
    description: "Bảng liên kết giữa linh kiện và nhà cung cấp, lưu giá vốn và lượng hàng sẵn có trong kho.",
    estimatedRows: "~8,000 dòng (SF-0.01) / ~800K dòng (SF-1)",
    columns: [
      { name: "ps_partkey", type: "INTEGER", description: "Mã sản phẩm", isPk: true, isFk: true, fkTarget: "part.p_partkey" },
      { name: "ps_suppkey", type: "INTEGER", description: "Mã nhà cung cấp", isPk: true, isFk: true, fkTarget: "supplier.s_suppkey" },
      { name: "ps_availqty", type: "INTEGER", description: "Số lượng sản phẩm còn sẵn trong kho" },
      { name: "ps_supplycost", type: "DECIMAL(15,2)", description: "Giá thành cung cấp từ đối tác" },
    ],
  },
  {
    name: "supplier",
    displayName: "Nhà Cung Cấp",
    description: "Thông tin các đối tác cung ứng linh kiện và nguyên vật liệu.",
    estimatedRows: "~100 dòng (SF-0.01) / ~10K dòng (SF-1)",
    columns: [
      { name: "s_suppkey", type: "INTEGER", description: "Mã định danh nhà cung cấp", isPk: true },
      { name: "s_name", type: "VARCHAR(25)", description: "Tên nhà cung cấp" },
      { name: "s_address", type: "VARCHAR(40)", description: "Địa chỉ nhà cung cấp" },
      { name: "s_nationkey", type: "INTEGER", description: "Mã quốc gia sở tại", isFk: true, fkTarget: "nation.n_nationkey" },
      { name: "s_phone", type: "VARCHAR(15)", description: "Số điện thoại liên hệ", isPii: true },
      { name: "s_acctbal", type: "DECIMAL(15,2)", description: "Số dư tài khoản công nợ", isPii: true },
    ],
  },
  {
    name: "nation",
    displayName: "Quốc Gia",
    description: "Danh mục 25 quốc gia đối tác kinh doanh thuộc 5 khu vực địa lý toàn cầu.",
    estimatedRows: "25 dòng",
    columns: [
      { name: "n_nationkey", type: "INTEGER", description: "Mã quốc gia", isPk: true },
      { name: "n_name", type: "VARCHAR(25)", description: "Tên quốc gia (VIETNAM, JAPAN, UNITED STATES...)" },
      { name: "n_regionkey", type: "INTEGER", description: "Mã khu vực trực thuộc", isFk: true, fkTarget: "region.r_regionkey" },
    ],
  },
  {
    name: "region",
    displayName: "Khu Vực Địa Lý",
    description: "5 phân vùng địa lý kinh doanh toàn cầu của TPC-H.",
    estimatedRows: "5 dòng",
    columns: [
      { name: "r_regionkey", type: "INTEGER", description: "Mã khu vực", isPk: true },
      { name: "r_name", type: "VARCHAR(25)", description: "Tên khu vực: AFRICA, AMERICA, ASIA, EUROPE, MIDDLE EAST" },
    ],
  },
];

export const SEMANTIC_METRICS: MetricDefinition[] = [
  {
    id: "net_revenue",
    name: "Doanh Thu Thuần (Net Revenue)",
    businessMeaning: "Tổng doanh thu bán hàng thực tế sau khi đã trừ đi giá trị chiết khấu thương mại.",
    formulaSql: "SUM(l_extendedprice * (1 - l_discount))",
    tablesUsed: ["lineitem"],
  },
  {
    id: "cogs",
    name: "Giá Vốn & Thuế (Gross Cost)",
    businessMeaning: "Tổng giá trị dòng hàng sau khi tính toán cả chiết khấu và thuế VAT/nhập khẩu.",
    formulaSql: "SUM(l_extendedprice * (1 - l_discount) * (1 + l_tax))",
    tablesUsed: ["lineitem"],
  },
  {
    id: "late_delivery_count",
    name: "Đơn Hàng Giao Trễ Hạn",
    businessMeaning: "Số lượng dòng hàng có ngày nhận thực tế trễ hơn ngày cam kết giao hàng.",
    formulaSql: "COUNT(*) FILTER (WHERE l_receiptdate > l_commitdate)",
    tablesUsed: ["lineitem"],
  },
  {
    id: "return_rate",
    name: "Tỷ Lệ Hàng Hoàn Trả",
    businessMeaning: "Tỷ lệ phần trăm các mặt hàng bị khách hàng hoàn trả lại kho (l_returnflag = 'R').",
    formulaSql: "ROUND(COUNT(*) FILTER (WHERE l_returnflag = 'R') * 100.0 / COUNT(*), 2)",
    tablesUsed: ["lineitem"],
  },
  {
    id: "inventory_value",
    name: "Giá Trị Tồn Kho Ước Tính",
    businessMeaning: "Tổng giá trị lượng hàng còn sẵn trong kho tính theo đơn giá vốn của nhà cung cấp.",
    formulaSql: "SUM(ps_availqty * ps_supplycost)",
    tablesUsed: ["partsupp"],
  },
];
