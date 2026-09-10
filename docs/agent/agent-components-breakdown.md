# Kế Hoạch Chia Nhỏ Các Thành Phần Code Cho AI Agent Text-to-SQL (v3.0)

> **Tài liệu tham chiếu**: [agent-architecture-v3.md](file:///c:/text2sql-agent/docs/agent/agent-architecture-v3.md), [agent-architecture-v2.md](file:///c:/text2sql-agent/docs/agent/agent-architecture-v2.md), [DATABASE_SCHEMA.md](file:///c:/text2sql-agent/docs/DATABASE_SCHEMA.md), [AGENTS.md](file:///c:/text2sql-agent/AGENTS.md)  

> **Mục tiêu**: Phân rã toàn bộ hệ thống Agent thành các **component độc lập, module hóa**, sắp xếp theo thứ tự phát triển từ dưới lên (Bottom-Up). Mỗi component có định nghĩa Input/Output, logic xử lý, test case xác minh độc lập trước khi tích hợp.

---

## 1. Chiến Lược Triển Khai Tuần Tự (Phased Bottom-Up Strategy)

Để tránh tình trạng "code một khối khổng lồ rồi khó debug", hệ thống được chia làm **6 Giai đoạn (Phases)**. Nguyên tắc cốt lõi:
1. **Xây nền móng trước (Foundation & Data)**: Chuẩn bị schema, database test, pydantic models và config.
2. **Kiểm soát tất định trước LLM (Deterministic Guardrails First)**: Code xong và test pass 100% AST Parser, RBAC, Cost Guard trước khi cho LLM sinh SQL.
3. **Mỗi component đều có Unit Test riêng**: Không chuyển sang component tiếp theo khi component hiện tại chưa có test pass.
4. **Cô lập theo phiên (Thread/Session State)**: Không dùng biến toàn cục hay file đè nhau trên ổ đĩa.

```
+-----------------------------------------------------------------------------------+
| Phase 0: Nền Tảng, Môi Trường & Cơ Sở Dữ Liệu TPC-H (DuckDB)                      |
+-----------------------------------------+-----------------------------------------+
                                          |
+-----------------------------------------v-----------------------------------------+
| Phase 1: Hàng Rào Kiểm Soát Tất Định (LangGraph Control Pipeline - Pure Python)   |
| (1.1 AST Sanitizer -> 1.2 RBAC Policy -> 1.3 DB Executor & Cost -> 1.4 Subgraph)   |
+-----------------------------------------+-----------------------------------------+
                                          |
+-----------------------------------------v-----------------------------------------+
| Phase 2: Tra Cứu Ngữ Nghĩa & Giá Trị Phân Loại (Schema & Value Retriever)         |
| (2.1 TPC-H Schema Context -> 2.2 Categorical Value Finder -> 2.3 Retriever Agent) |
+-----------------------------------------+-----------------------------------------+
                                          |
+-----------------------------------------v-----------------------------------------+
| Phase 3: Sinh SQL & Vòng Lặp Tự Sửa Lỗi (SQL Generator & Self-Correction)         |
| (3.1 Prompting & Dialect -> 3.2 SQL Generator -> 3.3 Error Feedback Loop <= 3)    |
+-----------------------------------------+-----------------------------------------+
                                          |
+-----------------------------------------v-----------------------------------------+
| Phase 4: Điều Phối & Tương Tác (Clarification, Supervisor & Synthesizer)          |
| (4.1 Clarification Node -> 4.2 Response Synthesizer -> 4.3 Supervisor Graph)     |
+-----------------------------------------+-----------------------------------------+
                                          |
+-----------------------------------------v-----------------------------------------+
| Phase 5: Giao Tiếp API & Đánh Giá Benchmark (FastAPI, HITL Endpoint & Evals)      |
| (5.1 FastAPI Routes -> 5.2 HITL Approve/Reject -> 5.3 Benchmark Runner 50 câu)    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Chi Tiết Từng Component Cần Code

---

### PHASE 0: NỀN TẢNG, CẤU HÌNH & DỮ LIỆU TEST TPC-H

#### Component 0.1: Cấu Hình Dự Án & Pydantic Settings
- **File**: `src/config.py`
- **Nhiệm vụ**: Đọc toàn bộ biến môi trường từ `.env` với validation chặt chẽ bằng `pydantic-settings`.
- **Nội dung code**:
  - Class `Settings`: cấu hình LLM (API key, model names, temperature), Database (DuckDB path, BigQuery project), Guardrails (max query cost bytes, default row limit, max retries = 3), Logging level.
  - Hàm `get_settings()` kèm lru_cache.
- **Dependencies**: `pydantic-settings>=2.0`, `python-dotenv`.
- **Unit Test**: `tests/test_config.py` (kiểm tra load config mặc định, load từ env mẫu, validate thiếu key bắt buộc).

#### Component 0.2: Khởi Tạo Cơ Sở Dữ Liệu TPC-H Mẫu (DuckDB Engine)
- **File**: `src/utils/tpch_seeder.py` & `scripts/init_db.py`
- **Nhiệm vụ**: Khởi tạo database DuckDB local với đầy đủ 8 bảng TPC-H (`customer`, `orders`, `lineitem`, `part`, `partsupp`, `supplier`, `nation`, `region`) bằng extension `tpch` (`CALL dbgen(sf=0.01)` phục vụ unit test nhanh, sf=0.1 cho demo).
- **Nội dung code**:
  - Hàm `seed_tpch_data(db_path: str = ":memory:", scale_factor: float = 0.01) -> duckdb.DuckDBPyConnection`.
  - Hàm `get_table_row_counts(conn) -> dict[str, int]`.
  - Hàm `verify_tpch_tables(conn) -> bool`.
- **Dependencies**: `duckdb>=1.0`.
- **Unit Test**: `tests/test_tpch_seeder.py` (kiểm tra 8 bảng đã được tạo, kiểm tra số dòng khớp tỷ lệ scale factor).

#### Component 0.3: Khai Báo Data Models & Trạng Thái Hệ Thống (State Models)
- **File**: `src/models/state.py` & `src/models/rbac.py`
- **Nhiệm vụ**: Định nghĩa các Pydantic schema cho state truyền nhận giữa các node LangGraph.
- **Nội dung code**:
  - `src/models/rbac.py`:
    - Enum `UserRole`: `ANALYST`, `ADMIN`.
    - Class `UserContext`: `user_id`, `role: UserRole`, `allowed_tables`, `denied_columns`, `session_id`, `max_cost_bytes`.
  - `src/models/state.py`:
    - TypedDict `ControlPipelineInput`: `sql: str`, `user_context: UserContext`, `session_id: str`.
    - TypedDict `ControlPipelineOutput`: `is_valid: bool`, `error_type: Optional[str]`, `error_message: Optional[str]`, `data: Optional[list[dict]]`, `columns: Optional[list[str]]`, `bytes_scanned: int`, `execution_time_ms: float`.
    - TypedDict `AgentState`: Toàn bộ state bao gồm câu hỏi, clarification status, retrieved schema, draft SQL, retry count, hitl status, execution result, visualization config.
- **Dependencies**: `pydantic>=2.0`, `typing_extensions`.
- **Unit Test**: `tests/test_state_models.py` (kiểm tra serialize/deserialize state).

---

### PHASE 1: HÀNG RÀO KIỂM SOÁT TẤT ĐỊNH (LANGGRAPH CONTROL PIPELINE)
> **Nguyên tắc**: 100% code Python thuần + AST parser. Tuyệt đối không gọi LLM trong phase này.

#### Component 1.1: AST Sanitizer & SQL Validator
- **File**: `src/utils/ast_sanitizer.py`
- **Nhiệm vụ**: Phân tích cây cú pháp trừu tượng (AST) của câu lệnh SQL bằng `sqlglot`.
- **Nội dung code**:
  - Hàm `sanitize_and_validate_sql(sql: str, dialect: str = "duckdb", default_limit: int = 1000) -> ASTValidationResult`:
    - Chỉ cho phép root expression là `exp.Select` (hoặc CTE bắt đầu bằng `WITH ... SELECT`).
    - Chặn đứng mọi câu lệnh thay đổi dữ liệu: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `CREATE`.
    - Chặn multiple statements (tránh SQL Injection nối dấu chấm phẩy `; DROP TABLE ...`).
    - Kiểm tra mệnh đề `LIMIT`: Nếu chưa có `LIMIT`, tự động tiêm `LIMIT 1000` vào AST; nếu người dùng viết `LIMIT > 1000`, tự động giới hạn lại về 1000 đối với role không phải Admin.
    - Trích xuất danh sách các bảng (`tables_used`) và các cột (`columns_used`) xuất hiện trong query.
- **Dependencies**: `sqlglot>=25.0`.
- **Unit Test**: `tests/test_ast_sanitizer.py`:
  - Cho phép `SELECT ... FROM orders JOIN lineitem ...`.
  - Chặn `DROP TABLE customer;`, `UPDATE lineitem SET ...`, `SELECT * FROM orders; DELETE FROM part;`.
  - Tự động bổ sung `LIMIT 1000` cho câu query thiếu LIMIT.

#### Component 1.2: Bộ Kiểm Tra Quyền Hạn Dữ Liệu (RBAC Policy Enforcer)
- **File**: `src/utils/rbac_enforcer.py`
- **Nhiệm vụ**: So khớp danh sách bảng và cột trích xuất từ AST với quyền hạn của `UserRole`.
- **Nội dung code**:
  - Cấu hình ma trận quyền TPC-H:
    - Role `Analyst`: Được đọc toàn bộ 8 bảng nghiệp vụ, nhưng **CẤM** các cột PII/Tài chính cá nhân (`customer.c_phone`, `customer.c_acctbal`, `supplier.s_phone`, `supplier.s_acctbal`), cấm bảng audit nội bộ.
    - Role `Admin`: Toàn quyền truy cập.
  - Hàm `enforce_rbac_policy(tables_used: list[str], columns_used: list[str], user_context: UserContext) -> RBACCheckResult`:
    - Nếu vi phạm: Trả về danh sách cụ thể các cột/bảng bị từ chối kèm thông báo lỗi thân thiện để gửi ngược về cho SQL Generator sửa lại.
- **Dependencies**: Code thuần.
- **Unit Test**: `tests/test_rbac_enforcer.py`:
  - Role Analyst query `c_name, c_mktsegment` -> PASS.
  - Role Analyst query `c_name, c_phone, c_acctbal` -> FAIL (báo lỗi cấm cột `c_phone`, `c_acctbal`).
  - Role Admin query `c_phone` -> PASS.

#### Component 1.3: Warehouse Connector & Cost Guard (Dry-run)
- **File**: `src/utils/db_connector.py`
- **Nhiệm vụ**: Kết nối thực thi trên DuckDB/BigQuery, đo lường chi phí trước khi chạy và áp đặt giới hạn timeout.
- **Nội dung code**:
  - Class `BaseWarehouseConnector` (Abstract base) & `DuckDBConnector`:
    - Hàm `estimate_query_cost(sql: str, max_budget_bytes: int = 1073741824) -> CostEstimateResult`:
      - DuckDB: Chạy `EXPLAIN (FORMAT JSON)` lấy ước lượng số dòng hoặc kích thước bảng scan.
      - BigQuery: Gọi API với flag `dry_run=True` để lấy chính xác `total_bytes_processed`.
    - Hàm `execute_query(sql: str, timeout_seconds: int = 30) -> QueryResult`:
      - Thực thi query, kiểm soát timeout và ngắt query nếu vượt ngưỡng.
      - Chuyển đổi kết quả sang định dạng danh sách dict + metadata kiểu dữ liệu từng cột.
      - Đo đạc chính xác thời gian thực thi (`execution_time_ms`).
- **Dependencies**: `duckdb`, `google-cloud-bigquery` (tùy chọn).
- **Unit Test**: `tests/test_db_connector.py` (chạy query thử nghiệm, test bắt lỗi timeout, test bắt lỗi syntax).

#### Component 1.4: Audit Logger (Ghi Nhật Ký Truy Vấn)
- **File**: `src/utils/audit_logger.py`
- **Nhiệm vụ**: Ghi nhận toàn bộ thông tin truy vấn (thành công hoặc thất bại) vào cơ sở dữ liệu audit/file log có cấu trúc (JSON).
- **Nội dung code**:
  - Schema log: `query_id`, `session_id`, `user_id`, `role`, `question`, `sql`, `status` (`SUCCESS` / `BLOCKED_RBAC` / `BLOCKED_AST` / `TIMEOUT` / `ERROR`), `bytes_scanned`, `execution_time_ms`, `error_message`, `created_at`.
  - Class `AuditLogger` & hàm tiện ích `log_audit_event(event: AuditEvent) -> bool` chạy an toàn không làm gián đoạn luồng chính nếu log thất bại (Fail-Safe).
- **Dependencies**: `loguru` hoặc `logging` chuẩn.
- **Unit Test**: `tests/test_audit_logger.py`.

#### Component 1.5: LangGraph Control & Diagnostic Subgraph (Đóng Gói Thành Subgraph Hoàn Chỉnh)
- **Thư mục package**: `src/agents/control_pipeline/`
  - `nodes.py`: Chứa các node functions xử lý độc lập (`ast_check_node`, `rbac_check_node`, `cost_guard_node`, `hitl_gate_node`, `execute_node`, `audit_node`, `err_node`).
  - `routers.py`: Chứa các hàm conditional edge điều hướng luồng (`route_after_ast`, `route_after_rbac`, `route_after_cost`, `route_after_hitl`, `route_after_execute`).
  - `diagnostic.py`: Chứa node Agentic `error_diagnostic_node` (`ERROR_DIAGNOSTIC_AGENT`) sử dụng LLM Tier 2 để chẩn đoán nguyên nhân lỗi sâu và tạo Actionable Feedback.
  - `builder.py`: Khởi tạo `StateGraph(ControlState)`, lắp ghép node + edge, compile thành Runnable Graph.
  - `__init__.py`: Re-export `create_control_pipeline_graph`, `run_control_pipeline`, và các kiểu dữ liệu liên quan.
- **Nhiệm vụ**: Xây dựng đồ thị con (Subgraph) kết nối tuần tự các chốt chặn an toàn tất định, kết hợp với Agent chẩn đoán lỗi thông minh:
  `AST_CHECK` -> `RBAC_CHECK` -> `COST_GUARD` -> `HITL_APPROVAL` (nếu cần) -> `EXECUTE` -> `AUDIT_LOG`
  - Nếu gặp lỗi ở bất kỳ khâu nào -> chuyển sang `ERR_NODE` -> chuyển tiếp qua `ERROR_DIAGNOSTIC_AGENT` (tạo chỉ dẫn sửa lỗi Actionable Feedback) -> kết thúc Subgraph để gửi trả về cho `SQL Generator` tự sửa.
- **Nội dung code chi tiết**:
  - Node `ast_check_node`: Gọi Component 1.1 (`sanitize_and_validate_sql`). Nếu lỗi cú pháp hoặc DDL/DML -> chuyển `err_node`.
  - Node `rbac_check_node`: Gọi Component 1.2 (`enforce_rbac_policy`). Nếu vi phạm bảng/cột -> chuyển `err_node`.
  - Node `cost_guard_node`: Gọi Component 1.3 (`estimate_query_cost`). Nếu vượt ngân sách `max_cost_bytes` -> chuyển `err_node`.
  - Node `hitl_gate_node`: Dùng `interrupt()` của LangGraph để tạm dừng chờ người dùng phê duyệt câu lệnh SQL. Nếu từ chối -> chuyển `err_node`.
  - Node `execute_node`: Thực thi trên database qua Component 1.3 (`execute_query`). Nếu lỗi DB runtime hoặc timeout -> chuyển `err_node`.
  - Node `audit_node`: Luôn được gọi (kể cả thành công hay thất bại) qua Component 1.4 (`log_audit_event`).
  - Node `err_node`: Đóng gói payload mã lỗi chuẩn hóa (`error_type`, `error_message`, `status`).
  - Node `diagnostic_node` (`ERROR_DIAGNOSTIC_AGENT`): Gọi LLM Tier 2 với system prompt chẩn đoán SQL để so khớp câu query lỗi với schema, tạo ra chỉ dẫn sửa lỗi ngắn gọn (Actionable Feedback).
- **Dependencies**: `langgraph>=0.2`, `langchain-core`.
- **Unit Test**: `tests/test_control_pipeline.py`:
  - Test luồng query hợp lệ -> chạy trơn tru đến execute và trả về data.
  - Test câu query chèn lệnh cấm -> bị chặn ngay tại `ast_check_node`, chuyển qua chẩn đoán lỗi.
  - Test câu query vi phạm cột RBAC -> bị chặn tại `rbac_check_node`.
  - Test câu query bị timeout -> bị ngắt an toàn và chẩn đoán timeout.
  - Test node `error_diagnostic_node` sinh ra Actionable Feedback chuẩn.

---

### PHASE 2: TẦNG TRI THỨC & TRA CỨU SCHEMA (SCHEMA & VALUE RETRIEVER)

#### Component 2.1: Semantic Schema & Metric Layer Dictionary
- **File**: `src/utils/schema_context.py`
- **Nhiệm vụ**: Khai báo cấu trúc từ điển dữ liệu 8 bảng TPC-H, quan hệ Foreign Key, mô tả ý nghĩa từng cột và công thức tính toán chuẩn (dbt semantic metrics).
- **Nội dung code**:
  - DDL chi tiết 8 bảng có kèm comment tiếng Việt.
  - Từ điển các quan hệ JOIN chuẩn (ví dụ: `lineitem.l_orderkey = orders.o_orderkey`, `orders.o_custkey = customer.c_custkey`).
  - Định nghĩa công thức nghiệp vụ mẫu TPC-H:
    - Doanh thu thực tế (Net Revenue): `SUM(l_extendedprice * (1 - l_discount))`
    - Chiết khấu trung bình: `AVG(l_discount)`
    - Lợi nhuận gộp ước tính: `SUM(l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity)`
- **Dependencies**: Code thuần.
- **Unit Test**: `tests/test_schema_context.py`.

#### Component 2.2: Categorical Value Search (Tra Cứu Giá Trị Phân Loại Thực Tế)
- **File**: `src/utils/categorical_search.py`
- **Nhiệm vụ**: Giải quyết bài toán Entity/Value Linking. Khi người dùng hỏi *"ngành ô tô"*, subagent tra cứu ra giá trị thực trong database là `'AUTOMOBILE'` trong cột `c_mktsegment`.
- **Nội dung code**:
  - Trích xuất và cache danh sách distinct values của các cột phân loại chính trong TPC-H:
    - `c_mktsegment`: `BUILDING`, `AUTOMOBILE`, `MACHINERY`, `HOUSEHOLD`, `FURNITURE`.
    - `r_name`: `AFRICA`, `AMERICA`, `ASIA`, `EUROPE`, `MIDDLE EAST`.
    - `p_type`: Các mã loại phụ tùng (ví dụ: `ECONOMY ANODIZED STEEL`, `PROMO BRUSHED BRASS`...).
    - `o_orderstatus`: `O` (Open), `F` (Fulfilled), `P` (Pending).
  - Hàm `find_matching_categorical_values(user_query: str) -> list[CategoricalMatch]`: So khớp từ khóa tiếng Việt / fuzzy matching để tìm đúng giá trị và tên cột tương ứng trong database.
- **Dependencies**: `rapidfuzz` hoặc thư viện vector search nhẹ.
- **Unit Test**: `tests/test_categorical_search.py` (test tìm kiếm "châu á" -> `r_name = 'ASIA'`, "ngành máy móc" -> `c_mktsegment = 'MACHINERY'`).

#### Component 2.3: Subagent: Schema & Value Retriever
- **File**: `src/agents/schema_retriever.py`
- **Nhiệm vụ**: Kết hợp Semantic Schema (2.1) và Categorical Values (2.2) để chọn lọc ra đúng các bảng, cột và giá trị cần thiết cho câu hỏi của người dùng, đóng gói thành context tối giản.
- **Nội dung code**:
  - Hàm `retrieve_schema_context(question: str) -> str`:
    - Phân tích câu hỏi -> tìm top relevant tables.
    - Tìm các categorical values khớp trong câu hỏi.
    - Trích xuất DDL của các bảng liên quan kèm foreign keys để join.
    - Trả về chuỗi Markdown tóm tắt ngữ cảnh schema.
- **Dependencies**: `langchain-core` / OpenAI client.
- **Unit Test**: `tests/test_schema_retriever.py`.

---

### PHASE 3: SINH SQL & VÒNG LẶP TỰ SỬA LỖI (SQL GENERATOR & SELF-CORRECTION)

#### Component 3.1: SQL Prompt Engineering & Dialect Adapter
- **File**: `src/agents/prompts/sql_generator_prompt.py`
- **Nhiệm vụ**: Thiết kế System Prompt chuẩn mực cho việc sinh SQL, tối ưu dialect cho DuckDB.
- **Nội dung code**:
  - System Prompt với các quy tắc vàng:
    - Chỉ sinh duy nhất mã SQL, không giải thích dài dòng ở bước này.
    - Bắt buộc dùng đúng tên bảng/cột từ Schema Context.
    - Sử dụng chuẩn công thức metric (ví dụ `l_extendedprice * (1 - l_discount)` cho doanh thu).
    - Quy tắc ép kiểu ngày tháng chuẩn dialect (`CAST('1995-01-01' AS DATE)` hoặc `DATE '1995-01-01'`).
  - Error-Feedback Prompt Template: Cấu trúc prompt đưa lỗi kỹ thuật từ Phase 1 (AST lỗi, cột cấm RBAC, syntax error từ DB) vào để LLM sửa chữa.
- **Unit Test**: Kiểm tra format prompt với các biến đầu vào.

#### Component 3.2: Subagent: SQL Generator
- **File**: `src/agents/sql_generator.py`
- **Nhiệm vụ**: Nhận câu hỏi, schema context và lịch sử lỗi (nếu có) để gọi LLM sinh câu lệnh SQL.
- **Nội dung code**:
  - Hàm `generate_sql(question: str, schema_context: str, error_context: Optional[str] = None, user_role: str = "Analyst") -> str`:
    - Gọi LLM (Tier 1: GPT-4o / Claude 3.5 Sonnet).
    - Làm sạch chuỗi SQL trả về (cắt bỏ markdown ```sql ```).
- **Dependencies**: `langchain-openai` hoặc `google-genai` / `anthropic`.
- **Unit Test**: `tests/test_sql_generator.py` (mock LLM output, kiểm tra output trả về là câu SQL sạch).

#### Component 3.3: Bounded Self-Correction Loop (Vòng Lặp Sửa Lỗi Tự Động <= 3 Lần)
- **File**: Tích hợp trong luồng điều phối chính (`src/agents/supervisor.py` & `src/agents/control_pipeline.py`)
- **Nhiệm vụ**: Kết nối SQL Generator (Phase 3) với Control Pipeline (Phase 1).
- **Nội dung code**:
  - Kiểm tra điều kiện `retry_count < 3`:
    - Nếu Control Pipeline trả về `is_valid == False`:
      - Tăng `retry_count += 1`.
      - Nạp `error_message` vào `error_context`.
      - Kích hoạt lại `generate_sql`.
    - Nếu `retry_count >= 3`:
      - Dừng luồng, trả về thông báo thất bại nhã nhặn kèm hướng dẫn người dùng đặt lại câu hỏi.
      - Log audit thất bại.
- **Unit Test**: `tests/test_self_correction.py` (chạy giả lập lỗi cú pháp lần 1 -> sửa thành công lần 2; giả lập lỗi 3 lần liên tiếp -> kích hoạt graceful exit).

---

### PHASE 4: ĐIỀU PHỐI TỔNG THỂ & TƯƠNG TÁC (CLARIFICATION, SUPERVISOR & SYNTHESIZER)

#### Component 4.1: Khâu Làm Rõ Câu Hỏi Mơ Hồ (Clarification Agent)
- **File**: `src/agents/clarification.py`
- **Nhiệm vụ**: Đánh giá câu hỏi người dùng có đủ điều kiện lọc cần thiết hay không trước khi tốn token sinh SQL.
- **Nội dung code**:
  - Hàm `check_clarification_needed(question: str) -> ClarificationResult`:
    - Nhận biết các câu hỏi quá chung chung (ví dụ: *"Doanh thu thế nào?"* -> thiếu khoảng thời gian, thiếu khu vực).
    - Nếu thiếu: Trả về `needs_clarification = True`, kèm câu hỏi làm rõ gợi ý các phương án lựa chọn A, B, C.
    - Nếu câu hỏi đã rõ ràng (ví dụ: *"Top 5 khách hàng mua nhiều nhất năm 1995 tại Châu Á"*): Trả về `needs_clarification = False`.
- **Unit Test**: `tests/test_clarification.py` (kiểm tra với bộ câu hỏi mơ hồ mẫu và câu hỏi rõ ràng mẫu).

#### Component 4.2: Subagent: Response Synthesizer & Đề Xuất Biểu Đồ
- **File**: `src/agents/synthesizer.py`
- **Nhiệm vụ**: Đọc dữ liệu bảng trả về từ database để sinh lời giải thích kinh doanh và cấu hình biểu đồ (Recharts schema).
- **Nội dung code**:
  - Hàm `synthesize_response(question: str, data: list[dict], columns: list[str]) -> SynthesizedOutput`:
    - Phân tích kiểu dữ liệu: Nếu có cột ngày tháng + cột số lượng/tiền -> đề xuất `line` hoặc `area`. Nếu có cột phân loại (< 8 categories) -> đề xuất `bar` hoặc `pie`.
    - Sinh JSON cấu hình Recharts frontend: `{ chart_type: "bar", x_axis: "nation_name", y_axis: "total_revenue", title: "..." }`.
    - Viết tóm tắt insight kinh doanh bằng tiếng Việt (2-3 câu nêu bật con số cao nhất, xu hướng).
- **Unit Test**: `tests/test_synthesizer.py`.

#### Component 4.3: Deep Agent Supervisor (LangGraph State Graph Điều Phối Chính)
- **File**: `src/agents/supervisor.py`
- **Nhiệm vụ**: Graph mẹ (Master Graph) điều phối toàn bộ vòng đời của một yêu cầu.
- **Nội dung code**:
  - Kết nối các node:
    `USER_INPUT` -> `CLARIFICATION_CHECK` 
      - (Mơ hồ) -> `ASK_USER` -> END
      - (Rõ ràng) -> `SCHEMA_RETRIEVAL` -> `SQL_GENERATION` -> `CONTROL_PIPELINE_SUBGRAPH`
        - (Lỗi & retry < 3) -> `SQL_GENERATION`
        - (Lỗi & retry >= 3) -> `HANDLE_FAILURE` -> END
        - (Thành công) -> `RESPONSE_SYNTHESIS` -> END
  - Quản lý bộ nhớ phiên (Memory Checkpointer với `MemorySaver` hoặc `SqliteSaver`).
- **Unit Test**: `tests/test_supervisor.py` (chạy end-to-end giả lập từ câu hỏi đến kết quả).

---

### PHASE 5: GIAO TIẾP API & ĐÁNH GIÁ THỰC NGHIỆM (FASTAPI, HITL & EVALS)

#### Component 5.1: FastAPI Gateway & Endpoints
- **File**: `src/api/main.py` & `src/api/routes/query.py`
- **Nhiệm vụ**: Cung cấp RESTful API cho ứng dụng Web.
- **Nội dung code**:
  - `POST /api/v1/query/ask`: Tiếp nhận câu hỏi, session_id, role. Trả về kết quả hoặc trạng thái chờ phê duyệt (HITL).
  - `POST /api/v1/query/approve`: Nhận quyết định phê duyệt câu lệnh SQL khi graph tạm dừng tại `interrupt()`.
  - `GET /api/v1/query/history`: Lịch sử các câu hỏi trong phiên.
  - `GET /api/v1/audit/logs`: API xem audit trail dành riêng cho role Admin.
- **Dependencies**: `fastapi>=0.110`, `uvicorn`.
- **Unit Test**: `tests/test_api.py` (dùng `httpx.AsyncClient` test các endpoint).

#### Component 5.2: Bộ Benchmark Đánh Giá Độ Chính Xác (Execution Accuracy Runner)
- **File**: `evals/benchmark_runner.py` & `evals/datasets/benchmark_vi.json`
- **Nhiệm vụ**: Bộ đo lường chất lượng agent trên 50 câu hỏi tiếng Việt chuẩn TPC-H.
- **Nội dung code**:
  - File dataset `benchmark_vi.json`: 50 câu hỏi, ground-truth SQL, độ khó (Easy / Medium / Hard).
  - Runner thực thi:
    - Chạy từng câu hỏi qua Agent.
    - So sánh tập kết quả trả về của Agent SQL vs Ground-truth SQL trên DuckDB.
    - Tính toán 3 chỉ số cốt lõi: Valid SQL Rate (VSR), Execution Accuracy (EX), Tỷ lệ tự sửa lỗi thành công (Self-Correction Rate).
    - Xuất báo cáo kết quả ra bảng Markdown/HTML.
- **Unit Test**: `tests/test_eval_runner.py`.

---

## 3. Ma Trận Phụ Thuộc & Thứ Tự Thực Hiện Chi Tiết

| Thứ tự | Component | Tệp tin chính | Phụ thuộc trước | Kết quả kiểm thử (DoD) |
|---|---|---|---|---|
| **#1** | **Config & Env** | `src/config.py` | Không | Unit test đọc đúng biến môi trường `.env` |
| **#2** | **TPC-H Seeder** | `src/utils/tpch_seeder.py` | #1 | 8 bảng TPC-H có dữ liệu trong DuckDB |
| **#3** | **State & RBAC Models** | `src/models/state.py`, `rbac.py` | #1 | Serialize/Deserialize schema thành công |
| **#4** | **AST Sanitizer** | `src/utils/ast_sanitizer.py` | Không | 100% test chặn DDL/DML, thêm LIMIT pass |
| **#5** | **RBAC Enforcer** | `src/utils/rbac_enforcer.py` | #3, #4 | Chặn đúng cột PII theo role Analyst |
| **#6** | **DB Connector & Cost** | `src/utils/db_connector.py` | #1, #2 | Chạy query, đo execution_time, bắt timeout |
| **#7** | **Audit Logger** | `src/utils/audit_logger.py` | #1 | Ghi log JSON có cấu trúc |
| **#8** | **Control Subgraph** | `src/agents/control_pipeline.py` | #3, #4, #5, #6, #7 | Subgraph LangGraph pass các test case kiểm duyệt |
| **#9** | **Schema & Metrics Dict** | `src/utils/schema_context.py` | #2 | Cung cấp DDL và công thức metric |
| **#10**| **Categorical Search** | `src/utils/categorical_search.py` | #2 | Map đúng từ khóa tiếng Việt sang giá trị cột TPC-H |
| **#11**| **Schema Retriever** | `src/agents/schema_retriever.py` | #9, #10 | Trả về schema_context.md thu nhỏ chính xác |
| **#12**| **SQL Generator** | `src/agents/sql_generator.py` | #1, #9 | Sinh SQL chuẩn cú pháp DuckDB |
| **#13**| **Self-Correction** | Tích hợp Generator + Control | #8, #12 | Tự sửa lỗi sau khi bị AST hoặc DB báo lỗi (<= 3 lần) |
| **#14**| **Clarification Node**| `src/agents/clarification.py` | #1 | Nhận diện câu hỏi mơ hồ và hỏi lại gợi ý option |
| **#15**| **Response Synthesizer**| `src/agents/synthesizer.py` | #1 | Sinh Recharts JSON config + Insight tiếng Việt |
| **#16**| **Supervisor Graph** | `src/agents/supervisor.py` | #8, #11, #12, #13, #14, #15 | Graph chính chạy thông suốt end-to-end |
| **#17**| **FastAPI Gateway** | `src/api/main.py`, `routes/` | #16 | Endpoint `/ask`, `/approve` hoạt động qua Postman/Curl |
| **#18**| **Evals Benchmark** | `evals/benchmark_runner.py` | #16 | Chạy 50 câu hỏi mẫu, xuất chỉ số VSR, EX |

---

## 4. Định Nghĩa Hoàn Thành (Definition of Done - DoD) Cho Từng Bước

Trước khi chuyển sang code component tiếp theo:
1. **Mã nguồn sạch**: Được format và kiểm tra không có lỗi lint bằng lệnh:
   ```powershell
   ruff check .
   ruff format .
   ```
2. **Có Unit Test tương ứng**: File test nằm trong thư mục `tests/` với các case:
   - Happy path (Trường hợp dữ liệu đúng chuẩn).
   - Edge cases & Error path (Trường hợp vi phạm, dữ liệu rỗng, lỗi cú pháp).
   - Chạy lệnh test thành công:
     ```powershell
     pytest tests/test_<component_name>.py -v
     ```
3. **Type Annotation đầy đủ**: 100% hàm có type hints cho tham số và kiểu trả về theo chuẩn Python 3.11+.
4. **Không phụ thuộc file tĩnh toàn cục**: Mọi state được truyền qua Pydantic hoặc LangGraph State dict.
