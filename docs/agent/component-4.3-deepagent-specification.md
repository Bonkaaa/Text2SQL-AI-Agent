# Đặc Tả Kỹ Thuật & Danh Mục Tệp Tin Component 4.3: Deep Agent Supervisor
### Framework: LangChain `deepagents` Harness + LangGraph Control Subgraph (Hybrid Architecture)

---

## 1. Bối Cảnh & Nguyên Lý Cốt Lõi Của `deepagents`

Trong kiến trúc của đồ án ([docs/agent/data-01-agent-architecture.md](file:///c:/text2sql-agent/docs/agent/data-01-agent-architecture.md)), chúng ta lựa chọn mô hình **Hybrid**:
- **Tầng suy luận linh hoạt (Reasoning Harness)**: Sử dụng framework **`deepagents`** của LangChain (`pip install deepagents`, phiên bản `0.7.13+`).
  - Cung cấp sẵn cơ chế lập kế hoạch công việc theo dõi tiến độ qua middleware (`TodoListMiddleware` sinh tool `write_todos`).
  - Cung cấp Virtual Filesystem (`StateBackend`) làm vùng đệm chia sẻ ngữ cảnh in-memory giữa các subagents mà không làm phình context window và không lo xung đột file tĩnh trên đĩa giữa các phiên.
  - Cung cấp công cụ tích hợp **`task(subagent_name, description)`** để Deep Agent tự phân tích yêu cầu và ủy quyền (delegate) công việc cho các Subagents chuyên biệt với ngữ cảnh hoàn toàn cô lập (`mode: "isolated"`).
  - Khả năng nạp tri thức chuyên gia on-demand thông qua tham số `skills` và nạp tài liệu quy ước vận hành qua tham số `memory`.
- **Tầng kiểm soát tất định (Deterministic Control)**: Sử dụng **LangGraph Subgraph** (đã xây dựng ở Phase 1) gồm 6 nodes bất biến (AST check, RBAC enforcer, Cost guard, HITL interrupt, DB executor, Audit logger).
  - Đóng gói đồ thị `CompiledStateGraph` của Phase 1 thành một **`CompiledSubAgent`** của `deepagents`.
  - Giúp Deep Agent gọi vào hàng rào kiểm soát như một subagent thông thường qua tool `task("control-pipeline", ...)`, nhưng bên trong chạy 100% bằng code logic chặt chẽ, không để LLM đoán mò.

```
+-------------------------------------------------------------------------------+
|                       DEEP AGENT SUPERVISOR (Master Brain)                    |
|                Khởi tạo qua create_deep_agent(...) từ deepagents              |
|                                                                               |
|  [Built-in Todo Middleware]                [Virtual Filesystem - In Memory]   |
|  TodoListMiddleware -> write_todos         StateBackend: schema_context.md    |
|                                                          draft_sql.sql        |
|  [On-Demand Domain Skills]                 [Agent Operating Memory]           |
|  skills: tpch-analytics, duckdb-sql        memory: ["AGENTS.md"]              |
|                                                                               |
|  [Built-in Delegation Tool: task()]                                           |
|       |                     |                     |                     |     |
+-------|---------------------|---------------------|---------------------|-----+
        |                     |                     |                     |
        v                     v                     v                     v
+----------------+   +----------------+   +-------------------+  +---------------+
| SubAgent Dict  |   | SubAgent Dict  |   | CompiledSubAgent  |  | SubAgent Dict |
|schema-retriever|   | sql-generator  |   | control-pipeline  |  |  synthesizer  |
| (Tra cứu DDL & |   | (Sinh câu lệnh |   | (LangGraph Phase1 |  | (Dựng Recharts|
|   phân loại)   |   |   SELECT SQL)  |   | AST, RBAC, DB...) |  |   & Insight)  |
+----------------+   +----------------+   +-------------------+  +---------------+
```

---

## 2. Bảng Phân Tích & Cấu Hình Tham Số Cho `create_deep_agent`

Theo tài liệu chính thức của LangChain ([LangChain DeepAgents Reference](https://reference.langchain.com/python/deepagents/graph/create_deep_agent)), hàm `create_deep_agent` tiếp nhận các tham số được tối ưu hóa như sau:

| Tham số | Kiểu dữ liệu | Giá trị thiết lập trong dự án | Vai trò kỹ thuật & Ý nghĩa |
| :--- | :--- | :--- | :--- |
| **`name`** | `str` | `"text2sql-deep-supervisor"` | Định danh của Master Supervisor Agent phục vụ cấu trúc log và LangSmith tracing. |
| **`model`** | `str \| BaseChatModel` | `settings.tier1_model` (GPT-4o / Claude 3.5 Sonnet) | Mô hình LLM Tier 1 chịu trách nhiệm suy luận logic cao cấp, lập kế hoạch và phân tích bài toán. |
| **`system_prompt`** | `str` | `SUPERVISOR_SYSTEM_PROMPT` | Chỉ dẫn vai trò, nguyên tắc làm rõ câu hỏi (Clarification), thứ tự gọi `task()`, và cơ chế retry $\le 3$ lần. |
| **`memory`** | `list[str]` | `["AGENTS.md"]` | Tự động đọc và nạp tệp quy ước kỹ thuật [`AGENTS.md`](file:///c:/text2sql-agent/AGENTS.md) vào prompt của agent tại thời điểm khởi tạo, bảo đảm agent luôn tuân thủ nguyên tắc an toàn (chỉ SELECT, audit log, v.v.). |
| **`context_schema`**| `type[ContextT]` | `UserContext` | Schema định nghĩa ngữ cảnh bất biến của phiên (chứa `user_id`, `role: Analyst \| Admin`, `session_id`, `max_cost_bytes`). Giúp kiểm soát quyền hạn RBAC không bị model làm sai lệch. |
| **`middleware`** | `Sequence[AgentMiddleware]` | `[TodoListMiddleware()]` | **Bổ sung theo yêu cầu**: Kích hoạt công cụ `write_todos` quản lý danh sách công việc có cấu trúc, tự động trả về `result["todos"]` cho UI theo dõi tiến độ. |
| **`skills`** | `list[str]` | `["skills/tpch-analytics", "skills/duckdb-sql"]` | **Bổ sung theo yêu cầu**: Nạp tri thức chuyên môn on-demand qua các file `SKILL.md` (công thức dbt metrics, quy tắc cú pháp DuckDB, mapping biểu đồ Recharts). |
| **`subagents`** | `Sequence[SubAgent \| CompiledSubAgent]` | Danh sách 4 Subagents: `schema-retriever`, `sql-generator`, `response-synthesizer`, `control-pipeline` | Cung cấp danh sách các agent con chuyên trách để Master Supervisor ủy quyền xử lý qua tool `task()`. |
| **`backend`** | `BackendProtocol` | `StateBackend()` | Mặc định sử dụng bộ nhớ in-memory trong StateGraph. Các file trung gian (`schema_context.md`, `draft_sql.sql`) được cô lập 100% theo từng phiên truy vấn, không lo Race Condition trên ổ đĩa. |
| **`checkpointer`** | `BaseCheckpointSaver` | `MemorySaver()` | Lưu trữ trạng thái phiên đa người dùng theo `thread_id = session_id`, hỗ trợ pause/resume an toàn. |
| **`interrupt_on`** | `dict[str, ...]` | `{"task:control-pipeline": ...}` *(tùy chọn)* | Hỗ trợ chốt chặn Human-in-the-loop (HITL) tạm dừng đồ thị chờ người dùng duyệt khi câu query có chi phí lớn. |

---

## 3. Danh Mục Các Tệp Cần Viết / Chỉnh Sửa Cho Component 4.3

| STT | Tệp tin | Trạng thái | Nhiệm vụ kỹ thuật |
| :--- | :--- | :--- | :--- |
| **1** | `requirements.txt` | **MODIFY** | Bổ sung dependency `deepagents>=0.7.13` vào danh sách thư viện Python. |
| **2** | `skills/tpch-analytics/SKILL.md` | **NEW** | Domain Skill: Cheatsheet công thức dbt metrics TPC-H (Net Revenue, Gross Margin), danh mục 8 bảng và mã phân khúc khách hàng. |
| **3** | `skills/duckdb-sql/SKILL.md` | **NEW** | Domain Skill: Cheatsheet quy tắc cú pháp DuckDB (Date literals, Interval, CTE, Window Functions, Group By). |
| **4** | `src/agents/prompts/supervisor_prompt.py` | **NEW** | System Prompt cho Deep Agent Supervisor: hướng dẫn lập kế hoạch `write_todos`, kiểm tra câu hỏi mơ hồ, thứ tự gọi các subagents qua tool `task()`, và cơ chế retry có chặn ngưỡng ($\le 3$ lần). |
| **5** | `src/agents/prompts/__init__.py` | **MODIFY** | Re-export `SUPERVISOR_SYSTEM_PROMPT`. |
| **6** | `src/agents/control_pipeline/builder.py` | **MODIFY** | Cung cấp hàm `get_control_pipeline_subagent() -> CompiledSubAgent` để đóng gói LangGraph Phase 1 thành `CompiledSubAgent` chuẩn của `deepagents`. |
| **7** | `src/agents/control_pipeline/__init__.py` | **MODIFY** | Re-export `get_control_pipeline_subagent` và instance `control_pipeline_subagent`. |
| **8** | `src/agents/supervisor.py` | **NEW** | **Tệp trung tâm**: khởi tạo qua `create_deep_agent(...)`, cấu hình `TodoListMiddleware`, `skills`, `memory`, `context_schema`, `StateBackend`, đăng ký 4 subagents, tích hợp `SessionTracer`, và cung cấp các runner `create_text2sql_supervisor()`, `run_supervisor()`, `arun_supervisor()`. |
| **9** | `src/agents/__init__.py` | **MODIFY** | Re-export các đối tượng Supervisor cho các module khác sử dụng trực tiếp. |
| **10** | `tests/agents/test_supervisor.py` | **NEW** | Bộ kiểm thử TDD toàn diện: kiểm tra cấu hình 4 subagents, `CompiledSubAgent`, khởi tạo `create_deep_agent`, `TodoListMiddleware`, `skills`, bộ nhớ phiên và delegation loop. |

---

## 4. Chi Tiết Thiết Kế Kỹ Thuật Từng Phần

### 4.1. Định Nghĩa 2 Domain Skills (`skills/`)
- **`skills/tpch-analytics/SKILL.md`**:
  - Định nghĩa công thức tính toán: `Net Revenue = l_extendedprice * (1 - l_discount)`.
  - Từ điển các giá trị phân khúc: `AUTOMOBILE`, `BUILDING`, `FURNITURE`, `HOUSEHOLD`, `MACHINERY`.
  - Ý nghĩa các cờ trạng thái đơn hàng (`o_orderstatus`): `F` (Fulfilled/Hoàn tất), `O` (Open/Đang mở), `P` (Partial/Một phần).
- **`skills/duckdb-sql/SKILL.md`**:
  - Cú pháp ép kiểu ngày tháng: `DATE '1995-01-01'`.
  - Cú pháp cộng trừ thời gian: `o_orderdate + INTERVAL '1' YEAR`.
  - Quy định bắt buộc có `LIMIT 1000` và chỉ dùng lệnh `SELECT`.

### 4.2. `src/agents/prompts/supervisor_prompt.py`
- Hướng dẫn Supervisor:
  1. Sử dụng công cụ `write_todos` để chia nhỏ quy trình thành 5 bước trước khi thực thi.
  2. Phân tích câu hỏi: Nếu mơ hồ (thiếu năm, thiếu phân khúc), Supervisor hỏi lại người dùng ngay, không gọi subagents.
  3. Khi câu hỏi rõ ràng: Gọi `task("schema-retriever", ...)` $\rightarrow$ `task("sql-generator", ...)` $\rightarrow$ `task("control-pipeline", ...)`.
  4. Nếu `control-pipeline` trả về lỗi và `retry_count < 3`: Gọi lại `task("sql-generator", ...)` kèm `actionable_feedback`.
  5. Nếu `control-pipeline` thành công: Gọi `task("response-synthesizer", ...)` để tạo cấu hình Recharts JSON và Business Insight.

### 4.3. Đóng Gói `CompiledSubAgent` (`src/agents/control_pipeline/builder.py`)
- Sử dụng class `CompiledSubAgent` từ `deepagents`:
  ```python
  from deepagents import CompiledSubAgent
  from src.agents.control_pipeline.builder import build_control_pipeline_graph

  def get_control_pipeline_subagent(graph=None) -> CompiledSubAgent:
      active_graph = graph or build_control_pipeline_graph()
      return CompiledSubAgent(
          name="control-pipeline",
          description=(
              "Hàng rào kiểm soát tất định (CompiledSubAgent) thực thi kiểm tra cú pháp AST (sqlglot), "
              "chính sách phân quyền RBAC, dự toán chi phí Cost guard, Human-in-the-loop (HITL) "
              "và thực thi truy vấn an toàn trên Data Warehouse."
          ),
          runnable=active_graph,
      )
  ```

### 4.4. Cấu Trúc Master Supervisor (`src/agents/supervisor.py`)
- Khởi tạo `create_deep_agent` với đầy đủ bộ tham số đã thống nhất:
  ```python
  from deepagents import create_deep_agent
  from deepagents.backends import StateBackend
  from langchain.agents.middleware import TodoListMiddleware
  from langgraph.checkpoint.memory import MemorySaver

  from src.agents.prompts import SUPERVISOR_SYSTEM_PROMPT
  from src.models.rbac import UserContext

  def create_text2sql_supervisor(
      model=None,
      checkpointer=None,
      subagents=None,
      system_prompt=None,
      skills=None,
      middleware=None,
      **kwargs,
  ):
      active_middleware = list(middleware or [TodoListMiddleware()])
      active_skills = skills or ["skills/tpch-analytics", "skills/duckdb-sql"]

      return create_deep_agent(
          name="text2sql-deep-supervisor",
          model=model or settings.tier1_model,
          system_prompt=system_prompt or SUPERVISOR_SYSTEM_PROMPT,
          memory=["AGENTS.md"],
          context_schema=UserContext,
          middleware=active_middleware,
          skills=active_skills,
          subagents=subagents or get_supervisor_subagents(),
          backend=StateBackend(),
          checkpointer=checkpointer or MemorySaver(),
          **kwargs,
      )
  ```
- Tích hợp `SessionTracer` để tự động ghi nhận các kết quả trung gian và lưu vào `outputs/{timestamp}_{session_id[:8]}/`.

### 4.5. Cơ Chế Kiểm Soát Vòng Lặp & Hạn Mức Thực Thi (Execution Limits & Guardrails)

Nhằm ngăn chặn vòng lặp ReAct vô tận và bảo vệ tài nguyên Data Warehouse/LLM:

#### 1. Cơ chế đang áp dụng (Active Guardrails):
- **Cấu hình tập trung trong `src/config.py`**:
  * `supervisor_tool_call_limit: int = 20` (Giới hạn tối đa 20 lượt gọi tool trong 1 lượt chạy).
  * `supervisor_tool_call_thread_limit: int = 100` (Giới hạn tối đa 100 lượt gọi tool trong toàn bộ thread/session).
  * `supervisor_model_call_limit: int = 20` (Giới hạn tối đa 20 lượt gọi LLM trong 1 lượt chạy).
  * `supervisor_model_call_thread_limit: int = 100` (Giới hạn tối đa 100 lượt gọi LLM trong toàn bộ thread/session).
- **Middleware kiểm soát**:
  * `ToolCallLimitMiddleware(run_limit=20, thread_limit=100, exit_behavior="continue")`: Khi vượt quá 20 lần gọi tool/turn hoặc 100 lần/thread, khóa các tool calls tiếp theo và cho phép model tiếp tục để tổng hợp câu trả lời từ dữ liệu sẵn có.
  * `ModelCallLimitMiddleware(run_limit=20, thread_limit=100, exit_behavior="end")`: Phanh khẩn cấp, tự động kết thúc phiên an toàn kèm thông báo AI giải thích nguyên do nếu số lần suy luận vượt quá 20/turn hoặc 100/thread.
  * `recursion_limit` trong LangGraph config (mặc định 20-25 steps).

#### 2. Ý tưởng nâng cao mở rộng trong tương lai (Future Enhancements):
- **Custom `SubagentBudgetMiddleware`**:
  * Can thiệp vào hook `wrap_tool_call` của LangChain Middleware stack để phân tách tham số `args["subagent_name"]` của công cụ `task()`.
  * Đặt hạn ngạch (quota) chi tiết cho từng Subagent riêng biệt:
    - `control-pipeline`: Tối đa 3 câu SQL/phiên.
    - `sql-generator`: Tối đa 4 lần soạn thảo/phiên (bao gồm cả self-correction).
    - `schema-retriever`: Tối đa 2 lần tra cứu/phiên.
    - `response-synthesizer`: Tối đa 2 lần trực quan hóa.
- **Stateful Query Counter trong `control-pipeline` CompiledSubAgent**:
  * Quản lý biến đếm số lượt query của phiên trực tiếp bên trong runnable tất định của `control-pipeline`.
  * Khi vượt ngưỡng, `control-pipeline` tự động từ chối gửi lệnh xuống warehouse và nhả feedback ép Supervisor dừng truy vấn để tổng hợp kết quả.

---

## 5. Kế Hoạch Triển Khai Từng Bước (Roadmap)

1. **Bước 1: Cấu hình dependencies**: Cập nhật `requirements.txt` với `deepagents>=0.7.13` (đã test cài đặt thành công).
2. **Bước 2: Xây dựng Skills**: Tạo 2 thư mục `skills/tpch-analytics/SKILL.md` và `skills/duckdb-sql/SKILL.md`.
3. **Bước 3: Viết System Prompt**: Tạo `src/agents/prompts/supervisor_prompt.py` và re-export.
4. **Bước 4: Đóng gói `CompiledSubAgent`**: Cập nhật `src/agents/control_pipeline/builder.py` và `__init__.py`.
5. **Bước 5 (TDD RED)**: Xây dựng bộ kiểm thử `tests/agents/test_supervisor.py`.
6. **Bước 6 (TDD GREEN)**: Triển khai hoàn chỉnh `src/agents/supervisor.py` với `create_deep_agent`.
7. **Bước 7 (REFACTOR & VERIFY)**: Chạy `ruff check`, `ruff format` và chạy 100% test suite.
