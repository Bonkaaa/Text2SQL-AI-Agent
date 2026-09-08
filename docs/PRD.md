# PRD.md — Product Requirements Document

> **Dự án**: AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp  
> **Bộ dữ liệu chuẩn**: **TPC-H Benchmark (Wholesale & Supply Chain Analytics)**  
> **Phiên bản**: 2.0  
> **Trạng thái**: Approved for Build Phase  
> **Phạm vi áp dụng**: Đồ án tốt nghiệp / Xây dựng hệ sinh thái AI Agent cho Enterprise Data  

---

## 1. PROJECT BRIEF (BẢN TÓM TẮT DỰ ÁN)

- **Tên sản phẩm**: **Enterprise Text2SQL Analytics Agent (TPC-H Edition)**
- **Vấn đề cốt lõi (Pain Point)**:
  - Tại các doanh nghiệp phân phối, bán buôn và chuỗi cung ứng, nhân viên nghiệp vụ (Kinh doanh, Mua hàng, Quản lý kho, Vận tải) liên tục cần số liệu báo cáo doanh số, mức chiết khấu, tình trạng giao hàng trễ, và biến động tồn kho.
  - Hiện tại, mọi yêu cầu đều phải gửi ticket sang đội Data Engineer / Data Analyst, thời gian phản hồi mất từ **2 đến 5 ngày**, gây nghẽn quyết định nhập hàng và điều phối kinh doanh.
  - Đội ngũ Data quá tải với các câu hỏi truy vấn dữ liệu đơn giản lặp đi lặp lại.
- **Giải pháp (Solution)**:
  - Xây dựng một AI Agent Self-Service cho phép nhân viên nghiệp vụ hỏi trực tiếp bằng **tiếng Việt tự nhiên** trên kho dữ liệu chuẩn TPC-H.
  - Agent tự động làm rõ câu hỏi mơ hồ, liên kết đúng bảng/cột và giá trị dữ liệu thực tế (quốc gia, phân khúc, hãng sản xuất, phương thức vận chuyển), sinh câu lệnh SQL chuẩn xác.
  - Tích hợp **hàng rào an toàn dữ liệu (Data Governance)**: Kiểm duyệt cú pháp (chỉ đọc SELECT), phân quyền truy cập theo vai trò (RBAC), ước tính chi phí quét dữ liệu (bytes scanned), và yêu cầu người dùng xác nhận (Human-In-The-Loop) trước khi chạy thật.
  - Trả về kết quả trực quan gồm: Bảng dữ liệu + Biểu đồ động Recharts + Đoạn văn tóm tắt insight kinh doanh nổi bật.
- **Đối tượng sử dụng (Target Users)**:
  1. *Business Users / Supply Chain & Sales Analysts*: Cần số liệu nhanh, không biết viết SQL.
  2. *Data Team / Warehouse Administrators*: Cần giảm tải yêu cầu ad-hoc, muốn kiểm soát an toàn và chi phí truy vấn kho dữ liệu.

---

## 2. MỤC TIÊU & CHỈ SỐ THÀNH CÔNG (GOALS & SUCCESS METRICS)

### 2.1. Mục tiêu sản phẩm (Product Goals)
- Rút ngắn thời gian từ lúc phát sinh câu hỏi nghiệp vụ đến khi có số liệu biểu đồ từ **vài ngày xuống dưới 30 giây**.
- Trao quyền tự phục vụ (Self-service) cho ít nhất 80% các câu hỏi truy vấn dữ liệu dạng ad-hoc thông dụng trên 8 bảng TPC-H.
- Đảm bảo **an toàn tuyệt đối cho hệ thống dữ liệu**: 0% rủi ro rò rỉ dữ liệu nhạy cảm (PII nhà cung cấp, khách hàng) hoặc thao tác phá hoại dữ liệu (Zero Write/Drop).

### 2.2. Chỉ số thành công đo lường được (Target Metrics)

