# Architecture v4.0 — Implementation Blueprint

> **Status**: Ready for review → Proceed to build  
> **Scope**: 4 phases, 16 components  
> **Strategy**: Option B — New LangGraph analytics subgraph mounted as CompiledSubAgent under existing DeepAgents Supervisor

---

## Agreed Decisions Summary

| Decision | Choice |
|----------|--------|
| Pre-flight Gatekeeper | Two-tier: Regex guardrails (<1ms) + Merged LLM Guardrails & Clarification (Structured Output) |
| Refusal Strategy | Deterministic Hardcoded Refusal prompt (zero LLM hallucination/jailbreak leak) |
| Multi-query | Sequential execution, no parallelism, no query fusion |
| Analysis loop | Bounded by `max_analysis_tasks` config (default: 3) |
| Retry vs Analysis budget | Two separate limits |
| DeepAgents integration | Option B — analytics subgraph as CompiledSubAgent |
| Router | 2 routes: CONVERSATION vs ANALYTICS |
| Presentation Strategy | Composable ResponsePackage: One-shot LLM Spec + Deterministic Data Hydration (No hardcoded combinations, zero latency explosion) |
| DLP / Output Guard | Deferred (column-level RBAC sufficient for TPC-H) |
| MCP | Deferred |
| JWT auth | Deferred (mock auth acceptable for demo) |
| Deployment | DuckDB for local dev, real warehouse (BigQuery/Supabase Postgres) for demo |

---

## Phase 1 — Foundation

> Kill the regex. Introduce typed artifacts. Fix broken HITL.

### Component 1.1: QueryArtifact Model

**File**: `src/models/artifacts.py` (NEW)

```python
class QueryArtifact(BaseModel):
    """Typed evidence artifact produced by a single query execution."""

    artifact_id: str  # Auto-generated UUID
    task_id: str  # Links back to AnalysisTask

    # Query
    sql: str
    dialect: Literal["duckdb", "bigquery"] = "duckdb"
    explanation: str  # What this query is trying to answer

    # Schema lineage
    tables_used: list[str]
    columns_used: list[str]

    # Execution result
    status: Literal[
        "SUCCESS",
        "BLOCKED_AST",
        "BLOCKED_RBAC",
        "BLOCKED_COST",
        "BLOCKED_HITL",
        "DB_ERROR",
        "TIMEOUT",
    ]
    data: list[dict[str, Any]] | None = None
    columns: list[str] | None = None
    row_count: int = 0

    # Cost & performance
    estimated_bytes: int = 0
    execution_time_ms: float = 0.0

    # Error info (if failed)
    error_type: str | None = None
    error_message: str | None = None
```

**Why**: This replaces the brittle regex extraction in `query.py`. Every successful query through the control pipeline produces a `QueryArtifact` instead of a Vietnamese-language ToolMessage.

### Component 1.2: Refactor Control Pipeline Output

**File**: `src/agents/control_pipeline/nodes.py` (MODIFY)

**What changes**:
- `execute_node` and `audit_node` now construct and return a `QueryArtifact` as part of the state
- The success/failure message nodes write the artifact to state instead of formatting Vietnamese text
- The artifact is stored in `ControlState.query_artifact: QueryArtifact | None`

**File**: `src/models/state.py` (MODIFY)

**What changes**:
- Add `query_artifact: QueryArtifact | None` to `ControlState`
- Add `query_artifact: QueryArtifact | None` to `ControlPipelineOutput`

### Component 1.3: Kill Regex Extraction in query.py

**File**: `src/api/routes/query.py` (MODIFY)

**What changes**:
- Remove all `re.search()` calls for SQL, data, and HITL detection (lines 94-157)
- Instead, read `QueryArtifact` from the supervisor result:

```python
# BEFORE (brittle regex)
sql_match = re.search(r"-\s*Câu lệnh đã chạy:\s*(SELECT[\s\S]+?)(?:\n-|\Z)", c_text)

# AFTER (typed artifact)
artifact = result.get("query_artifact")
if artifact:
    sql = artifact.sql
    data = artifact.data
    columns = artifact.columns
```

- The supervisor's return dict gains a `query_artifact` key

### Component 1.4: HITL Bug Fix

**File**: `src/api/routes/query.py` (MODIFY) — ✅ ALREADY DONE

**What was fixed**:
1. Resume key changed from `"approved"` → `"hitl_approved"` to match `hitl_gate_node` contract
2. The `Command` is now actually sent to the graph via `agent.ainvoke(resume_command, config)` instead of being discarded

---

## Phase 2 — Multi-Query Intelligence

> Introduce AnalysisPlan. Build the analytics LangGraph subgraph. Support 1-N queries per request.

### Component 2.1: AnalysisPlan & AnalysisTask Models

**File**: `src/models/artifacts.py` (EXTEND)

