# ADR-0001: Lựa chọn Mô hình Hybrid (DeepAgents + LangGraph) và Chuẩn hóa trên TPC-H Benchmark

- **Mã bản ghi**: `ADR-0001`
- **Trạng thái**: `Accepted` (Đã phê duyệt & áp dụng)
- **Ngày quyết định**: `2026-09-08`
- **Người đề xuất**: AI Agent Architect & Development Team
- **Tài liệu liên quan**:
  - [agent-architecture-v2.md](file:///c:/text2sql-agent/docs/agent-architecture-v2.md)
  - [ARCHITECTURE.md](file:///c:/text2sql-agent/docs/ARCHITECTURE.md)
  - [PRD.md](file:///c:/text2sql-agent/docs/PRD.md)
  - [DATABASE_SCHEMA.md](file:///c:/text2sql-agent/docs/DATABASE_SCHEMA.md)
  - [DATA_FLOW.md](file:///c:/text2sql-agent/docs/DATA_FLOW.md)

---

## 1. BỐI CẢNH & VẤN ĐỀ ĐẶT RA (CONTEXT & PROBLEM STATEMENT)

Dự án phát triển một hệ sinh thái **AI Agent Text-to-SQL Self-Service Analytics** cho phép người dùng nghiệp vụ đặt câu hỏi tự nhiên bằng tiếng Việt để truy xuất dữ liệu kho. Trong môi trường doanh nghiệp thực tế, hệ thống phải giải quyết đồng thời hai yêu cầu luôn mâu thuẫn:

1. **Yêu cầu về Tính linh hoạt trong Suy luận (Agentic Reasoning)**:
   - Hiểu được các câu hỏi tiếng Việt phong phú, nhận diện được câu hỏi mơ hồ để chủ động hỏi lại (Clarification).
   - Lập kế hoạch phân rã truy vấn, liên kết đúng bảng/cột và giá trị dữ liệu thực tế (Schema & Entity Linking).
   - Khả năng tự sửa lỗi truy vấn (Self-Correction) khi database báo lỗi cú pháp hoặc logic.
2. **Yêu cầu về Tính tất định & An toàn Dữ liệu (Deterministic Governance)**:
   - Chặn đứng 100% các câu lệnh phá hoại cấu trúc hoặc thay đổi dữ liệu (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`).
   - Kiểm soát truy cập theo vai trò (RBAC): Chặn nhân viên nghiệp vụ (`Analyst`) xem các trường PII và tài chính nhạy cảm.
   - Kiểm soát chi phí quét dữ liệu (Cost Guard): Ước tính trước số bytes scanned trên bảng lớn, ngăn ngừa query gây tràn ngân sách cloud.
   - Bắt buộc phải có sự xác nhận của con người (Human-in-the-Loop) và luôn ghi nhận Audit Log.

Nếu chỉ dùng LLM để tự quyết định toàn bộ quy trình kiểm duyệt thông qua Prompting, hệ thống sẽ đối mặt với rủi ro bị Jailbreak, ảo giác (Hallucination), hoặc model "bỏ quên" các bước kiểm tra an ninh.

Đồng thời, dự án cần một **bộ dữ liệu chuẩn doanh nghiệp có cấu trúc phức tạp** và hệ thống truy vấn đối chứng (Ground-truth) đáng tin cậy để đo lường độ chính xác thực thi (Execution Accuracy).

---

## 2. CÁC PHƯƠNG ÁN ĐÃ XEM XÉT (CONSIDERED OPTIONS)

### Phương án 1: Chuỗi tuần tự tuyến tính (Pure LangChain / LCEL Chain)
- *Mô tả*: Dùng một chuỗi tuần tự `Prompt -> LLM -> SQL Parser -> Execute -> Response`.
- *Ưu điểm*: Cài đặt nhanh, đơn giản.
- *Lý do loại bỏ*: Không hỗ trợ vòng lặp tự sửa lỗi (Looping), không có cơ chế rẽ nhánh khi câu hỏi mơ hồ, không hỗ trợ tạm dừng/đánh thức (Pause/Resume) phiên làm việc cho Human-in-the-loop.

### Phương án 2: Agent tự trị gọi công cụ tuần tự (Pure ReAct Agent)
- *Mô tả*: Một Agent duy nhất tự do gọi các công cụ: `schema_search`, `check_rbac`, `dry_run`, `execute_sql`, `log_audit`.
- *Ưu điểm*: Linh hoạt, model tự chọn thứ tự gọi tool.
- *Lý do loại bỏ*: **Không có tính tất định**. Không có gì đảm bảo LLM sẽ luôn luôn gọi `check_rbac` trước khi gọi `execute_sql`, hoặc luôn nhớ gọi `log_audit` khi có lỗi xảy ra. Điều này vi phạm nghiêm trọng tiêu chuẩn an toàn dữ liệu doanh nghiệp.

### Phương án 3: Mô hình Hybrid (DeepAgents Harness + LangGraph Control Subgraph) trên chuẩn TPC-H Benchmark *(Phương án được chọn)*
- *Mô tả*:
  - **Tầng ngoài (DeepAgents)**: Đóng vai trò "Bộ não suy luận" chịu trách nhiệm lập kế hoạch (`write_todos`), quản lý Context qua Virtual Filesystem (`session://{thread_id}/`), điều phối các subagents chuyên biệt (Clarifier, Schema Retriever, SQL Generator, Response Synthesizer).
  - **Tầng trong (LangGraph Subgraph)**: Đóng gói thành một `CompiledSubAgent` chạy bằng **code logic Python thuần (0 token LLM)** để kiểm duyệt 6 bước bất biến: AST Sanitizer (`sqlglot`), RBAC Policy, Dry-run Cost Guard, HITL `interrupt`, Warehouse Executor và Audit Logger.
  - **Kho dữ liệu**: Chuẩn hóa toàn bộ schema trên **8 bảng TPC-H Benchmark** kết hợp giữa DuckDB (dev local) và Google BigQuery (production demo).

---

## 3. QUYẾT ĐỊNH KIẾN TRÚC (DECISION OUTCOME)

Nhóm quyết định chọn **Phương án 3: Mô hình Hybrid DeepAgents + LangGraph trên chuẩn TPC-H**.

### Phân công trách nhiệm ranh giới:
```
[TẦNG NGHĨ - DeepAgents Harness]
├── 1. Supervisor: Điều phối kế hoạch, quản lý Session Virtual Filesystem
├── 2. Clarifier: Nhận diện mơ hồ & sinh câu hỏi làm rõ
├── 3. Schema & Value Retriever: Vector DDL + Distinct values + dbt metrics
├── 4. SQL Generator: Soạn thảo SQL kèm giải trình & nhận phản hồi lỗi
└── 5. Response Synthesizer: Đề xuất cấu hình Recharts & tóm tắt insight kinh doanh

                  ↓ (Bàn giao draft_sql.sql)

[TẦNG KIỂM SOÁT TẤT ĐỊNH - LangGraph Control Subgraph]
├── 1. AST Sanitizer (sqlglot): Bắt buộc SELECT, chặn DDL/DML, auto LIMIT 1000
├── 2. RBAC Policy: Chặn các cột cấm (c_phone, c_acctbal, s_phone, s_acctbal)
├── 3. Cost Guard: Dry-run đo bytes scanned trên bảng lớn lineitem
├── 4. HITL Approval: LangGraph interrupt() tạm dừng phiên chờ người duyệt
├── 5. Warehouse Executor: Timeout 30s + DuckDB/BigQuery client
└── 6. Audit Logger: Ghi nhận 100% vết truy vấn và chi phí vào bảng audit_logs
```

### Chuẩn hóa Dữ liệu trên TPC-H:
- Sử dụng 8 bảng quan hệ của TPC-H: `region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem`.
- Sử dụng công cụ native của DuckDB (`CALL dbgen(sf=0.1)`) để sinh dữ liệu mẫu nhanh chóng, chuẩn xác và không tốn phí lưu trữ.
- Sử dụng 22 câu truy vấn chuẩn của TPC-H làm cơ sở xây dựng bộ **Spider-like Benchmark 50 câu hỏi tiếng Việt** để đo Execution Accuracy (EX) và Valid SQL Rate (VSR).

---

## 4. LÝ DO & LUẬN ĐIỂM BẢO VỆ (RATIONALE)

1. **Đảm bảo tính tất định cho Governance (Zero Trust on LLM for Security)**:
   - Các quy định bảo mật, phân quyền và kiểm soát ngân sách không được phép phụ thuộc vào sự "ghi nhớ" của LLM. Bằng cách viết thành các node code thuần trong Subgraph LangGraph, luồng kiểm duyệt là bất biến 100%.
2. **Tối ưu chi phí Token LLM (Zero LLM Token for Governance)**:
   - Việc kiểm tra AST bằng `sqlglot`, đối chiếu RBAC bằng cấu trúc Set trong Python, và đo bytes scanned bằng API dry-run tiêu tốn **0 token LLM**, giúp hệ thống có tốc độ phản hồi cực nhanh (< 50ms) ở tầng kiểm duyệt.
3. **Cô lập phiên an toàn (Multi-tenant Context Isolation)**:
   - Virtual Filesystem của DeepAgents được namespaced theo `session://{thread_id}/`, giải quyết triệt để bài toán Race Condition khi nhiều người dùng gửi câu hỏi cùng lúc qua FastAPI.
4. **Chuẩn hóa đo lường khoa học (Benchmark Credibility)**:
   - Thay vì dùng dữ liệu giả định tự tạo thiếu khách quan, việc sử dụng TPC-H — tiêu chuẩn vàng của ngành công nghiệp cơ sở dữ liệu — mang lại độ tin cậy khoa học cao nhất khi bảo vệ đồ án trước hội đồng.

---

## 5. HỆ QUẢ & TÁC ĐỘNG (CONSEQUENCES & TRADE-OFFS)

### Tác động tích cực (Positive):
- Kiến trúc có luận điểm kỹ thuật sắc bén, phân định rõ ràng giữa "Suy luận linh hoạt" và "Kiểm soát an toàn".
- Dữ liệu TPC-H sẵn sàng ngay lập tức thông qua DuckDB extension, không phụ thuộc vào hạ tầng cloud phức tạp trong giai đoạn phát triển.
- Hỗ trợ đầy đủ các tính năng nâng cao: Self-Correction ($\le 3$ lần), HITL Approval, Clarification Loop.

### Thách thức & Biện pháp khắc phục (Trade-offs & Mitigations):
- **Độ phức tạp tích hợp**: Cần cầu nối đồng bộ giữa State của LangGraph và Virtual Filesystem của DeepAgents.
  - *Khắc phục*: Quy định rõ State Schema `AgentState` trong [ARCHITECTURE.md](file:///c:/text2sql-agent/docs/ARCHITECTURE.md) và [DATA_FLOW.md](file:///c:/text2sql-agent/docs/DATA_FLOW.md), dùng file path `session://{thread_id}/...` làm khóa định danh thống nhất.
- **Dialect khác biệt giữa DuckDB và BigQuery**:
  - *Khắc phục*: Sử dụng `sqlglot.transpile` hoặc cấu hình dialect linh hoạt trong prompt của SQL Generator để tương thích cả hai môi trường.

---

## 6. KẾ HOẠCH XÁC MINH & TUÂN THỦ (COMPLIANCE & VERIFICATION)

Mọi thay đổi mã nguồn tiếp theo bắt buộc phải vượt qua các bài kiểm thử tự động sau:
1. **Unit Test AST Security** (`tests/test_ast_security.py`): Chặn đứng 100% các câu truy vấn chứa `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER` hoặc SQL Injection.
2. **Unit Test RBAC Enforcement**: Kiểm tra việc chặn các cột `c_phone`, `c_acctbal`, `s_phone`, `s_acctbal` đối với role `Analyst`.
3. **Integration Test trên DuckDB TPC-H**: Đảm bảo toàn bộ 8 bảng trong thư mục `data/` được nạp thành công và thực thi được các câu lệnh SELECT cơ bản và nâng cao.
4. **Benchmark Evaluation** (`evals/benchmark_runner.py`): Đạt mục tiêu Execution Accuracy $\ge 82\%$ trên tập câu hỏi mẫu.