| Chỉ số | Định nghĩa / Cách đo | Mục tiêu MVP |
|---|---|---|
| **Execution Accuracy (EX)** | Tỷ lệ kết quả truy vấn sinh ra trùng khớp với kết quả câu SQL chuẩn (Ground-truth TPC-H Q1-Q22) | $\ge 82\%$ |
| **Valid SQL Rate (VSR)** | Tỷ lệ câu SQL sinh ra đúng cú pháp và chạy thành công trên Warehouse | $\ge 95\%$ |
| **Governance Compliance** | Tỷ lệ chặn đứng 100% các câu lệnh biến đổi dữ liệu (DML/DDL) và vi phạm RBAC | **100%** |
| **Self-Correction Success Rate** | Tỷ lệ truy vấn lỗi được Agent tự sửa thành công qua vòng lặp phản hồi ($\le 3$ lần) | $\ge 60\%$ |
| **Average Query Turnaround** | Tổng thời gian từ khi người dùng hỏi đến khi hiển thị biểu đồ kết quả | $< 30$ giây |

---

## 3. CHÂN DUNG NGƯỜI DÙNG & USER STORIES

### 3.1. Chân dung người dùng (User Personas)
- **Persona 1: Nguyễn Văn An — Supply Chain & Sales Analyst (Role: `Analyst`)**
  - *Mục tiêu*: Tra cứu nhanh doanh số bán buôn theo khu vực (`r_name`), mặt hàng bán chạy (`p_name`), tỷ lệ hoàn hàng (`l_returnflag`), và các đơn giao trễ hạn.
  - *Nỗi sợ*: Viết sai query lấy nhầm dữ liệu, chờ đội data quá lâu làm lỡ kế hoạch nhập hàng và đàm phán chiết khấu.
- **Persona 2: Trần Thị Bình — Data Lead / Admin (Role: `Admin`)**
  - *Mục tiêu*: Quản lý schema kho dữ liệu, cấp quyền an toàn, giám sát chi phí BigQuery/DuckDB hàng tháng.
  - *Nỗi sợ*: AI sinh câu lệnh nguy hiểm (DROP, DELETE) hoặc quét toàn bộ bảng `lineitem` dung lượng lớn làm vọt chi phí cloud.

### 3.2. Danh sách User Stories

```
[US-01] Là một Analyst, tôi muốn hỏi về doanh số, tồn kho theo khu vực bằng tiếng Việt tự nhiên, 
        để không cần học cú pháp SQL phức tạp mà vẫn lấy được dữ liệu chính xác.

[US-02] Là một Analyst, khi câu hỏi của tôi chưa rõ ràng (ví dụ: "doanh số năm nay" mà chưa rõ khoảng thời gian hay khu vực), 
        tôi muốn Agent chủ động hỏi lại kèm gợi ý, để tôi không nhận về kết quả sai lệch.

[US-03] Là một Analyst, tôi muốn nhìn thấy câu SQL nháp, lời giải thích ý nghĩa truy vấn 
        và chi phí quét dữ liệu ước tính (bytes scanned trên bảng lineitem), để tôi tự tin duyệt trước khi chạy.

[US-04] Là một Analyst, tôi muốn kết quả được tự động dựng thành biểu đồ trực quan (Recharts) 
        kèm lời bình luận tóm tắt insight, để tôi có thể dùng ngay vào báo cáo giao ban.

[US-05] Là một Admin, tôi muốn hệ thống tự động chặn 100% các câu lệnh INSERT, UPDATE, DELETE, DROP, 
        để kho dữ liệu luôn được an toàn ở chế độ Read-Only.

[US-06] Là một Admin, tôi muốn phân quyền theo vai trò (Analyst không được xem số điện thoại, địa chỉ 
        hay số dư tài khoản của khách hàng và nhà cung cấp), để tuân thủ quy chế bảo mật dữ liệu doanh nghiệp.

[US-07] Là một Admin, tôi muốn hệ thống cảnh báo hoặc chặn các truy vấn quét dữ liệu vượt quá ngưỡng dung lượng, 
        để kiểm soát chi phí dịch vụ Cloud Warehouse.

[US-08] Là một Admin, tôi muốn có bảng Audit Log lưu lại toàn bộ lịch sử ai đã hỏi gì, SQL sinh ra là gì, 
        chi phí quét bao nhiêu, để phục vụ thanh tra và đánh giá hiệu năng.
```

---

## 4. TÍNH NĂNG CỐT LÕI (CORE FEATURES)

