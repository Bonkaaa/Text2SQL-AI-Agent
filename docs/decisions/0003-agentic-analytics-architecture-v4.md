# ADR-0003: Chuyển Đổi Từ Single-Query Text2SQL Sang Agentic Self-Service Analytics Engine (Kiến Trúc v4.0)

- **Mã bản ghi**: `ADR-0003`
- **Trạng thái**: `Accepted` (Đã phê duyệt & áp dụng)
- **Ngày quyết định**: `2026-09-24`
- **Người đề xuất**: AI Agent Architect & Development Team
- **Tài liệu liên quan**:
  - [agent-architecture-v4.md](file:///d:/Text2SQL-AI-Agent/docs/agent-architecture-v4.md)
  - [PRD.md](file:///d:/Text2SQL-AI-Agent/docs/PRD.md)
  - [IMPLEMENTATION_BLUEPRINT.md](file:///d:/Text2SQL-AI-Agent/docs/IMPLEMENTATION_BLUEPRINT.md)
  - [ADR-0001: Lựa chọn Mô hình Hybrid](file:///d:/Text2SQL-AI-Agent/docs/decisions/0001-hybrid-agent-architecture.md)
  - [ADR-0002: Bổ sung Error Diagnostic Agent](file:///d:/Text2SQL-AI-Agent/docs/decisions/0002-error-diagnostic-agent-and-modular-control-pipeline.md)

---

## 1. BỐI CẢNH & VẤN ĐỀ ĐẶT RA (CONTEXT & PROBLEM STATEMENT)

Hệ thống kiến trúc v2.0 và v3.0 ([ADR-0001](file:///d:/Text2SQL-AI-Agent/docs/decisions/0001-hybrid-agent-architecture.md), [ADR-0002](file:///d:/Text2SQL-AI-Agent/docs/decisions/0002-error-diagnostic-agent-and-modular-control-pipeline.md)) vận hành trên giả định: **"Mỗi câu hỏi của người dùng được giải quyết trọn vẹn bằng 1 câu truy vấn SQL duy nhất và 1 biểu đồ phản hồi"**.

Trong quá trình đánh giá thực tế trên bộ dữ liệu chuỗi cung ứng TPC-H Benchmark, giả định này bộc lộ những hạn chế kỹ thuật và nghiệp vụ nghiêm trọng:

1. **Không phản ánh đúng nghiệp vụ phân tích dữ liệu (Analytical Workflow Gap)**:
   - Một Data Analyst khi nhận câu hỏi kinh doanh (ví dụ: *"Tại sao lợi nhuận quý 3/1995 giảm sút?"*) không bao giờ viết 1 câu SQL khổng lồ chứa hàng chục phép JOIN/Subquery để trả lời mọi thứ cùng lúc. Quy trình tự nhiên luôn là: Khảo sát xu hướng tổng quan $\to$ Chia nhỏ thành các giả thuyết (do chiết khấu, do đơn hàng bị hủy, hay do nhà cung cấp giao trễ) $\to$ Chạy chuỗi truy vấn thăm dò $\to$ Đối chiếu số liệu và rút ra kết luận.
   - Việc ép LLM sinh 1 câu SQL duy nhất cho câu hỏi phức tạp làm tăng vọt tỷ lệ sinh sai cú pháp và ảo giác tên cột.
2. **Sự nhập nhằng trong khâu tổng hợp (Coupled Synthesizer)**:
   - Node `Synthesizer` ở v3.0 vừa phải đọc hiểu bảng số liệu, vừa phải tính toán độ lệch tăng trưởng, vừa phải sinh mã cấu hình biểu đồ Recharts JSON. Điều này làm prompt bị quá tải (prompt bloat), dẫn đến cấu hình biểu đồ thường xuyên thiếu trường hoặc insight hời hợt.
3. **Lỗ hổng truyền thông bằng Regex thô (Fragile Regex Scraping)**:
   - Tại `src/api/routes/query.py`, mã nguồn backend phải dùng biểu thức chính quy (`re.search(r"```sql(.*?)```")`) để cào dữ liệu từ chuỗi text Markdown tiếng Việt mà LLM trả về. Đây là một anti-pattern nghiêm trọng: chỉ cần LLM đổi định dạng câu chữ, API sẽ không trích xuất được SQL và dữ liệu, gây lỗi màn hình trắng cho người dùng cuối.
4. **Vấn đề tích hợp kiến trúc**:
   - Nhóm cần tích hợp năng lực phân tích đa bước mới vào hệ thống mà không phá vỡ tầng `DeepAgents Supervisor` (`TodoListMiddleware`, `StateBackend`) đã được chuẩn hóa.

---

## 2. CÁC PHƯƠNG ÁN ĐÃ XEM XÉT (CONSIDERED OPTIONS)

### Phương án 1: Giữ nguyên luồng Single-Query v3.0 và ép Prompt mở rộng
- *Mô tả*: Tiếp tục duy trì 1 câu SQL duy nhất, dùng Few-shot prompt phức tạp hơn để hướng dẫn LLM viết các câu SQL có CTE đa tầng.
- *Nhược điểm*: Không giải quyết được bài toán phân tích thăm dò; các câu lệnh CTE dài 80-100 dòng cực kỳ khó kiểm duyệt an toàn và dễ làm cạn kiệt token context.

### Phương án 2: Viết lại toàn bộ hệ thống thành một LangGraph Monolithic duy nhất (Loại bỏ DeepAgents)
- *Mô tả*: Xóa bỏ hoàn toàn tầng `supervisor.py` của DeepAgents, gom toàn bộ router, planning, multi-query loop, control pipeline và synthesis vào 1 file đồ thị LangGraph lớn.
- *Nhược điểm*: Phá vỡ kiến trúc đã thống nhất trong ADR-0001; lãng phí năng lực quản lý hội thoại đa lượt, `TodoListMiddleware` và cơ chế phân tách tầng suy luận của DeepAgents.

### Phương án 3: Kiến trúc v4.0 - Option B (DeepAgents Supervisor + LangGraph Analytics SubAgent + Deterministic Control Subgraph) *(Phương án được chọn)*
- *Mô tả*:
  - **Tầng Điều Phối Trò Chuyện (DeepAgents Supervisor)**: Tiếp tục giữ vai trò Front Controller, quản lý `thread_id`, context hội thoại, và phân luồng thông qua `Intent Router` (`CONVERSATION` vs `ANALYTICS`).
  - **Tầng Phân Tích Chuyên Sâu (Analytics Subgraph)**: Đóng gói toàn bộ quy trình phân tích thành một Subgraph LangGraph khép kín, được đăng ký dưới dạng `CompiledSubAgent` (hoặc Callable Structured Tool) trong Supervisor.
  - **Kế hoạch Phân Tích Tuần Tự (`AnalysisPlan`)**: Cho phép phân rã bài toán thành tối đa 3 nhiệm vụ truy vấn tuần tự.
  - **Kế Thừa Hàng Rào Kiểm Duyệt Tất Định**: Lồng ghép trực tiếp `Control Subgraph` của v3.0 (AST, RBAC, Cost, HITL, DB Executor, Diagnostic Agent) vào từng vòng lặp truy vấn.
  - **Phân rã chức năng Phân Tích & Trình Diễn**: Tách thành `DataAnalyzer` (chuyên tính toán số liệu và xác nhận giả thuyết) và `PresentationSynthesizer` (chuyên tạo `ChartSpec`, `TableSpec`).
  - **Định Kiểu Mạnh Toàn Diện (Typed Artifact Contract)**: Bỏ hoàn toàn regex; API trao đổi trực tiếp qua Pydantic V2 Model `ArtifactBundle`.

---

## 3. CÁC QUYẾT ĐỊNH CỐT LÕI (KEY ARCHITECTURAL DECISIONS)

Nhóm thống nhất áp dụng **Phương án 3** với các quy tắc kỹ thuật cố định sau:

### 3.1. Cơ chế thực thi tuần tự (Sequential-Only Execution)
- **Quyết định**: Các nhiệm vụ trong `AnalysisPlan` ($T_1, T_2, \dots, T_N$) bắt buộc thực thi tuần tự, kết quả của $T_i$ được ghi vào `EvidenceStore` làm ngữ cảnh cho $T_{i+1}$.
- **Loại bỏ**: Tuyệt đối **không hỗ trợ thực thi song song (Parallel Execution)** và **không hỗ trợ gộp câu lệnh (Query Fusion)** trong phiên bản này nhằm tránh xung đột tài nguyên kho dữ liệu, bảo đảm tính xác thực của số liệu và giữ chi phí LLM ở mức dự đoán được.

### 3.2. Cơ chế Ngân Sách Kép (Dual-Budget Guardrail)
Tách biệt hoàn toàn hai ngân sách kiểm soát để ngăn ngừa vòng lặp vô hạn:
1. **Analysis Task Budget**: `max_analysis_tasks = 3` (Một câu hỏi không được sinh quá 3 truy vấn tuần tự).
2. **Per-Query Error Retry Budget**: `max_query_retries = 3` (Một truy vấn bị lỗi chỉ được phép sửa tối đa 3 lần thông qua `DiagnosticAgent`).

### 3.3. Hợp đồng định kiểu Pydantic (Zero-Regex Contract)
- Toàn bộ kết quả từ Subgraph trả về cho API backend phải tuân thủ nghiêm ngặt mô hình `ArtifactBundle` (`src/models/artifacts.py`).
- Cấm tuyệt đối việc sử dụng `re.search` để bóc tách SQL hoặc chuỗi JSON từ tin nhắn văn bản trong `src/api/routes/query.py`.

### 3.4. Chiến lược Kho dữ liệu đa môi trường (Dual Warehouse Strategy)
- Môi trường Local / Dev: Tiếp tục sử dụng **DuckDB** (`CALL dbgen(sf=0.1)`).
- Môi trường Demo & Đánh giá Nâng cao: Hỗ trợ kết nối **Google BigQuery Sandbox** hoặc **Supabase PostgreSQL** qua abstraction `WarehouseClient` để kiểm chứng chi phí quét dữ liệu thực tế (`bytes_scanned`).

---

## 4. HỆ QUẢ & QUẢN TRỊ RỦI RO (CONSEQUENCES & TRADE-OFFS)

### 4.1. Lợi ích đạt được (Positive Impacts)
- **Nâng cao năng lực giải quyết bài toán**: Hệ thống có khả năng giải quyết các câu hỏi phân tích kinh doanh đa chiều mà kiến trúc v3.0 bất khả thi.
- **Tăng độ ổn định của API**: Loại bỏ hoàn toàn lỗi crash giao diện do regex bóc tách thất bại.
- **Biểu đồ trực quan chuẩn xác**: Tách biệt khâu phân tích số liệu giúp `PresentationSynthesizer` sinh cấu hình Recharts nhất quán, không bị hallucinate trường dữ liệu.
- **Kế thừa 100% cơ chế an ninh**: Không phải viết lại khâu AST Sanitizer, RBAC và HITL.

### 4.2. Thách thức & Biện pháp giảm thiểu (Risks & Mitigations)
- **Độ trễ tăng đối với câu hỏi đa bước**: Vì phải chạy tối đa 3 truy vấn tuần tự, thời gian xử lý có thể kéo dài lên 20-30 giây.
  - *Biện pháp*: Giới hạn cứng `max_analysis_tasks = 3`; đối với câu hỏi đơn giản, Planner chỉ sinh 1 task duy nhất để hoàn thành ngay trong 3-5 giây.
- **Tăng số lượng token LLM tiêu thụ**:
  - *Biện pháp*: Phân tầng model (Model Tiering). Planner và DataAnalyzer sử dụng model nhanh/rẻ (GPT-4o-mini hoặc Claude 3.5 Haiku); chỉ khâu sinh SQL phức tạp mới kích hoạt model chất lượng cao.
