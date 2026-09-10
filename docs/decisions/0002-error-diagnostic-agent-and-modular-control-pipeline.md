# ADR-0002: Bổ sung Node Agentic "Error Diagnostic Agent" và Mô-đun Hóa Package Control Pipeline (Kiến trúc v3.0)

- **Mã bản ghi**: `ADR-0002`
- **Trạng thái**: `Accepted` (Đã phê duyệt & áp dụng)
- **Ngày quyết định**: `2026-09-11`
- **Người đề xuất**: AI Agent Architect & Development Team
- **Tài liệu liên quan**:
  - [agent-architecture-v3.md](file:///c:/text2sql-agent/docs/agent/agent-architecture-v3.md)
  - [agent-architecture-v2.md](file:///c:/text2sql-agent/docs/agent/agent-architecture-v2.md)
  - [agent-components-breakdown.md](file:///c:/text2sql-agent/docs/agent/agent-components-breakdown.md)
  - [ADR-0001: Lựa chọn Mô hình Hybrid](file:///c:/text2sql-agent/docs/decisions/0001-hybrid-agent-architecture.md)

---

## 1. BỐI CẢNH & VẤN ĐỀ ĐẶT RA (CONTEXT & PROBLEM STATEMENT)

Trong kiến trúc v2.0 ([ADR-0001](file:///c:/text2sql-agent/docs/decisions/0001-hybrid-agent-architecture.md)), toàn bộ **LangGraph Control Pipeline (Component 1.5)** được thiết kế theo hướng **100% tất định (Deterministic - Zero LLM Token)** bằng code Python thuần và AST parser. Thiết kế này giúp bảo vệ tối đa dữ liệu doanh nghiệp và chặn đứng hoàn toàn nguy cơ SQL Injection / rò rỉ dữ liệu RBAC.

Tuy nhiên, trong quá trình rà soát và thiết kế chi tiết thực thi (Implementation Phase), nhóm phát triển nhận thấy hai hạn chế quan trọng:

1. **Thiếu tính "Agentic" trong quy trình phản hồi và tự sửa lỗi (Self-Correction Gap)**:
   - Khi câu SQL bị chặn hoặc lỗi (lỗi cú pháp sqlglot, vi phạm cột cấm RBAC, vượt timeout, hoặc lỗi runtime từ DuckDB/BigQuery như `Binder Error: Referenced column not found`), pipeline v2.0 chỉ đóng gói chuỗi lỗi kỹ thuật thô (`error_message`) đưa về cho SQL Generator.
   - SQL Generator phải tự mò mẫm từ thông báo lỗi thô của database để đoán xem mình sai ở đâu. Điều này dẫn đến hiện tượng **blind trial-and-error**, làm lãng phí số lượt retry ($\le 3$ lần) và làm giảm tỷ lệ sửa lỗi thành công (`Self-Correction Success Rate` chỉ đạt khoảng 60%).
2. **Cấu trúc mã nguồn nguyên khối (Monolithic File Anti-Pattern)**:
   - Nếu dồn toàn bộ logic của Subgraph LangGraph (định nghĩa trạng thái, 7 node functions, các hàm conditional edges, logic compile graph) vào một file duy nhất `src/agents/control_pipeline.py`, mã nguồn sẽ trở nên cồng kềnh, khó unit test độc lập từng node, và vi phạm nguyên tắc Single Responsibility.

---

## 2. CÁC PHƯƠNG ÁN ĐÃ XEM XÉT (CONSIDERED OPTIONS)

### Phương án 1: Giữ nguyên Subgraph tất định 100% (Kiến trúc v2.0 gốc)
- *Mô tả*: Chỉ dùng code Python thuần trong Control Subgraph, không thêm LLM ở bất kỳ khâu nào.
- *Ưu điểm*: Tiết kiệm 100% chi phí token cho khâu kiểm duyệt, tốc độ cực nhanh.
- *Nhược điểm*: Phản hồi lỗi nghèo nàn, thiếu tính Agentic; SQL Generator dễ lặp lại lỗi cũ trong vòng lặp Self-Correction.

### Phương án 2: Dùng LLM thay thế khâu AST Sanitizer và RBAC Check
- *Mô tả*: Cho một LLM Agent tự đọc câu SQL và tự phán đoán xem câu lệnh có an toàn hay vi phạm quyền của Analyst không.
- *Ưu điểm*: Trông có vẻ "Agentic" toàn phần.
- *Lý do loại bỏ tuyệt đối*: **Vi phạm nghiêm trọng nguyên tắc an toàn dữ liệu doanh nghiệp**. LLM có thể bị Jailbreak, Prompt Injection từ câu hỏi người dùng, hoặc ảo giác (hallucination) bỏ qua các cột nhạy cảm như `c_phone`, `c_acctbal`.

### Phương án 3: Giữ vững Hàng rào An toàn Tất định + Bổ sung Node Agentic "Error Diagnostic Agent" & Phân rã Mô-đun Gói Code *(Phương án được chọn)*
- *Mô tả*:
  - **Giữ nguyên 100% tính tất định cho các chốt chặn an ninh**: AST Check (`sqlglot`), RBAC Policy Enforcer, Cost Guard, Warehouse Executor Timeout (`self._conn.interrupt()`), và Audit Logger tiếp tục chạy bằng code Python thuần để bảo đảm an toàn dữ liệu tuyệt đối (Zero Trust on LLM for Security).
  - **Bổ sung Node Agentic `ERROR_DIAGNOSTIC_AGENT`**: Nằm tại lối ra của luồng lỗi (`Node ERR`). Khi có lỗi xảy ra, kích hoạt LLM Tier 2 (`gpt-4o-mini`) đóng vai trò "Bác sĩ chẩn đoán truy vấn", đối chiếu câu SQL lỗi với `schema_context` để sinh ra **Actionable Diagnostic Feedback** (chỉ rõ tên cột đúng, điều kiện join thiếu, cách khắc phục vi phạm RBAC) gửi về cho SQL Generator.
  - **Phân rã gói mã nguồn**: Tách `src/agents/control_pipeline/` thành package mô-đun hóa gồm các file chuyên trách: `nodes.py`, `routers.py`, `diagnostic.py`, `builder.py`, `__init__.py`.

---

## 3. QUYẾT ĐỊNH KIẾN TRÚC (DECISION OUTCOME)

Nhóm thống nhất phê duyệt **Phương án 3** và chính thức nâng cấp kiến trúc hệ thống lên **v3.0** ([agent-architecture-v3.md](file:///c:/text2sql-agent/docs/agent/agent-architecture-v3.md)).

### 3.1. Cấu trúc Luồng Điều Khiển v3.0 (LangGraph Control & Diagnostic Subgraph):
```
[draft_sql.sql]
       │
       ▼
 1. AST_CHECK (sqlglot) ───────────(Lỗi DDL/DML/Syntax)──┐
       │ (Hợp lệ)                                         │
       ▼                                                  │
 2. RBAC_CHECK (Ma trận quyền) ────(Vi phạm cột/bảng)───┤
       │ (Hợp lệ)                                         │
       ▼                                                  │
 3. COST_GUARD (EXPLAIN/Dry-run) ──(Vượt budget)────────┤
       │ (Hợp lệ)                                         │
       ▼                                                  │
 4. HITL_GATE (interrupt) ─────────(Người dùng từ chối)──┤
       │ (Phê duyệt)                                      │
       ▼                                                  │
 5. EXECUTE (DuckDB/BigQuery) ─────(Runtime/Timeout)────┤
       │ (Thành công)                                     │
       ▼                                                  │
 6. AUDIT_LOG (Ghi vết thành công)                        ▼
       │                                            Node ERR (Đóng gói mã lỗi)
       │                                                  │
       │                                                  ▼
       │                                      ERROR_DIAGNOSTIC_AGENT (Tier 2 LLM)
       │                                      (Phân tích nguyên nhân & Actionable Feedback)
       │                                                  │
       ▼                                                  ▼
 [Trả về Data Bảng]                            [Trả về Actionable Feedback cho Retry Loop]
```

### 3.2. Cấu trúc Mô-đun Hóa Package `src/agents/control_pipeline/`:
```text
src/agents/control_pipeline/
├── __init__.py       # Re-export create_control_pipeline_graph, ControlState, và API thực thi
├── nodes.py          # 7 Node functions tất định độc lập: ast_check, rbac_check, cost_guard, hitl_gate, execute, audit, err
├── routers.py        # Các hàm conditional edge định tuyến luồng điều khiển
├── diagnostic.py     # Node Agentic: ERROR_DIAGNOSTIC_AGENT (LLM Tier 2)
└── builder.py        # Lắp ráp StateGraph(ControlState), nối cạnh và compile thành Runnable
```

### 3.3. Đồng bộ hóa Data Contract trong State Model:
Bổ sung các trường dữ liệu trong [src/models/state.py](file:///c:/text2sql-agent/src/models/state.py):
- `ControlState`: Bổ sung `actionable_feedback: str | None`, `schema_context: str | None`.
- `ControlPipelineOutput`: Bổ sung `actionable_feedback: str | None`, mở rộng `status` hỗ trợ `"TIMEOUT"`.
- `UserContext`: Bổ sung trực tiếp `allowed_tables: set[str]` và `denied_columns: set[str]`.

---

## 4. LÝ DO & LUẬN ĐIỂM BẢO VỆ (RATIONALE)

1. **Cân bằng hoàn hảo giữa An toàn và Tính Agentic**:
   - Khâu an ninh dữ liệu (Guardrails) vẫn là **tất định 100%**. Tính Agentic chỉ được kích hoạt ở khâu **hỗ trợ chẩn đoán và khắc phục hậu quả (Remediation & Diagnostics)**.
2. **Nâng cao hiệu suất Self-Correction**:
   - Thay vì nạp thông báo lỗi khô khan của database vào prompt của SQL Generator, hệ thống nạp lời giải thích và gợi ý cụ thể từ Diagnostic Agent. Mục tiêu kỳ vọng nâng tỷ lệ sửa lỗi thành công (`Self-Correction Success Rate`) từ $\ge 60\%$ lên **$\ge 75\%$**.
3. **Tối ưu chi phí Token theo Model Tiering**:
   - Các truy vấn đúng cú pháp và hợp lệ (luồng thành công) tiêu tốn **0 token** trong toàn bộ Subgraph.
   - Khi có lỗi, hệ thống chỉ dùng **Model Tier 2** (siêu nhẹ, chi phí cực thấp, độ trễ < 1s) để chẩn đoán, không làm đội chi phí vận hành.
4. **Dễ kiểm thử và bảo trì (Testability & Maintainability)**:
   - Việc phân tách thành các file `nodes.py`, `routers.py`, `diagnostic.py` cho phép viết các bài Unit Test độc lập cho từng node mà không cần khởi động toàn bộ đồ thị LangGraph.

---

## 5. HỆ QUẢ & TÁC ĐỘNG (CONSEQUENCES & TRADE-OFFS)

### Tác động tích cực (Positive):
- Kiến trúc hệ thống thể hiện rõ nét tính Agentic cao cấp: Agent không chỉ biết sinh SQL mà còn có khả năng tự chẩn đoán nguyên nhân thất bại và đề xuất giải pháp sửa sai.
- Mã nguồn được tổ chức sạch sẽ, tuân thủ Clean Architecture và dễ mở rộng.
- Nâng cao độ chính xác tổng thể (Execution Accuracy) khi đánh giá trên tập benchmark.

### Thách thức & Biện pháp khắc phục (Trade-offs & Mitigations):
- **Phụ thuộc vào LLM khi chẩn đoán lỗi**: Nếu LLM Tier 2 gặp sự cố mạng hoặc timeout, luồng xử lý lỗi có thể bị nghẽn.
  - *Biện pháp khắc phục*: Trong `diagnostic.py`, cài đặt cơ chế **Fail-Safe**: Nếu gọi LLM chẩn đoán thất bại hoặc timeout quá 5 giây, node tự động fallback trả về chuỗi `error_message` kỹ thuật gốc mà không làm crash hệ thống.

---

## 6. KẾ HOẠCH XÁC MINH & TUÂN THỦ (COMPLIANCE & VERIFICATION)

Kế hoạch kiểm thử tự động cho các thành phần mới:
1. **Unit Test từng Node** (`tests/test_control_nodes.py`): Kiểm tra riêng biệt từng hàm node trong `nodes.py` với các input giả định.
2. **Unit Test Diagnostic Agent** (`tests/test_error_diagnostic.py`): Mock LLM output, kiểm tra khả năng bắt lỗi và sinh Actionable Feedback.
3. **Integration Test Subgraph** (`tests/test_control_pipeline.py`): Kiểm tra toàn bộ luồng rẽ nhánh từ `AST_CHECK` đến `AUDIT` và `DIAGNOSTIC`.
4. **Linting & Code Quality**: Đảm bảo 100% file mới tuân thủ quy chuẩn `ruff check .` và `ruff format .`.