### Feature 1: NL-to-SQL & Schema Linking với Categorical Value Search (TPC-H)
- Chuyển đổi câu hỏi tiếng Việt có dấu/không dấu sang SQL tương thích DuckDB / BigQuery Standard SQL.
- **Schema Linking**: Sử dụng Vector Search tìm đúng 8 bảng TPC-H (`region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem`).
- **Categorical Value Search**: Khớp thực thể danh mục thực tế trong database:
  - Phân khúc khách hàng: `'AUTOMOBILE'`, `'BUILDING'`, `'FURNITURE'`, `'HOUSEHOLD'`, `'MACHINERY'`.
  - Khu vực: `'ASIA'`, `'EUROPE'`, `'AMERICA'`, `'AFRICA'`, `'MIDDLE EAST'`.
  - Phương thức giao hàng: `'AIR'`, `'FOB'`, `'SHIP'`, `'TRUCK'`, `'MAIL'`.
  - Trạng thái dòng hàng: `'R'` (Returned), `'A'` (Accepted), `'N'` (None).
- **Semantic Metrics**: Áp dụng các định nghĩa tính toán nghiệp vụ thống nhất (Doanh thu thuần `extendedprice * (1 - discount)`, chi phí nhập hàng, tỷ lệ giao trễ).

### Feature 2: Clarification Loop & Hội thoại đa lượt (Multi-turn)
- Nhận diện câu hỏi mơ hồ, thiếu điều kiện lọc cốt lõi (thiếu mốc năm, thiếu khu vực địa lý, thiếu thương hiệu).
- Trả về câu hỏi làm rõ thân thiện kèm các tùy chọn gợi ý.
- Ghi nhớ ngữ cảnh trò chuyện (LangGraph state checkpoint) để người dùng có thể hỏi tiếp nối (Follow-up questions).

### Feature 3: Deterministic Governance & Cost Guard
- **AST Security Sanitizer**: Parse toàn bộ SQL qua `sqlglot`. Bắt buộc kiểu câu lệnh là `SELECT`. Chặn đứng và ném lỗi với mọi thao tác ghi/xóa/sửa cấu trúc hoặc SQL injection.
- **Role-Based Access Control (RBAC)**: Đối chiếu danh sách bảng/cột được truy vấn với ma trận phân quyền của vai trò (`Analyst` vs `Admin`). Chặn các cột PII (`c_phone`, `c_acctbal`, `s_phone`, `s_acctbal`).
- **Cost Guard (Dry-run)**: Ước tính trước số bytes dữ liệu sẽ quét trên bảng `lineitem`/`orders` qua BigQuery `dryRun` hoặc DuckDB `EXPLAIN`. Cảnh báo hoặc chặn nếu vượt ngưỡng quota (ví dụ: > 1GB đối với Analyst).

### Feature 4: Human-in-the-Loop (HITL) Approval Flow
- Áp dụng cơ chế tạm dừng `interrupt()` của LangGraph.
- Hiển thị pop-up / modal trên giao diện người dùng:
  - Câu lệnh SQL dự kiến thực thi (kèm cú pháp highlight).
  - Lời diễn giải ngắn gọn câu SQL này làm nhiệm vụ gì.
  - Ước tính chi phí quét dữ liệu.
- Người dùng có 2 hành động: **[Xác nhận Chạy]** hoặc **[Từ chối / Yêu cầu viết lại]**.

### Feature 5: Tự động trực quan hóa & Phân tích Insight
- Tự động nhận diện cấu trúc dữ liệu trả về để đề xuất loại biểu đồ thích hợp (Doanh thu theo tháng/năm $\rightarrow$ Line/Area Chart; Doanh số theo 5 khu vực $\rightarrow$ Bar/Pie Chart).
- Tích hợp trực quan với thư viện **Recharts**.
- Sinh bản tóm tắt phân tích kinh doanh (Narrative Insight): Nêu rõ xu hướng tăng trưởng, khu vực đóng góp doanh thu lớn nhất, nhóm mặt hàng có tỷ lệ hoàn hàng cao.

### Feature 6: Bounded Self-Correction Loop & Audit Logging
- Nếu câu truy vấn bị lỗi (sai cú pháp SQL dialect, lỗi runtime DB): Agent tự động nhận error context và sinh lại câu lệnh.
- Giới hạn cứng: **Tối đa 3 lần retry (`MAX_RETRIES = 3`)** để tránh lặp vô hạn và lãng phí token.
- Ghi lại toàn bộ hành trình truy vấn vào bảng `audit_logs` phục vụ giám sát và cải tiến chất lượng prompt.

