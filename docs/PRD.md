# PRD.md — Product Requirements Document

> **Dự án**: AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp  
> **Bộ dữ liệu chuẩn**: **TPC-H Benchmark (Wholesale & Supply Chain Analytics - 8 Tables)**  
> **Phiên bản**: 4.0  
> **Trạng thái**: Approved for Build Phase  
> **Ngày cập nhật**: 2026-09-24  
> **Tài liệu kiến trúc**: [agent-architecture-v4.md](file:///d:/Text2SQL-AI-Agent/docs/agent-architecture-v4.md)  
> **Quyết định kiến trúc**: [ADR-0003](file:///d:/Text2SQL-AI-Agent/docs/decisions/0003-agentic-analytics-architecture-v4.md)  
> **Kế hoạch triển khai**: [IMPLEMENTATION_BLUEPRINT.md](file:///d:/Text2SQL-AI-Agent/docs/IMPLEMENTATION_BLUEPRINT.md)  

---

## 1. PROJECT BRIEF (BẢN TÓM TẮT DỰ ÁN)

- **Tên sản phẩm**: **Enterprise Agentic Self-Service Analytics Engine (TPC-H Edition)**
- **Vấn đề cốt lõi (Pain Point)**:
  - Tại các doanh nghiệp thương mại, phân phối bán buôn và chuỗi cung ứng, nhân viên nghiệp vụ (Kinh doanh, Mua hàng, Quản lý kho, Vận tải) liên tục đối mặt với các câu hỏi phân tích kinh doanh đa biến: *Tại sao doanh thu khu vực giảm sút? Nhà cung cấp nào giao hàng trễ nhiều nhất? Sản phẩm nào có tỷ lệ trả hàng cao vượt mức trung bình?*
  - Hiện tại, mọi yêu cầu phân tích đều phải gửi ticket sang đội ngũ Data Analyst / Data Engineer. Thời gian phản hồi kéo dài từ **2 đến 5 ngày**, gây nghẽn quyết định nhập hàng, điều tiết tồn kho và đàm phán chiết khấu.
  - Các công cụ Text-to-SQL truyền thống trên thị trường chỉ hỗ trợ mô hình thô sơ: **"1 câu text $\to$ 1 câu SQL đơn lẻ $\to$ 1 bảng kết quả"**. Mô hình này hoàn toàn bất lực trước các bài toán phân tích kinh doanh thực tế đòi hỏi thăm dò nhiều bước và kiểm chứng giả thuyết.
  - Sự kết hợp lỏng lẻo giữa phân tích số liệu và sinh biểu đồ dẫn đến việc LLM thường xuyên ảo giác trường dữ liệu (hallucination) hoặc trả về insight chung chung, thiếu căn cứ số học.
- **Giải pháp (Solution)**:
  - Xây dựng một **Agentic Self-Service Analytics Engine** cho phép người dùng hỏi đáp bằng **tiếng Việt tự nhiên** trên kho dữ liệu chuẩn TPC-H.
  - Mô phỏng chính xác phương pháp luận làm việc của một **Senior Data Analyst**:
    1. *Hiểu bài toán*: Tiếp nhận câu hỏi, làm rõ các điểm mơ hồ (Clarification Loop).
    2. *Lập kế hoạch phân tích (`AnalysisPlan`)*: Đặt mục tiêu và phân rã thành tối đa 3 nhiệm vụ truy vấn tuần tự để kiểm chứng các giả thuyết.
    3. *Thực thi & Thu thập bằng chứng*: Sinh SQL tập trung, đưa qua hàng rào kiểm duyệt an toàn tuyệt đối (Deterministic Control Subgraph), tích lũy số liệu vào `EvidenceStore`.
    4. *Phân tích chuyên sâu (`DataAnalyzer`)*: Tính toán các chỉ số tăng trưởng ($\Delta\%$), tỷ trọng đóng góp, phát hiện ngoại lệ.
    5. *Trình diễn chuẩn chỉ (`PresentationSynthesizer`)*: Sinh biểu đồ Recharts tối ưu và xuất bản gói kết quả định kiểu mạnh (`ArtifactBundle`).
- **Đối tượng sử dụng (Target Users)**:
  1. *Business Users / Supply Chain & Sales Analysts (Role: `Analyst`)*: Cần số liệu và insight phân tích nhanh chóng mà không cần kỹ năng viết SQL chuyên sâu.
  2. *Data Team / Warehouse Administrators (Role: `Admin`)*: Cần giảm tải yêu cầu ad-hoc, muốn kiểm soát an toàn tuyệt đối (Zero DML/DDL, RBAC) và định lượng chi phí quét dữ liệu kho cloud.

---

## 2. MỤC TIÊU & CHỈ SỐ THÀNH CÔNG (GOALS & SUCCESS METRICS)

### 2.1. Mục tiêu sản phẩm (Product Goals)
- Rút ngắn thời gian từ lúc phát sinh bài toán nghiệp vụ đến khi có báo cáo phân tích kèm biểu đồ từ **vài ngày xuống dưới 30 giây**.
- Trao quyền tự phục vụ (Self-service) cho các bài toán phân tích ad-hoc từ đơn giản đến phức tạp trên 8 bảng TPC-H.
- Đảm bảo **an toàn dữ liệu tuyệt đối (Zero Trust on LLM for Security)**: Chặn đứng 100% các thao tác thay đổi dữ liệu hoặc truy cập trái phép trường nhạy cảm.
- Loại bỏ hoàn toàn lỗi hiển thị giao diện thông qua giao thức truyền thông định kiểu mạnh (Zero Regex Scraping).

### 2.2. Chỉ số thành công đo lường được (Target Metrics)

| Chỉ số | Định nghĩa / Cách đo | Mục tiêu v4.0 |
|---|---|---|
| **Execution Accuracy (EX)** | Tỷ lệ kết quả truy vấn sinh ra trùng khớp với Ground-truth (TPC-H Q1-Q22) | $\ge 82\%$ |
| **Valid SQL Rate (VSR)** | Tỷ lệ câu SQL sinh ra đúng cú pháp và chạy thành công trên Warehouse | $\ge 95\%$ |
| **Governance Compliance** | Tỷ lệ chặn đứng 100% các câu lệnh biến đổi dữ liệu (DML/DDL) và vi phạm RBAC | **100%** |
| **Self-Correction Success Rate** | Tỷ lệ truy vấn lỗi được sửa thành công nhờ `DiagnosticAgent` ($\le 3$ lần retry) | $\ge 65\%$ |
| **Multi-Query Plan Completion** | Tỷ lệ các kế hoạch phân tích nhiều bước hoàn thành trọn vẹn và tổng hợp thành công | $\ge 85\%$ |
| **Presentation Integrity** | Tỷ lệ output chuẩn hóa Pydantic `ArtifactBundle` thành công, không dùng regex fallback | **100%** |
| **Average End-to-End Latency** | Tổng thời gian hoàn thành (bao gồm lập kế hoạch, truy vấn và phân tích) | $< 30$ giây |

---

## 3. CHÂN DUNG NGƯỜI DÙNG & USER STORIES

### 3.1. Chân dung người dùng (User Personas)
- **Persona 1: Nguyễn Văn An — Supply Chain & Sales Analyst (Role: `Analyst`)**
  - *Mục tiêu*: Tra cứu và phân tích nguyên nhân biến động doanh số, đánh giá nhà cung cấp có tỷ lệ giao trễ cao, tìm mặt hàng tồn kho nhiều.
  - *Nỗi sợ*: Dữ liệu trích xuất sai lệch, chờ đợi đội Data quá lâu làm lỡ kế hoạch đàm phán hợp đồng.
- **Persona 2: Trần Thị Bình — Data Lead / Admin (Role: `Admin`)**
  - *Mục tiêu*: Giám sát an toàn kho dữ liệu, bảo đảm tuân thủ bảo mật thông tin (không lộ SĐT, tài khoản khách hàng), kiểm soát chi phí query BigQuery.
  - *Nỗi sợ*: AI sinh câu lệnh nguy hiểm (DROP, DELETE) hoặc quét toàn bộ bảng `lineitem` làm đội chi phí cloud.

### 3.2. Danh sách User Stories (Kiến trúc v4.0)

```
[US-01] Là một Analyst, tôi muốn hỏi các câu hỏi phân tích kinh doanh đa chiều bằng tiếng Việt tự nhiên,
        để Agent tự động chia nhỏ bài toán thành các bước truy vấn hợp lý và đưa ra lời giải hoàn chỉnh.

[US-02] Là một Analyst, khi câu hỏi của tôi chưa rõ ràng về thời gian hoặc phạm vi,
        tôi muốn Agent chủ động hỏi lại kèm gợi ý cụ thể để làm rõ mục tiêu phân tích.

[US-03] Là một Analyst, tôi muốn xem trước câu SQL, mục đích truy vấn và ước tính chi phí quét dữ liệu
        để xác nhận (Human-in-the-Loop) trước khi câu lệnh được chạy trên kho dữ liệu thật.

[US-04] Là một Analyst, tôi muốn nhận kết quả dưới dạng bản báo cáo có cấu trúc gồm:
        Tóm tắt điều hành, các luận điểm kèm số liệu chứng minh, bảng dữ liệu định dạng chuẩn và biểu đồ Recharts trực quan.

[US-05] Là một Admin, tôi muốn hệ thống phân loại câu chào hỏi xã giao và câu hỏi phân tích ngay từ cửa vào,
        để tiết kiệm tài nguyên tính toán và chi phí API token.

[US-06] Là một Admin, tôi muốn hệ thống kiểm duyệt tĩnh cú pháp bằng AST để chặn đứng 100% câu lệnh DML/DDL
        và các kỹ thuật SQL Injection tinh vi.

[US-07] Là một Admin, tôi muốn áp dụng ma trận phân quyền (RBAC) để chặn nhân viên Analyst truy vấn
        các cột nhạy cảm (c_phone, c_acctbal, s_phone, s_acctbal) ngay tại lớp kiểm duyệt trước khi chạm tới Database.

[US-08] Là một Admin, tôi muốn toàn bộ lịch sử truy vấn, chi phí quét dữ liệu và thời gian thực thi
        được ghi lại trong bảng audit_logs phục vụ thanh tra và tối ưu hóa hệ thống.
```

---

## 4. TÍNH NĂNG CỐT LÕI (CORE FEATURES)

### Feature 1: Intent Routing & Question Clarification Loop
- **Intent Router (`src/agents/router.py`)**: Tách bạch 2 luồng:
  - `CONVERSATION`: Chào hỏi, hướng dẫn, giải thích khái niệm $\to$ Trả lời trực tiếp, không truy cập Database.
  - `ANALYTICS`: Yêu cầu trích xuất dữ liệu, so sánh chỉ số $\to$ Kích hoạt Analytics SubAgent.
- **Clarification Loop (`src/agents/clarification.py`)**: Nhận diện câu hỏi thiếu điều kiện trọng yếu; trả về câu hỏi làm rõ có cấu trúc và tạm dừng chờ người dùng bổ sung thông tin.

### Feature 2: Schema Linking & Categorical Value Retriever
- **Vector Search (ChromaDB)**: Tìm kiếm semantic embedding trên DDL và mô tả nghiệp vụ của 8 bảng TPC-H (`region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem`).
- **Categorical Value Search**: Khớp chính xác các giá trị danh mục thực tế trong database (khu vực `'ASIA'`, phân khúc `'BUILDING'`, hình thức giao `'AIR'`, cờ trạng thái dòng hàng `'R'`), triệt tiêu lỗi gõ sai literal.
- **Semantic Business Metrics**: Cung cấp công thức chuẩn cho doanh thu thuần (`l_extendedprice * (1 - l_discount)`), chi phí thực tế, tỷ lệ hoàn hàng.

### Feature 3: Analysis Planner & Hypothesis Formulation
- **Lập kế hoạch phân tích (`AnalysisPlan`)**:
  - Chuyển đổi bài toán kinh doanh thành: Mục tiêu tổng quan (`goal`) + Các giả thuyết cần kiểm chứng (`hypotheses`) + Danh sách nhiệm vụ truy vấn tuần tự (`tasks`).
  - Khống chế ngân sách nghiêm ngặt: **Tối đa 3 nhiệm vụ tuần tự ($N \le 3$)**.
  - Mỗi nhiệm vụ có một mục tiêu đơn nhất, dễ viết SQL và dễ kiểm chứng.

### Feature 4: Sequential Execution & Evidence Collection Loop
- **Task Query Generator**: Viết câu SQL tập trung cho từng task đơn lẻ, kết hợp bối cảnh rút ra từ các task trước đó.
- **Evidence Accumulation (`EvidenceStore`)**: Lưu trữ có cấu trúc kết quả mẫu (data sample), số dòng, thống kê cơ bản và chi phí quét của từng task đã thực thi thành công.

### Feature 5: Hàng Rào Kiểm Duyệt Tất Định & Diagnostic Agent
Kế thừa toàn diện nền tảng an ninh vững chắc từ v3.0:
- **AST Security Sanitizer (`sqlglot`)**: Chỉ chấp nhận `SELECT`. Chặn mọi lệnh sửa đổi dữ liệu và batch statement.
- **RBAC Policy Enforcer**: Áp dụng ma trận quyền theo vai trò (`Analyst` vs `Admin`), chặn cột nhạy cảm.
- **Cost Guard**: Dry-run kiểm tra dung lượng bytes quét; chặn nếu vượt ngưỡng quota.
- **Human-In-The-Loop (HITL) Gate**: Cơ chế `interrupt()` của LangGraph yêu cầu người dùng xác nhận câu lệnh và chi phí.
- **Warehouse Timeout & Limit**: Giới hạn thời gian truy vấn 30s (`interrupt()`) và tự động chèn `LIMIT 1000`.
- **Error Diagnostic Agent**: Phân tích lỗi kỹ thuật và cung cấp phản hồi có định hướng cho Generator; khống chế vòng lặp sửa lỗi tối đa **3 lần retry (`max_retries = 3`)**.
- **Audit Logger**: Ghi log cấu trúc JSON vào bảng `audit_logs`.

### Feature 6: Decoupled Data Analysis & Presentation Synthesizer
- **Data Analyzer (`src/agents/data_analyzer.py`)**:
  - Thực hiện tính toán toán học: Độ tăng trưởng ($\Delta\%$), tỷ trọng đóng góp, độ phân tán số liệu.
  - Xác nhận hoặc bác bỏ các giả thuyết trong `AnalysisPlan`.
- **Presentation Synthesizer (`src/agents/presentation_synthesizer.py`)**:
  - Sinh cấu hình trực quan **Recharts** tối ưu (Line, Bar, Area, Composed).
  - Định dạng bảng số liệu chuẩn (tiền tệ USD, tỷ lệ phần trăm).
  - Soạn thảo bản tóm tắt điều hành bằng tiếng Việt tự nhiên chuẩn mực.
- **Typed Delivery Contract**: Đóng gói toàn bộ kết quả vào Pydantic V2 Model `ArtifactBundle`, bảo đảm 100% tương thích với API backend và Web UI.

---

## 5. NHỮNG GÌ NẰM NGOÀI PHẠM VI (NON-GOALS)

Để đảm bảo dự án hoàn thành xuất sắc và đúng hạn:

1. **KHÔNG hỗ trợ thao tác ghi / sửa dữ liệu (Zero Write/Drop)**: Hệ thống 100% là Read-Only Analytics.
2. **KHÔNG thực thi truy vấn song song hoặc gộp câu lệnh (No Parallelism & No Query Fusion)**: Các truy vấn trong một kế hoạch bắt buộc chạy tuần tự để đảm bảo độ tin cậy và kiểm soát chi phí.
3. **KHÔNG tự động sinh Dashboard vô hạn**: Hệ thống tập trung giải quyết bài toán phân tích ad-hoc theo phiên hội thoại, không thay thế các công cụ BI doanh nghiệp như Tableau/PowerBI.
4. **KHÔNG xử lý tài liệu phi cấu trúc**: Giới hạn phạm vi dữ liệu trong 8 bảng chuẩn của TPC-H Benchmark.

---

## 6. RÀNG BUỘC KỸ THUẬT & AN TOÀN (CONSTRAINTS)

### 6.1. Ràng buộc An toàn & Ngân sách (Dual-Budget Rules)
- **Analysis Task Budget**: Tối đa 3 tasks cho một câu hỏi người dùng.
- **Per-Query Retry Budget**: Tối đa 3 lần retry sửa lỗi cho một câu SQL.
- **Warehouse Execution Timeout**: Tối đa 30 giây cho mỗi lệnh thực thi.
- **Result Row Limit**: Tối đa 1000 dòng trả về cho người dùng.

### 6.2. Môi trường Kho dữ liệu (Warehouse Strategy)
- **Local Dev / Testing**: **DuckDB** file cục bộ (`data/tpch.duckdb`) hoặc in-memory via `CALL dbgen(sf=0.1)`.
- **Production Demo**: **Google BigQuery Sandbox** hoặc **Supabase Managed PostgreSQL**, kết nối thông qua abstraction `WarehouseClient`.

### 6.3. Kiến trúc Tích hợp (Integration Topology)
- Tích hợp theo **Option B**: LangGraph Analytics Subgraph được đóng gói và đăng ký dưới dạng `CompiledSubAgent` của `DeepAgents Supervisor`.

---

## 7. KẾ HOẠCH PHÂN KỲ PHÁT TRIỂN (PROJECT PHASING)

Chi tiết thực hiện theo [IMPLEMENTATION_BLUEPRINT.md](file:///d:/Text2SQL-AI-Agent/docs/IMPLEMENTATION_BLUEPRINT.md):

```
[ Phase 1: Foundation & Contracts ]
├── Xóa bỏ Regex Parsing trong src/api/routes/query.py.
├── Bổ sung Pydantic V2 models: AnalysisPlan, QueryTask, EvidenceStore, ArtifactBundle.
└── Viết Unit Tests kiểm tra hợp đồng dữ liệu.

[ Phase 2: Core Analysis Engine ]
├── Xây dựng Intent Router (CONVERSATION vs ANALYTICS).
├── Xây dựng Analysis Planner (Goal, Hypotheses, Tasks <= 3).
├── Xây dựng Data Analyzer (Math, Trends, Hypotheses verification).
└── Xây dựng Presentation Synthesizer (Recharts Spec, Table Spec, Executive Summary).

[ Phase 3: Subgraph Assembly & Option B Mounting ]
├── Lắp ráp LangGraph Analytics Subgraph với Sequential Execution Loop.
├── Tích hợp Control Pipeline Subgraph v3.0 (AST, RBAC, Cost, HITL, Diagnostic).
└── Gắn kết Subgraph vào DeepAgents Supervisor dưới dạng CompiledSubAgent.

[ Phase 4: Verification, Evaluation & Demo Delivery ]
├── Tích hợp Warehouse Client (DuckDB + BigQuery / Supabase).
├── Chạy đánh giá bộ Benchmark 50 câu hỏi tiếng Việt TPC-H (EX, VSR, Plan Success Rate).
└── Hoàn thiện Web UI Next.js hiển thị ArtifactBundle đầy đủ.
```
