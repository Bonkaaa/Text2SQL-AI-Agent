# PRD.md — Product Requirements Document

> **Dự án**: AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp  
> **Bộ dữ liệu chuẩn**: **TPC-DS Benchmark (Omnichannel Retail & Enterprise Data Warehouse - 24 Tables)**  
> **Phiên bản**: 4.0  
> **Trạng thái**: Production Architecture Standard  
> **Ngày cập nhật**: 2026-10-01  
> **Tài liệu kiến trúc**: [ARCHITECTURE.md](file:///d:/Text2SQL-AI-Agent/docs/ARCHITECTURE.md), [agent-architecture-v4.md](file:///d:/Text2SQL-AI-Agent/docs/agent-architecture-v4.md)  
> **Đặc tả luồng dữ liệu**: [DATA_FLOW.md](file:///d:/Text2SQL-AI-Agent/docs/DATA_FLOW.md)  
> **Từ điển cơ sở dữ liệu**: [DATABASE_SCHEMA.md](file:///d:/Text2SQL-AI-Agent/docs/DATABASE_SCHEMA.md)  

---

## 1. PROJECT BRIEF (BẢN TÓM TẮT DỰ ÁN)

- **Tên sản phẩm**: **Enterprise Agentic Self-Service Analytics Engine (TPC-DS Edition)**
- **Vấn đề cốt lõi (Pain Point)**:
  - Tại các doanh nghiệp thương mại và bán lẻ đa kênh (Omnichannel Retail), nhân viên nghiệp vụ (Kinh doanh, Tiếp thị, Quản lý kho, Điều hành chuỗi cung ứng) liên tục đối mặt với các câu hỏi phân tích kinh doanh đa biến: *Tại sao doanh thu quý 3 sụt giảm? Kênh bán lẻ tại quầy (Store) hay trực tuyến (Web) bị ảnh hưởng nhiều nhất? Ngành hàng nào có tỷ lệ trả hàng vượt mức trung bình? Tồn kho có đáp ứng được nhu cầu các chương trình khuyến mãi không?*
  - Hiện tại, mọi yêu cầu phân tích đều phải gửi ticket sang đội ngũ Data Analyst (DA). Thời gian phản hồi kéo dài từ **2 đến 5 ngày**, gây nghẽn nghiêm trọng cho các quyết định chiến lược và điều phối vận hành.
  - Các công cụ Text-to-SQL truyền thống trên thị trường chỉ hỗ trợ mô hình thô sơ: **"1 câu text $\to$ 1 câu SQL đơn lẻ $\to$ 1 bảng kết quả"**. Mô hình này hoàn toàn bất lực trước kho dữ liệu chuẩn công nghiệp (Snowflake Schema gồm 24 bảng, 429 cột và quan hệ bắc cầu qua bảng ngày tháng `date_dim`) và các câu hỏi đòi hỏi điều tra nhiều góc nhìn.
  - Nguy cơ an ninh (SQL Injection, biến đổi dữ liệu trái phép, rò rỉ dữ liệu cá nhân PII) và tình trạng lỗi giao diện phổ biến khi dùng Regular Expression để trích xuất JSON/SQL từ câu trả lời tự do của LLM.
- **Giải pháp (Solution)**:
  - Xây dựng một **Agentic Self-Service Analytics Engine (Kiến trúc v4.0)** cho phép người dùng hỏi đáp bằng **tiếng Việt tự nhiên** trên kho dữ liệu phân tích chuẩn TPC-DS.
  - Mô phỏng chính xác phương pháp luận làm việc của một **Senior Data Analyst**:
    1. *Kiểm soát sơ bộ & Làm rõ*: Nhận diện ý định, hỏi lại khi câu hỏi thiếu mốc thời gian hoặc kênh bán ([`PreflightGatekeeper`](file:///d:/Text2SQL-AI-Agent/src/agents/preflight_gatekeeper.py)).
    2. *Lập kế hoạch phân tích (`AnalysisPlan`)*: Đặt mục tiêu và phân rã thành tối đa 3 nhiệm vụ truy vấn tuần tự ($N \le 3$) để kiểm chứng các giả thuyết kinh doanh ([`AnalysisPlanner`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/planner.py)).
    3. *Thực thi & Thu thập bằng chứng*: Dò đường nối BFS, sinh SQL tập trung, đưa qua hàng rào an ninh tất định 100% bằng code thuần ([`LangGraph Control Pipeline`](file:///d:/Text2SQL-AI-Agent/src/agents/control_pipeline/builder.py)), tích lũy số liệu vào `EvidenceStore`.
    4. *Phân tích chuyên sâu (`EvidenceAnalyzer`)*: Tính toán các chỉ số tăng trưởng ($\Delta\%$), tỷ trọng đóng góp, phát hiện ngoại lệ và kiểm chứng giả thuyết.
    5. *Trình diễn chuẩn chỉ (`ResponseSynthesizer`)*: Chọn cấu hình trực quan Recharts linh hoạt và rót dữ liệu tất định (Deterministic Data Hydration), xuất bản gói kết quả định kiểu mạnh (`ResponsePackage` / `ArtifactBundle`).
- **Đối tượng sử dụng (Target Users)**:
  1. *Business Users / Sales & Inventory Analysts (Role: `Analyst`)*: Cần số liệu và insight phân tích nhanh chóng mà không cần kỹ năng viết SQL chuyên sâu.
  2. *Data Team / Warehouse Administrators (Role: `Admin`)*: Cần giảm tải yêu cầu ad-hoc, muốn kiểm soát an toàn tuyệt đối (Zero DML/DDL, RBAC bảo vệ PII) và định lượng chi phí quét dữ liệu kho cloud.

---

## 2. MỤC TIÊU & CHỈ SỐ THÀNH CÔNG (GOALS & TARGET METRICS)

### 2.1. Mục tiêu sản phẩm (Product Goals)
- Rút ngắn thời gian từ lúc phát sinh bài toán nghiệp vụ đến khi có báo cáo phân tích kèm biểu đồ từ **vài ngày xuống dưới 30 giây**.
- Trao quyền tự phục vụ (Self-service) cho các bài toán phân tích ad-hoc từ đơn giản đến phức tạp trên 24 bảng TPC-DS.
- Đảm bảo **an toàn dữ liệu tuyệt đối (Zero Trust on LLM for Security)**: Chặn đứng 100% các thao tác thay đổi dữ liệu hoặc truy cập trái phép trường nhạy cảm PII.
- Loại bỏ hoàn toàn lỗi hiển thị giao diện thông qua giao thức truyền thông định kiểu mạnh (Zero Regex Scraping).

### 2.2. Chỉ số thành công đo lường được (Target Metrics)

| Chỉ số | Định nghĩa / Cách đo | Mục tiêu v4.0 (TPC-DS) |
|---|---|:---:|
| **Valid SQL Rate (VSR)** | Tỷ lệ câu SQL sinh ra đúng cú pháp và chạy thành công trên Warehouse | $\ge \mathbf{92\%}$ |
| **Execution Accuracy (EX)** | Tỷ lệ kết quả truy vấn sinh ra trùng khớp với Ground-truth trên bộ dữ liệu TPC-DS | $\ge \mathbf{78\%}$ |
| **Governance Compliance** | Tỷ lệ chặn đứng 100% các câu lệnh biến đổi dữ liệu (DML/DDL) và vi phạm RBAC | $\mathbf{100\%}$ |
| **Self-Correction Success Rate** | Tỷ lệ truy vấn lỗi được sửa thành công nhờ `DiagnosticAgent` ($\le 3$ lần retry) | $\ge \mathbf{65\%}$ |
| **Multi-Query Plan Completion** | Tỷ lệ các kế hoạch phân tích nhiều bước hoàn thành trọn vẹn và tổng hợp thành công | $\ge \mathbf{85\%}$ |
| **Presentation Integrity** | Tỷ lệ output chuẩn hóa Pydantic `ResponsePackage` thành công, không dùng regex fallback | $\mathbf{100\%}$ |
| **Average End-to-End Latency** | Tổng thời gian hoàn thành (bao gồm lập kế hoạch, truy vấn và phân tích) | $<\mathbf{30\text{ giây}}$ |

---

## 3. CHÂN DUNG NGƯỜI DÙNG & USER STORIES

### 3.1. Chân dung người dùng (User Personas)
- **Persona 1: Nguyễn Văn An — Business / Retail Analyst (Role: `Analyst`)**
  - *Mục tiêu*: Tra cứu và phân tích nguyên nhân biến động doanh số đa kênh (Store vs Web vs Catalog), đánh giá tỷ lệ trả hàng theo ngành hàng, theo dõi tồn kho theo kho bãi.
  - *Nỗi sợ*: Dữ liệu trích xuất sai lệch, chờ đợi đội kỹ thuật quá lâu làm lỡ kế hoạch đàm phán nhà cung cấp hoặc điều tiết khuyến mãi.
- **Persona 2: Trần Thị Bình — Data Lead / Enterprise Admin (Role: `Admin`)**
  - *Mục tiêu*: Giám sát an toàn kho dữ liệu, bảo đảm tuân thủ bảo mật thông tin (không lộ họ tên, email, ngày sinh, địa chỉ khách hàng), kiểm soát chi phí query Cloud Warehouse.
  - *Nỗi sợ*: AI sinh câu lệnh nguy hiểm (DROP, DELETE) hoặc quét toàn bộ các bảng Fact lớn (`store_sales`, `catalog_sales`) làm đội chi phí hạ tầng.

### 3.2. Danh sách User Stories (Kiến trúc v4.0)

```
[US-01] Là một Analyst, tôi muốn hỏi các câu hỏi phân tích kinh doanh đa biến bằng tiếng Việt tự nhiên,
        để Agent tự động chia nhỏ bài toán thành chuỗi truy vấn hợp lý và đưa ra lời giải hoàn chỉnh.

[US-02] Là một Analyst, khi câu hỏi của tôi chưa rõ ràng về thời gian (năm, quý) hoặc kênh bán,
        tôi muốn Agent chủ động hỏi lại kèm gợi ý cụ thể để làm rõ mục tiêu phân tích.

[US-03] Là một Analyst, tôi muốn xem trước câu SQL, mục đích truy vấn và ước tính chi phí quét dữ liệu
        để xác nhận (Human-in-the-Loop) trước khi câu lệnh được chạy trên kho dữ liệu thật.

[US-04] Là một Analyst, tôi muốn nhận kết quả dưới dạng bản báo cáo có cấu trúc gồm:
        Tóm tắt điều hành, các thẻ chỉ số KPI, bảng dữ liệu định dạng chuẩn và biểu đồ Recharts trực quan.

[US-05] Là một Admin, tôi muốn hệ thống phân loại câu chào hỏi xã giao và câu hỏi phân tích ngay từ cửa vào,
        để tiết kiệm tài nguyên tính toán và chi phí API token.

[US-06] Là một Admin, tôi muốn hệ thống kiểm duyệt tĩnh cú pháp bằng AST để chặn đứng 100% câu lệnh DML/DDL
        và các kỹ thuật SQL Injection tinh vi.

[US-07] Là một Admin, tôi muốn áp dụng ma trận phân quyền (RBAC) để chặn nhân viên Analyst truy vấn
        các cột nhạy cảm PII (c_first_name, c_last_name, c_email_address, c_birth_country) trước khi chạm tới Database.

[US-08] Là một Admin, tôi muốn toàn bộ lịch sử truy vấn, chi phí quét dữ liệu và thời gian thực thi
        được ghi lại trong bảng audit_logs phục vụ thanh tra và tối ưu hóa hệ thống.
```

---

## 4. TÍNH NĂNG CỐT LÕI (CORE FEATURES)

### Feature 1: Pre-flight Gatekeeper & Clarification Loop
- **Tier 1 (Regex Guard)**: Chốt chặn $< 0.1$ms ngăn chặn mã độc SQL Injection và từ khóa can thiệp dữ liệu (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`).
- **Tier 2 (Unified LLM Guard)**: Đánh giá độ mơ hồ và ngoài miền dữ liệu TPC-DS; tự động sinh câu hỏi làm rõ kèm 2-4 tùy chọn gợi ý A, B, C để người dùng chọn nhanh.

### Feature 2: Active Schema Linking, BFS Snowflake Join Path & Categorical Search
- **Schema Pruning (24 Bảng)**: Lọc động các bảng Fact (`store_sales`, `web_sales`, `catalog_sales`, `store_returns`, `web_returns`, `catalog_returns`, `inventory`) và Dimension (`date_dim`, `item`, `customer`, `store`, `promotion`).
- **BFS Join Path**: Tự động dò tìm đường nối ngắn nhất trong đồ thị quan hệ Snowflake 24 bảng.
- **Categorical Value Search**: Khớp chính xác các giá trị danh mục thực tế trong database (ngành hàng `item.i_category`, tình trạng hôn nhân, phương thức vận chuyển `ship_mode.sm_type`).
- **TPC-DS Golden Rules**: Bắt buộc JOIN với `date_dim` khi lọc thời gian; sử dụng chuẩn doanh thu thuần `ss_net_paid`, `ws_net_paid`, `cs_net_paid`.

### Feature 3: Analysis Planner & Hypothesis Formulation
- **Lập kế hoạch phân tích (`AnalysisPlan`)**:
  - Chuyển đổi câu hỏi lớn thành: Mục tiêu cốt lõi (`goal`) + Các giả thuyết nghiệp vụ cần kiểm chứng (`hypotheses`) + Danh sách nhiệm vụ truy vấn tuần tự (`tasks`).
  - Khống chế ngân sách nghiêm ngặt: **Tối đa 3 nhiệm vụ tuần tự ($N \le 3$)**.
  - Mỗi nhiệm vụ có một mục tiêu đơn nhất, dễ viết SQL và dễ kiểm chứng.

### Feature 4: Sequential Execution & Evidence Collection Loop
- **Task Query Generator**: Viết câu SQL tập trung cho từng task đơn lẻ, kết hợp bối cảnh rút ra từ các task trước đó.
- **Evidence Accumulation (`EvidenceStore`)**: Lưu trữ có cấu trúc kết quả mẫu (data sample), số dòng, thống kê cơ bản và chi phí quét của từng task đã thực thi thành công.

### Feature 5: Hàng Rào Kiểm Duyệt Tất Định & Diagnostic Agent
- **AST Security Sanitizer (`sqlglot`)**: Chỉ chấp nhận `SELECT`. Chặn mọi lệnh sửa đổi dữ liệu và batch statement.
- **RBAC Policy Enforcer**: Áp dụng ma trận quyền theo vai trò (`Analyst` vs `Admin`), chặn cột nhạy cảm PII.
- **Cost Guard**: Dry-run kiểm tra dung lượng bytes quét; cảnh báo nếu vượt hạn mức.
- **Human-In-The-Loop (HITL) Gate**: Cơ chế `interrupt()` của LangGraph yêu cầu người dùng xác nhận câu lệnh và chi phí.
- **Warehouse Timeout & Limit**: Giới hạn thời gian truy vấn 30s và tự động chèn `LIMIT 1000`.
- **Error Diagnostic Agent**: Phân tích lỗi kỹ thuật và cung cấp phản hồi có định hướng cho Generator; khống chế vòng lặp sửa lỗi tối đa **3 lần retry (`max_retries = 3`)**.
- **Audit Logger**: Ghi log cấu trúc JSON vào bảng `audit_logs`.

### Feature 6: Decoupled Evidence Analysis & Presentation Synthesizer
- **Evidence Analyzer ([`evidence_analyzer.py`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/evidence_analyzer.py))**:
  - Thực hiện tính toán toán học: Độ tăng trưởng ($\Delta\%$), tỷ trọng đóng góp, độ phân tán số liệu.
  - Xác nhận hoặc bác bỏ các giả thuyết trong `AnalysisPlan`.
- **Response Synthesizer ([`response_synthesizer.py`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/response_synthesizer.py))**:
  - Cơ chế One-Shot Spec Selection + Deterministic Data Hydration: Chọn bố cục linh hoạt và rót dữ liệu thật vào cấu trúc biểu đồ Recharts, thẻ KPI và bảng dữ liệu.
  - Soạn thảo bản tóm tắt điều hành bằng tiếng Việt tự nhiên chuẩn mực.
- **Typed Delivery Contract**: Đóng gói toàn bộ kết quả vào Pydantic V2 Model `ResponsePackage`, triệt tiêu hoàn toàn rủi ro vỡ giao diện do regex parsing.

### Feature 7: Modern Executive Workstation (Frontend UI)
- Giao diện làm việc chuyên nghiệp với Executive Launchpad, Inspector Drawer tra cứu tiến trình Agent, TPC-DS Schema Explorer và hệ thống biểu đồ trực quan hóa tương tác cao.

---

## 5. NHỮNG GÌ NẰM NGOÀI PHẠM VI (NON-GOALS)

Để đảm bảo dự án hoàn thành xuất sắc và đúng hạn:
1. **KHÔNG hỗ trợ thao tác ghi / sửa dữ liệu (Zero Write/Drop)**: Hệ thống 100% là Read-Only Analytics.
2. **KHÔNG thực thi truy vấn song song hoặc gộp câu lệnh (No Parallelism & No Query Fusion)**: Các truy vấn trong một kế hoạch bắt buộc chạy tuần tự để đảm bảo độ tin cậy và kiểm soát chi phí.
3. **KHÔNG tự động sinh Dashboard vô hạn**: Hệ thống tập trung giải quyết bài toán phân tích ad-hoc theo phiên hội thoại, không thay thế các công cụ BI doanh nghiệp như Tableau/PowerBI.
4. **KHÔNG xử lý tài liệu phi cấu trúc**: Giới hạn phạm vi dữ liệu trong 24 bảng chuẩn của TPC-DS Benchmark.

---

## 6. RÀNG BUỘC KỸ THUẬT & AN TOÀN (CONSTRAINTS)

### 6.1. Ràng buộc An toàn & Ngân sách (Dual-Budget Rules)
- **Analysis Task Budget**: Tối đa 3 tasks cho một câu hỏi người dùng.
- **Per-Query Retry Budget**: Tối đa 3 lần retry sửa lỗi cho một câu SQL.
- **Warehouse Execution Timeout**: Tối đa 30 giây cho mỗi lệnh thực thi.
- **Result Row Limit**: Tối đa 1000 dòng trả về cho người dùng.

### 6.2. Môi trường Kho dữ liệu (Warehouse Strategy)
- **Local Dev / Testing**: **DuckDB** file cục bộ (`data/tpcds.duckdb`) khởi tạo tự động qua extension `CALL dsdgen(sf=0.01..1)`.
- **Production Demo**: **Google BigQuery Sandbox** hoặc **Supabase Managed PostgreSQL**, kết nối thông qua abstraction `WarehouseClient`.

---

## 7. KẾ HOẠCH PHÂN KỲ PHÁT TRIỂN (PROJECT PHASING)

```
[ Phase 1: Foundation & Contracts ]
├── Xóa bỏ Regex Parsing trong src/api/routes/query.py.
├── Bổ sung Pydantic V2 models: AnalysisPlan, QueryArtifact, EvidenceStore, ResponsePackage.
└── Hoàn thiện Unit Tests kiểm tra hợp đồng dữ liệu.

[ Phase 2: Core Analysis Engine v4.0 ]
├── Xây dựng Preflight Gatekeeper (Regex + Unified LLM Clarification).
├── Xây dựng Analysis Planner (Goal, Hypotheses, Tasks <= 3).
├── Xây dựng Evidence Analyzer (Math, Trends, Hypotheses verification).
└── Xây dựng Response Synthesizer (Composable Spec + Data Hydration).

[ Phase 3: Subgraph Assembly & TPC-DS Migration ]
├── Lắp ráp LangGraph Analytics Subgraph với Sequential Execution Loop.
├── Tích hợp Control Pipeline Subgraph (AST, RBAC, Cost, HITL, Diagnostic).
├── Nạp dữ liệu DuckDB TPC-DS 24 bảng (tpcds_seeder.py).
└── Xây dựng đồ thị khóa ngoại BFS và chỉ mục danh mục TPC-DS.

[ Phase 4: Frontend Modernization & Evaluation ]
├── Hoàn thiện Next.js Workstation UI (Launchpad, Inspector, TPC-DS Drawer, Recharts).
├── Chạy đánh giá bộ Benchmark 50 câu hỏi tiếng Việt TPC-DS (VSR, EX, Self-correction).
└── Viết Đồ án tốt nghiệp hoàn chỉnh (5 chương).
```