```python
class AnalysisTask(BaseModel):
    """A single analytical sub-question that needs evidence."""

    task_id: str
    description: str  # What needs to be answered
    status: Literal[
        "PLANNED",
        "RETRIEVING_CONTEXT",
        "GENERATING_QUERY",
        "VALIDATING",
        "EXECUTING",
        "COMPLETED",
        "FAILED",
    ] = "PLANNED"
    depends_on: list[str] = []  # task_ids (for documentation, not DAG execution)

    # Populated after execution
    query_artifact: QueryArtifact | None = None
    retry_count: int = 0


class AnalysisPlan(BaseModel):
    """The investigation plan for a user's analytical request."""

    plan_id: str
    goal: str  # What the user wants to know
    tasks: list[AnalysisTask]

    # Budgets
    max_tasks: int = 3  # Hard ceiling from config
    current_task_index: int = 0

    # Evidence collection
    evidence_summary: str | None = None  # Updated after each task completes
    needs_more_evidence: bool = False


class AnalyticsResult(BaseModel):
    """Complete result of an analytics workflow."""

    plan: AnalysisPlan
    artifacts: list[QueryArtifact]
    insight: str | None = None
    visualization: dict[str, Any] | None = None
    status: Literal["COMPLETED", "PARTIAL", "FAILED"]
```

### Component 2.2: Analytics Planner (LLM Node)

**File**: `src/agents/analytics/planner.py` (NEW)

**Responsibility**: Takes a user question + schema context and produces an `AnalysisPlan`.

**Implementation**:
- LLM call with structured output (Pydantic model)
- System prompt instructs: "Decompose this analytical question into 1-3 concrete sub-questions that each need one SQL query to answer"
- Uses Tier 2 model (cheaper, this is planning not SQL generation)
- Respects `max_analysis_tasks` from config

**Example**:
```
Input:  "Why did revenue decrease in Europe in 1996?"
Output: AnalysisPlan(
    goal="Investigate European revenue decline in 1996",
    tasks=[
        AnalysisTask(task_id="t1", description="Calculate Europe revenue 1995 vs 1996"),
        AnalysisTask(task_id="t2", description="Break down revenue change by country in Europe"),
        AnalysisTask(task_id="t3", description="Identify product categories driving the decline"),
    ]
)
```

### Component 2.3: Task Executor (Deterministic Node)

**File**: `src/agents/analytics/task_executor.py` (NEW)

**Responsibility**: Takes a single `AnalysisTask` and runs it through the existing pipeline:

```
AnalysisTask
    ↓
Schema Retriever (existing subagent)
    ↓
SQL Generator (existing subagent)  
    ↓
Control Pipeline (existing subgraph)
    ↓
QueryArtifact
```

**Key design**: This node reuses your existing subagents. It does NOT duplicate any governance logic. It just orchestrates the existing components for one task at a time.

**Self-correction**: Each task has its own `retry_count` with `MAX_RETRIES = 3` (existing behavior).

#### Component 2.3.1: Active Semantic & Metadata Tools Layer

> Chuyển đổi SQL Generator và Direct Chat từ thế bị động (Passive Context Injection) sang Active Tool-Calling Agent.

**File**: `src/agents/tools/metadata_tools.py` (NEW)

**Bộ 4 Strategic Tools**:
1. `search_tables_and_columns(query: str, top_k: int = 5)`: Tra cứu DDL và ngữ nghĩa bảng/cột từ từ khóa/câu hỏi.
2. `get_column_samples_and_values(table: str, column: str, query: str = "")`: Tra cứu danh sách unique values và giá trị thực tế trong DB (ví dụ: `c_mktsegment` $\to$ `['AUTOMOBILE', 'BUILDING', 'FURNITURE', 'HOUSEHOLD', 'MACHINERY']`).
3. `find_join_path(table_a: str, table_b: str)`: Tìm lộ trình JOIN ngắn nhất và điều kiện khóa ngoại chính xác giữa 2 bảng qua thuật toán BFS trên đồ thị 8 bảng TPC-H.
4. `search_business_definition(query: str)`: Tra cứu định nghĩa chỉ số nghiệp vụ dbt chuẩn (doanh thu thuần, doanh thu gộp, tỷ lệ hoàn hàng...) từ `TPCH_SEMANTIC_METRICS`.

**Phân bổ Tools**:
- **Consultation SubAgent (`consultation-agent` / CONVERSATION Route)**: Gắn 3 tools (1, 2, 4) để trả lời ngay các câu hỏi về data catalog, ý nghĩa cột, công thức mà không sinh SQL, không tốn tài nguyên warehouse. Master Supervisor là Pure Orchestrator chỉ gọi subagent này qua `task()`.
- **SQL Generator DeepAgent (`create_sql_generator_agent`)**: Đóng gói thành DeepAgent hoàn chỉnh chạy trên nền LangGraph runtime. Tự động nạp `skills/duckdb-sql` và `skills/tpch-analytics` qua `SkillsMiddleware`, gắn trực tiếp cả 4 Active Metadata Tools, và quản lý structured output qua `response_format=SQLGenerationResult`. Hỗ trợ cả 2 runner `generate_sql` (sync) và `agenerate_sql` (async).