---

## 5. NHỮNG GÌ NẰM NGOÀI PHẠM VI (NON-GOALS)

Để đảm bảo dự án tập trung cao độ và hoàn thành đúng tiến độ:

1. **KHÔNG hỗ trợ thao tác ghi / sửa đổi dữ liệu (No DML/DDL)**: Hệ thống 100% là Read-Only Analytics. Tuyệt đối không phục vụ tác vụ tạo đơn hàng mới, sửa giá sản phẩm, xóa nhà cung cấp.
2. **KHÔNG xử lý dữ liệu phi cấu trúc**: Hệ thống chỉ truy vấn 8 bảng có cấu trúc của TPC-H. Không tìm kiếm trên file PDF hợp đồng hay email giao dịch bên ngoài.
3. **KHÔNG thay thế toàn bộ nền tảng BI phức tạp**: Sản phẩm hướng tới truy vấn số liệu ad-hoc và biểu đồ nhanh, không nhằm mục đích xây dựng các dashboard phức tạp hàng trăm widget như PowerBI / Tableau.
4. **KHÔNG tự động cấp quyền người dùng**: Việc phân quyền người dùng là cấu hình tĩnh (Static RBAC matrix) hoặc quản lý bởi Supabase Auth, Agent không có quyền tự cấp quyền truy cập bảng cho người dùng.

---

## 6. RÀNG BUỘC KỸ THUẬT & AN TOÀN (CONSTRAINTS)

- **Môi trường Warehouse**:
  - Dev/Local: **DuckDB** in-memory / file `data/tpch.duckdb` (sinh qua `CALL dbgen(sf=0.1)` hoặc `sf=1`).
  - Production/Demo: **Google BigQuery Sandbox** (sử dụng dataset TPC-H mẫu hoặc nạp file Parquet từ DuckDB).
- **Ràng buộc an toàn**:
  - Mọi câu lệnh trước khi chạy bắt buộc phải được parse thành công qua AST parser.
  - Tự động chèn mệnh đề `LIMIT 1000` cho mọi truy vấn để phòng tránh crash trình duyệt do dữ liệu quá lớn.
  - Giới hạn thời gian truy vấn (Timeout): Tối đa 30 giây cho mỗi lệnh thực thi warehouse.
- **Ràng buộc chi phí LLM**:
  - Áp dụng phân tầng model (Model Tiering): SQL Generator dùng model chất lượng cao (Claude 3.5 Sonnet / GPT-4o); các khâu tóm tắt và tra cứu dùng model tiết kiệm (Claude 3.5 Haiku / GPT-4o-mini).
  - Không tốn token LLM cho khâu kiểm duyệt an toàn (toàn bộ chạy bằng code logic thuần).

---

## 7. KẾ HOẠCH PHÂN KỲ PHÁT TRIỂN (PROJECT PHASING)

```
[ Phase 1: MVP - Build Phase ] (Phạm vi đồ án hiện tại)
├── Core Engine: DeepAgents điều phối + LangGraph Control Subgraph.
├── Hàng rào Governance: AST Validator (sqlglot) + RBAC + Cost Guard + Audit Log.
├── Trải nghiệm người dùng: Clarification Loop + HITL Modal + Biểu đồ Recharts.
├── Kho dữ liệu: 8 bảng TPC-H sinh tự động qua DuckDB extension (scale factor 0.1 / 1).
└── Bộ đánh giá: Benchmark 50 câu hỏi tiếng Việt dựa trên 22 mẫu TPC-H chuẩn đo Execution Accuracy.

[ Phase 2: Mở rộng trong tương lai ] (Hướng phát triển tiếp theo)
├── Hỗ trợ Data Mesh: Truy vấn liên kho dữ liệu (Federated Query qua Trino/DuckDB).
├── Đồng bộ tự động dbt Semantic Layer trực tiếp từ GitHub repository của Data team.
└── Tạo Dashboard tự động theo chủ đề qua chuỗi hội thoại (Interactive Canvas).
```