**Cập nhật Prompt Templates**:
- `SQL_GENERATOR_SYSTEM_PROMPT` ([src/agents/prompts/sql_generator_prompt.py](file:///d:/Text2SQL-AI-Agent/src/agents/prompts/sql_generator_prompt.py)):
  + **Đặc tả chi tiết từng công cụ**: Liệt kê rõ các tham số (params), giải thích chức năng, và chỉ rõ chính xác **khi nào nên dùng (when to use)** cho từng tool trong 4 tools (`search_tables_and_columns`, `get_column_samples_and_values`, `find_join_path`, `search_business_definition`).
  + **Quy trình phối hợp công cụ (Tool Calling Workflow)**: Quy định tuần tự 4 bước: (1) Điều tra chỉ số $\to$ (2) Điều tra cấu trúc & JOIN $\to$ (3) Điều tra giá trị literal $\to$ (4) Sinh SQL tối ưu.
- `CONSULTATION_SYSTEM_PROMPT`: Chỉ dẫn cho `consultation-agent` trả lời trực tiếp câu chào hỏi, và gọi metadata tools khi người dùng hỏi giải thích schema, bảng, cột hoặc định nghĩa dbt metrics.
- `SUPERVISOR_SYSTEM_PROMPT`: Pure Orchestrator hướng dẫn điều phối: gọi `task("consultation-agent", ...)` cho route CONVERSATION/METADATA và `task("analytics-subagent", ...)` cho route ANALYTICS.

### Component 2.4: Evidence Analyzer (LLM Node)

**File**: `src/agents/analytics/evidence_analyzer.py` (NEW)

**Responsibility**: After all planned tasks complete, examines the collected `QueryArtifact` list and decides:
1. Is there enough evidence to answer the user's question? → Proceed to presentation
2. Is more evidence needed? → Generate 1 new `AnalysisTask` (if within budget)

**Bounded by**: `max_analysis_tasks` from config. If budget is exhausted, always proceeds to presentation with whatever evidence exists.

**Implementation**: LLM call with structured output returning either `{"enough": true, "summary": "..."}` or `{"enough": false, "next_task": AnalysisTask(...)}`.

### Component 2.5: Analytics LangGraph Subgraph

**File**: `src/agents/analytics/graph.py` (NEW)

**Responsibility**: Wires components 2.2-2.4 into a LangGraph graph:

```
                ┌─────────────────┐
                │  Planner Node   │
                └────────┬────────┘
                         ▼
                ┌─────────────────┐
            ┌──▶│ Task Executor   │──┐
            │   │ (sequential)    │  │
            │   └─────────────────┘  │
            │            ▼           │
            │   ┌─────────────────┐  │
            │   │Evidence Analyzer│  │
            │   └────────┬────────┘  │
            │            │           │
            │     ┌──────┴──────┐    │
            │     │             │    │
            │   MORE?         DONE   │
            │     │             │    │
            └─────┘    ┌────────┘    │
                       ▼             │
              ┌─────────────────┐    │
              │  Presentation   │    │
              │  (Insight+Viz)  │    │
              └─────────────────┘
```

**State**: `AnalyticsState(TypedDict)` containing:
- `question: str`
- `user_context: UserContext`
- `session_id: str`
- `plan: AnalysisPlan | None`
- `artifacts: list[QueryArtifact]`
- `insight: str | None`
- `visualization: dict | None`
- `status: str`

**Mounting**: This graph is compiled and mounted as a `CompiledSubAgent` in the Supervisor's subagent list, replacing the current direct sql-generator → control-pipeline → synthesizer flow for ANALYTICS-route requests.

### Component 2.6: Config Updates

**File**: `src/config.py` (MODIFY)

**New settings**:
```python
# Analysis budget (separate from retry budget)
max_analysis_tasks: int = 3  # Max tasks per user request
max_analysis_queries: int = 5  # Max total SQL queries (including retries)
max_analysis_runtime_seconds: int = 120  # Total wall-clock limit for analytics
```

---

## Phase 2.5 — Pre-Flight Security & Clarification Gatekeeper (Defense-in-Depth)

> Thiết lập "Vành đai an ninh & Làm rõ câu hỏi" ngay tại cổng đón tiếp (Front-door Gatekeeper) trước khi bất kỳ tài nguyên Supervisor hay Execution Subgraph nào được kích hoạt.
> Áp dụng cơ chế Phòng thủ 2 tầng (Two-Tier): Regex Guardrails (< 1ms, $0) + Merged LLM Guardrails & Clarification (1 Structured Output Call). Chặn đứng hành vi trái phép bằng Hardcoded Refusal tĩnh.

### Kiến Trúc Luồng Pre-Flight (End-to-End Gatekeeper Flow)

```
Natural Language Input
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  Tier 1: Deterministic Regex Guardrails (< 0.1ms, $0)  │
│  - SQL Injection & Mutating DDL/DML Patterns           │
│  - Prompt Injection, Jailbreak, System Prompt Leaks    │
│  - XSS, Shell Injection, Illegal Scripting             │
└───────────────────────────┬────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │ Match Malicious Pattern?       │
           YES                              NO
            │                               │
            ▼                               ▼
┌───────────────────────────────┐   ┌────────────────────────────────────────────────────────┐
│ 🛑 Hardcoded Refusal (Tier 1) │   │  Tier 2: Unified LLM Guardrails + Clarification Gate   │
│ Trả về câu từ chối cứng ngay, │   │  (Single Structured Output Call via Tier 2 Model)      │
│ không tốn token LLM           │   │  Model: InputPreflightEvaluation                       │
└───────────────────────────────┘   └───────────────────────────┬────────────────────────────┘
                                                                │
                                ┌───────────────────────────────┼──────────────────────────────┐
                                │ is_safe == False?             │ needs_clarification == True? │ is_safe & clear?
                                ▼                               ▼                              ▼
                ┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌────────────────────────┐
                │ 🛑 Hardcoded Refusal (Tier 2) │ │ ❓ Return Clarification       │ │ 🚀 Proceed to Master   │
                │ Chặn vi phạm ngữ nghĩa hoặc   │ │ Trả về câu hỏi làm rõ +       │ │ Supervisor (Pure       │
                │ yêu cầu ngoài miền (Out-of-   │ │ danh sách gợi ý A, B, C...    │ │ Orchestrator)          │
                │ Domain) bằng thông báo tĩnh   │ │ Ngắt sớm, không tốn resource  │ └────────────────────────┘
                └───────────────────────────────┘ └───────────────────────────────┘
```

### Component 2.5.1: Regex Guardrails Layer (Tier 1)

**File**: `src/agents/guardrails/regex_guard.py` (NEW)

**Mục tiêu**: Chặn đứng 100% các mẫu tấn công rõ ràng và độc hại thô thiển trong `< 0.1ms` với chi phí `0 token`, không cần chờ đợi LLM.

**3 Nhóm Quy Tắc Regex Chuyên Biệt**:
1. **DDL / DML Mutating SQL Injection**:
   - Chặn từ khóa biến đổi dữ liệu: `\b(drop|alter|truncate|delete|insert|update|grant|revoke|create|replace)\b`
   - Chặn batch statement & injection syntax: `;\s*--`, `;\s*drop`, `;\s*select`, `union\s+select`
   - Chặn thăm dò hệ thống: `information_schema`, `sys\.`, `xp_cmdshell`, `pg_sleep`, `sleep\(`
2. **Prompt Injection & System Prompt Exfiltration**:
   - Chặn ghi đè chỉ dẫn hệ thống: `(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+instructions`
   - Tiếng Việt tương đương: `(bỏ qua|quên|xóa)\s+(mọi\s+)?(hướng dẫn|chỉ dẫn|quy tắc|câu lệnh trước)`
   - Chặn trích xuất system prompt: `(what is your|reveal|show|print|display)\s+(system\s+)?(prompt|instructions)`
   - Tiếng Việt tương đương: `(cho tôi xem|hiển thị|in ra)\s+(system\s+)?(prompt|hướng dẫn hệ thống)`
   - Chặn Jailbreak / Bypass: `(dan\s+mode|jailbreak|developer\s+mode|evil\s+mode)`
3. **Script / Shell Injections**:
   - `<script[\s\S]*?>`, `javascript:`, `eval\(`, `exec\(`, `bash\s+-c`, `cmd\.exe`

**Đặc tả Class & Hàm**:
```python
class RegexGuardResult(BaseModel):
    is_safe: bool
    violation_type: (
        Literal["DDL_DML_INJECTION", "PROMPT_INJECTION", "SCRIPT_INJECTION"] | None
    ) = None
    matched_pattern: str | None = None
    refusal_message: str | None = None


def evaluate_regex_guardrails(question: str) -> RegexGuardResult:
    """Kiểm tra regex deterministic nhanh trong 0.1ms."""
```

---

### Component 2.5.2: Unified Preflight Evaluation Model (Tier 2 Model)

**File**: `src/models/artifacts.py` (EXTEND) hoặc `src/models/state.py` (EXTEND)

**Mục tiêu**: Định nghĩa Typed Contract duy nhất gộp cả Guardrails (An toàn & Miền nghiệp vụ) và Clarification (Độ rõ ràng).

```python
class SafetyCategory(str, Enum):
    SAFE = "SAFE"
    UNSAFE_PROMPT_INJECTION = (
        "UNSAFE_PROMPT_INJECTION"  # Cố tình jailbreak, prompt leak, override rules
    )
    UNSAFE_DATA_MUTATION = (
        "UNSAFE_DATA_MUTATION"  # Cố tình đòi xóa, sửa, phá hoại dữ liệu DB
    )
    UNSUPPORTED_OUT_OF_DOMAIN = "UNSUPPORTED_OUT_OF_DOMAIN"  # Lạc đề hoàn toàn (làm thơ, code game, dịch văn bản)


class InputPreflightEvaluation(BaseModel):
    """Structured Output từ Tier 2 LLM đánh giá an toàn và độ rõ ràng của câu hỏi."""

    # --- Guardrails Section ---
    is_safe: bool = Field(
        description="True nếu câu hỏi an toàn và nằm trong phạm vi nghiệp vụ phân tích dữ liệu; False nếu vi phạm bảo mật hoặc hoàn toàn lạc đề."
    )
    safety_category: SafetyCategory = Field(
        default=SafetyCategory.SAFE, description="Phân loại mức độ an toàn của câu hỏi."
    )
    safety_reason: str | None = Field(
        default=None,
        description="Giải thích ngắn gọn lý do kỹ thuật nếu phát hiện câu hỏi không an toàn hoặc ngoài miền.",
    )

    # --- Clarification Section ---
    needs_clarification: bool = Field(
        description="True nếu câu hỏi an toàn nhưng mơ hồ, thiếu chiều lọc quan trọng (thời gian, khu vực, đối tượng) để sinh SQL chính xác."
    )
    clarification_reason: str | None = Field(
        default=None,
        description="Lý do cần làm rõ (ví dụ: 'Chưa có mốc thời gian', 'Thiếu đối tượng phân tích cụ thể').",
    )
    clarification_question: str | None = Field(
        default=None,
        description="Câu hỏi tiếng Việt lịch sự, định hướng nghiệp vụ để hỏi lại người dùng.",
    )
    suggested_options: list[str] = Field(
        default_factory=list,
        description="Danh sách từ 2-4 tùy chọn gợi ý cụ thể A, B, C... dựa trên ngữ cảnh TPC-H.",
    )
```

---

### Component 2.5.3: Pre-flight Gatekeeper Engine & Hardcoded Refusal

**File**: `src/agents/preflight_gatekeeper.py` (NEW — nâng cấp và thay thế logic từ `src/agents/clarification.py`)

**Quy trình Thực Thi 3 Bước**:
1. **Bước 1 (Regex Check)**: Gọi `evaluate_regex_guardrails(question)`.
   - Nếu `not result.is_safe`: Trả về ngay quyết định `SECURITY_BLOCKED` kèm thông điệp từ chối cứng (Hardcoded Refusal).
2. **Bước 2 (LLM Evaluation)**: Nếu vượt qua Tier 1, gọi Tier 2 LLM (`settings.tier2_model`) với structured output `InputPreflightEvaluation`.
   - Sử dụng prompt template chuyên biệt `PREFLIGHT_GATEKEEPER_PROMPT` kết hợp hướng dẫn an toàn và tiêu chuẩn phân loại TPC-H.
3. **Bước 3 (Post-Check Routing & Hardcoded Refusal Mapping)**:
   - **Nếu `is_safe is False`**:
     Tuyệt đối KHÔNG để LLM tự sinh câu trả lời xin lỗi hoặc giải thích dài dòng (tránh bị bypass/leak prompt). Hệ thống ánh xạ trực tiếp sang **Hardcoded Refusal Messages**:
     * `UNSAFE_PROMPT_INJECTION` / `UNSAFE_DATA_MUTATION`:
       `"Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin và bảo mật dữ liệu của hệ thống."`
     * `UNSUPPORTED_OUT_OF_DOMAIN`:
       `"Hệ thống chỉ hỗ trợ giải đáp và phân tích dữ liệu kinh doanh & chuỗi cung ứng (TPC-H Benchmark). Vui lòng đặt câu hỏi liên quan đến doanh thu, đơn hàng, khách hàng, nhà cung cấp hoặc tồn kho."`
   - **Nếu `is_safe is True` VÀ `needs_clarification is True`**:
     Trả về quyết định `CLARIFICATION_REQUIRED` kèm `clarification_question` và `suggested_options`.
   - **Nếu `is_safe is True` VÀ `needs_clarification is False`**:
     Trả về quyết định `ALLOWED` để luồng đi tiếp vào Master Supervisor.

**Fail-Safe Policy (Cơ chế Phòng ngừa lỗi)**:
- Nếu LLM API gặp sự cố timeout hoặc network error: Kích hoạt cơ chế Fail-Open an toàn có kiểm soát (`is_safe=True`, `needs_clarification=False`) và ghi log cảnh báo mức WARNING để không làm nghẽn người dùng hợp lệ, vì tầng kiểm duyệt phía sau (AST Sanitizer & RBAC ở Control Pipeline) vẫn là lá chắn bảo vệ tất định cuối cùng.

---

### Component 2.5.4: Master Supervisor Entry Integration

**File**: `src/agents/supervisor.py` (MODIFY) & `src/api/routes/query.py` (VERIFY)

**Thay đổi**:
- Thay thế hoàn toàn hàm `check_clarification_needed` tại Stage 1 của `run_supervisor()` bằng:
  ```python
  gatekeeper_result = evaluate_input_preflight(question=question, llm=preflight_llm)
  ```
- **Xử lý `gatekeeper_result.decision`**:
  * `SECURITY_BLOCKED`: Trả về ngay payload với `status="SECURITY_BLOCKED"`, `is_safe=False`, `refusal_reason=...`, không khởi tạo Virtual State, không gọi Master Supervisor, ghi structured audit log.
  * `CLARIFICATION_REQUIRED`: Trả về ngay `status="CLARIFICATION_REQUIRED"`, `clarification_question=...`, `suggested_options=...`.
  * `ALLOWED`: Khởi tạo session state và chuyển cho DeepAgents Master Supervisor điều phối (Consultation vs Analytics).

**TDD Execution Steps**:
1. **Red**: Viết bộ test toàn diện `tests/agents/test_preflight_gatekeeper.py`:
   - Test Tier 1 Regex: DDL/DML attacks (`DROP TABLE`, `UPDATE lineitem`), Jailbreak (`ignore instructions`, `show system prompt`), Shell payload.
   - Test Tier 2 Guardrails: Semantic prompt injection, Out-of-domain requests (làm thơ, hỏi thời tiết).
   - Test Tier 2 Clarification: Câu hỏi mơ hồ ("doanh thu thế nào"), Câu hỏi rõ ràng ("top 5 khách hàng năm 1995").
   - Test Hardcoded Refusal: Đảm bảo không có chuỗi LLM tự do lọt ra ngoài khi bị block.
   - Test Fail-Safe fallback khi LLM gặp sự cố mạng.
2. **Green**: Cài đặt `regex_guard.py` và `preflight_gatekeeper.py`.
3. **Refactor**: Cập nhật `src/agents/supervisor.py` và chạy `pytest tests/agents/test_preflight_gatekeeper.py`.

---

---

## Phase 3 — Composable Presentation & Response Synthesizer

> Tối ưu hóa toàn diện khâu xuất xưởng dữ liệu: Thay thế việc chia cắt rườm rà thành kiến trúc tinh gọn **One-Shot Spec Selection + Deterministic Data Hydration**, cho phép Agent tự do kết hợp bất kỳ tổ hợp output nào (Text, KPI, Chart, Table, Callout) trong đúng 1 lượt gọi LLM duy nhất mà không gây bùng nổ latency.

### Component 3.1: Typed Artifact Primitives & ResponsePackage Schema

**File**: `src/models/artifacts.py` (EXTEND)

Định nghĩa bộ Primitives linh hoạt và mô hình hợp đồng One-Shot Spec theo chuẩn Pydantic V2 Discriminated Union:
- `KpiArtifact`: Thẻ chỉ số kèm delta và đơn vị tính (USD, %, chiếc,...).
- `ChartArtifact`: Cấu hình Recharts đầy đủ (Line, Bar, Area, Pie, Composed) kèm mảng data thật.
- `TableArtifact`: Bảng dữ liệu định dạng chuẩn, danh sách cột và tổng số dòng.
- `EvidenceArtifact`: Dẫn chứng số liệu chứng minh cho từng luận điểm.
- `CalloutArtifact`: Cảnh báo dữ liệu thiếu, vi phạm chính sách hoặc không có dữ liệu.
- `FileArtifact`: Liên kết tải tệp CSV/Excel xuất xưởng.
- `ArtifactItem`: Tagged / Discriminated Union theo trường `type`.
- `ArtifactSpec` & `SynthesisDecision`: Hợp đồng Structured Output cho LLM chỉ sinh cấu hình, không chép lại dữ liệu.
- `ResponsePackage`: Gói phản hồi hoàn chỉnh cho API và Frontend Next.js.

### Component 3.2: One-Shot Response Synthesizer & Data Hydrator

**File**: `src/agents/analytics/response_synthesizer.py` (NEW)

**Input**: User question + EvidenceStore (danh sách `QueryArtifact`) + AnalysisGoal  
**Output**: `ResponsePackage` (hoàn chỉnh, sẵn sàng cho API và Web UI)

```python
class ResponseSynthesizer:
    async def synthesize(
        self,
        question: str,
        evidence_store: EvidenceStore,
        analysis_goal: str | None = None,
        session_id: str = "default",
    ) -> ResponsePackage: ...
```

**Quy trình 2 nhịp (Two-Step Synthesis)**:
1. **Bước 1: LLM Presentation Spec Decision (Single Hop - ~1s, $0.001)**:
   - Sử dụng Tier 2 LLM (`settings.tier2_model`) với Structured Output `SynthesisDecision`.
   - LLM nhận câu hỏi gốc + tóm tắt kết quả (5 dòng dữ liệu mẫu và danh sách cột của từng task), sau đó tự do quyết định:
     * Cần những loại artifact nào (Text, KPI, Chart, Table, Callout)?
     * Số lượng bao nhiêu (có thể có nhiều KPI, nhiều Chart cùng lúc)?
     * Cấu hình trục X, trục Y, tiêu đề, cột hiển thị là gì?
   - **Zero Token Waste & Zero Hallucination**: LLM KHÔNG chép lại toàn bộ dữ liệu bảng vào JSON, chỉ sinh các cấu hình định danh (`ArtifactSpec`).
2. **Bước 2: Deterministic Data Hydration (Python Code thuần < 2ms, $0)**:
   - Code Python duyệt qua `selected_artifacts` và tự động lấy mảng dữ liệu thực thi từ `QueryArtifact.data` bơm (hydrate) vào:
     * `chart` $\to$ gắn vào `ChartArtifact.data`
     * `table` $\to$ gắn vào `TableArtifact.rows`
     * `kpi` $\to$ trích xuất giá trị dòng đầu tiên của cột chỉ định vào `KpiArtifact.value`
   - Đóng gói toàn bộ thành `ResponsePackage` chuẩn Pydantic V2.

**Fast-path & Fail-Safe Fallbacks**:
- **Fast-path**: Nếu `EvidenceStore` rỗng hoặc toàn bộ truy vấn thất bại: Trả về ngay `ResponsePackage` với `CalloutArtifact(variant="error" | "no_data")` mà không cần gọi LLM (zero token, latency < 1ms).
- **Fail-Safe**: Nếu LLM gặp sự cố API: Bắt exception và kích hoạt fallback tất định tạo Table từ artifact thành công đầu tiên.

**TDD Execution Steps**:
1. **Red**: Bổ sung `ArtifactItem`, `ArtifactSpec`, `SynthesisDecision`, `ResponsePackage` vào `src/models/artifacts.py`. Viết `tests/agents/test_response_synthesizer.py` kiểm thử:
   - Fast-path fallback khi không có dữ liệu
   - Đa dạng tổ hợp: Chỉ Text, Text + KPI, Text + Chart + Table
   - Cơ chế Data Hydration rót đúng 100% dữ liệu gốc không bị biến đổi
   - Fail-safe fallback khi LLM gặp lỗi mạng
2. **Green**: Hiện thực hóa `src/agents/analytics/response_synthesizer.py`.
3. **Refactor**: Chạy `ruff check` và `pytest tests/agents/test_response_synthesizer.py`.

---

### Component 3.3: Deprecate synthesizer.py

**File**: `src/agents/synthesizer.py` (DEPRECATE)

**What happens**: The existing synthesizer continues to work for backward compatibility during the transition. Once the analytics subgraph is fully wired, the synthesizer is no longer called for ANALYTICS-route requests. Keep it alive for any edge cases until fully migrated.

---

## Phase 4 — Pure Orchestrator & API Evolution

> Chuẩn hóa phân loại điều phối tại Master Supervisor và nâng cấp API response contract.

### Component 4.1: Intent Delegation via Pure Orchestrator

**Trách nhiệm**: Phân loại ý định người dùng (CONVERSATION / METADATA vs ANALYTICS) sau khi câu hỏi đã vượt qua Pre-flight Gatekeeper.

**Hiện trạng & Kiến trúc hoàn thiện**:
Master Supervisor đã được thiết lập là **Pure Orchestrator** với bộ kỹ năng điều phối chuyên sâu ([skills/analytics-orchestrator/SKILL.md](file:///d:/Text2SQL-AI-Agent/skills/analytics-orchestrator/SKILL.md)):
- **Input đã được Pre-Flight Gatekeeper kiểm tra an toàn và rõ ràng ở Stage 1**.
- Supervisor phân loại trực tiếp qua LLM Orchestrator bằng công cụ `task()`:
  * Nếu là chào hỏi hoặc tra cứu danh mục bảng, cột, dbt metrics: ủy quyền cho `consultation-agent` (trang bị 3 Strategic Metadata Tools).
  * Nếu là câu hỏi phân tích số liệu TPC-H chuyên sâu: ủy quyền cho `analytics-subagent` (CompiledSubAgent bọc Analytics LangGraph Subgraph).
- **Lợi ích**: Không cần dựng thêm một node LangGraph `router.py` rời rạc, tránh dư thừa 1 bước hop trung gian và giảm độ trễ thêm 1-2 giây.

### Component 4.2: API Response Contract Evolution

**File**: `src/models/api_schemas.py` (MODIFY)

**New `QueryResponse` structure** (tương thích ngược hoàn toàn, bổ sung các trường an ninh và phân tích v4):

```python
class QueryResponse(BaseModel):
    # Existing fields (giữ tương thích ngược)
    session_id: str
    status: Literal["SUCCESS", "CLARIFICATION_REQUIRED", "SECURITY_BLOCKED", "ERROR"]
    question: str
    final_answer: str | None = None
    sql: str | None = None  # Primary SQL (first artifact's SQL)
    data: list[dict] | None = None  # Primary data
    columns: list[str] | None = None
    recharts_config: dict | None = None

    # Pre-Flight Security & Clarification Fields (v4 - Phase 2.5)
    is_safe: bool = True
    safety_category: str | None = None
    refusal_reason: str | None = None
    is_ambiguous: bool = False
    clarification_question: str | None = None
    suggested_options: list[str] = []

    # Analytics & Multi-Query Fields (v4 - Phase 2 & 3)
    intent: Literal["CONVERSATION", "ANALYTICS"] | None = None
    tasks: list[dict] | None = None  # AnalysisTask summaries
    artifacts: list[dict] | None = None  # QueryArtifact summaries
    response_package: dict | None = (
        None  # ResponsePackage (Phase 3 Composable Artifacts)
    )
    output_artifacts: list[dict] | None = (
        None  # Danh sách ArtifactItem cho Frontend Component Registry
    )
    insight: dict | None = None  # InsightResult summary
    visualization: dict | None = None  # VisualizationResult (Primary chart nếu có)
    metadata: dict | None = None  # query_count, total_execution_time_ms, etc.

    # Runtime & Governance Fields
    requires_hitl: bool = False
    estimated_cost_bytes: int | None = None
    execution_time_ms: float = 0.0
    error: str | None = None
```

**Frontend impact**: Frontend có thể đọc ngay `is_safe == False` để hiển thị alert đỏ từ chối, `is_ambiguous == True` để hiển thị modal chọn phương án A, B, C, hoặc render báo cáo phân tích đa chiều linh hoạt (`output_artifacts` qua Component Registry: KPI, Chart, Table, Callout) mà không cần thay đổi cấu trúc URL API.

---

## New File Structure

```
src/agents/
├── guardrails/                   # NEW — Phase 2.5: Deterministic Input Guardrails
│   ├── __init__.py
│   └── regex_guard.py            # NEW — Fast regex detector (< 0.1ms, $0)
├── preflight_gatekeeper.py       # NEW — Phase 2.5: Two-tier gatekeeper (nâng cấp từ clarification.py)
├── analytics/                    # NEW — Phase 2 & 3: Analytics LangGraph subgraph
│   ├── __init__.py
│   ├── graph.py                  # LangGraph analytics subgraph builder
│   ├── planner.py                # AnalysisPlan generation (LLM)
│   ├── task_executor.py          # Single task execution orchestrator
│   ├── evidence_analyzer.py      # "Enough evidence?" decision (LLM)
│   └── response_synthesizer.py   # NEW — Phase 3: One-shot LLM Spec + Deterministic Data Hydrator (ResponsePackage)
├── tools/                        # Active Semantic & Metadata Tools
│   ├── __init__.py
│   └── metadata_tools.py         # 4 Strategic Tools (catalog, samples, join, metrics)
├── consultation.py               # Consultation SubAgent (CONVERSATION / METADATA)
├── supervisor.py                 # Pure Orchestrator (write_todos + task delegation)
├── synthesizer.py                # DEPRECATE — Replaced by analytics/*
├── schema_retriever.py           # KEEP — Reused by task_executor
├── sql_generator.py              # KEEP — Active tool-calling SQL Generator
├── clarification.py              # MIGRATED — Logic sáp nhập vào preflight_gatekeeper.py
├── self_correction.py            # KEEP — Reused by task_executor
└── control_pipeline/             # KEEP — Reused by task_executor
    ├── nodes.py                  # MODIFY — Add QueryArtifact output
    ├── builder.py
    ├── routers.py
    ├── hitl_evaluator.py
    └── diagnostic.py

src/models/
├── artifacts.py                  # NEW — QueryArtifact, AnalysisPlan, InsightResult, etc.
├── api_schemas.py                # MODIFY — Extended QueryResponse with Pre-flight & Analytics
├── state.py                      # MODIFY — InputPreflightEvaluation & ControlState artifacts
└── rbac.py                       # KEEP
```

---

## Deployment Strategy

### Local Development
- **DuckDB** with TPC-H data (`sf=0.1` or `sf=1`) — zero cost, millisecond queries
- This is the default and what tests run against

### Demo / Presentation
- **Google BigQuery Sandbox** (free tier, 1TB/month query)
  - Load TPC-H data via Parquet files from DuckDB export
  - `dryRun` cost estimation becomes meaningful (real bytes scanned)
  - Demonstrates the Cost Guard and HITL are working against real infrastructure
  - Query latency is realistic (seconds, not milliseconds)
- **Alternative**: Supabase PostgreSQL (free tier)
  - If BigQuery setup is too complex, Supabase gives you a real PostgreSQL instance
  - Less "enterprise warehouse" feel but still a real remote database

**Config switch**: `src/config.py` already supports `warehouse_type` (duckdb vs bigquery). The control pipeline already has adapter logic for both dialects.

---

## LLM / Deterministic Boundary

```
Deterministic Code (Zero Hallucination):   LLM Probabilistic Code:
  ├── Tier 1 Regex Guardrails (< 0.1ms)      ├── Tier 2 Preflight Gatekeeper (Safe/Clarify)
  ├── Hardcoded Refusal Enforcer             ├── Supervisor Pure Orchestrator (TodoList & Delegation)
  ├── AST Validation (sqlglot)               ├── Consultation Agent (Friendly Q&A + Catalog)
  ├── RBAC Policy Check                      ├── Analytics Planner (AnalysisPlan Decomposition)
  ├── Cost Guard (dry-run)                   ├── Task SQL Generator (Active Tool Calling)
  ├── HITL Gate (interrupt)                  ├── Evidence Analyzer (Information Sufficiency)
  ├── Warehouse Executor                     └── Insight Generator (Business Findings)
  ├── Audit Logger
  ├── Visualization Planner (Heuristics)
  ├── Response Composer
  ├── Task Orchestrator (loop control)
  └── Budget Enforcement
```

Security-critical decisions remain in deterministic code. No exceptions.

---

## Implementation Order

```
Week 1: Phase 1 — Foundation (✅ COMPLETED)
├── QueryArtifact model & Control pipeline refactor
├── Kill regex in query.py
└── HITL interrupt fix & integration tests

Week 2: Phase 2 — Multi-Query Intelligence & Active Tools (✅ COMPLETED)
├── 4 Strategic Metadata Tools (catalog, samples, join path, metrics)
├── Consultation SubAgent + Orchestrator Skill
├── Supervisor Refactor: Pure Orchestrator with write_todos + task()
└── 233 Unit/Integration Tests 100% Passed

Week 3 (Hiện tại): Phase 2.5 — Pre-Flight Security & Clarification Gatekeeper
├── Component 2.5.1: Regex Guardrails Layer (src/agents/guardrails/regex_guard.py)
├── Component 2.5.2: Unified InputPreflightEvaluation Model
├── Component 2.5.3: Pre-flight Gatekeeper Engine with Hardcoded Refusal Mapping
└── Component 2.5.4: Master Supervisor Pre-Flight Integration & Test Suite

Week 4: Phase 3 — Presentation Split
├── Component 3.1: Insight Generator (src/agents/analytics/insight_generator.py)
├── Component 3.2: Visualization Planner (src/agents/analytics/visualization_planner.py)
└── Component 3.3: Response Composer (src/agents/analytics/response_composer.py)

Week 5: Phase 4 — API Evolution & E2E Benchmark
├── Component 4.2: QueryResponse Model Evolution in api_schemas.py
├── API route /ask & /approve update with full Pre-Flight & Artifact support
└── Spider-like Benchmark Runner (evals/benchmark_runner.py)
```

This is the fastest, safest path to a production-grade v4 architecture. Each phase produces a verified, testable increment.
