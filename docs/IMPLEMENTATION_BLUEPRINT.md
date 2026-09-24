# Architecture v4.0 — Implementation Blueprint

> **Status**: Ready for review → Proceed to build  
> **Scope**: 4 phases, 16 components  
> **Strategy**: Option B — New LangGraph analytics subgraph mounted as CompiledSubAgent under existing DeepAgents Supervisor

---

## Agreed Decisions Summary

| Decision | Choice |
|----------|--------|
| Multi-query | Sequential execution, no parallelism, no query fusion |
| Analysis loop | Bounded by `max_analysis_tasks` config (default: 3) |
| Retry vs Analysis budget | Two separate limits |
| DeepAgents integration | Option B — analytics subgraph as CompiledSubAgent |
| Router | 2 routes: CONVERSATION vs ANALYTICS |
| Dashboard Planner | Deferred (single viz per response is sufficient) |
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
    
    artifact_id: str          # Auto-generated UUID
    task_id: str              # Links back to AnalysisTask
    
    # Query
    sql: str
    dialect: Literal["duckdb", "bigquery"] = "duckdb"
    explanation: str          # What this query is trying to answer
    
    # Schema lineage
    tables_used: list[str]
    columns_used: list[str]
    
    # Execution result
    status: Literal["SUCCESS", "BLOCKED_AST", "BLOCKED_RBAC", 
                     "BLOCKED_COST", "BLOCKED_HITL", "DB_ERROR", "TIMEOUT"]
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
    description: str          # What needs to be answered
    status: Literal["PLANNED", "RETRIEVING_CONTEXT", "GENERATING_QUERY",
                     "VALIDATING", "EXECUTING", "COMPLETED", "FAILED"] = "PLANNED"
    depends_on: list[str] = []  # task_ids (for documentation, not DAG execution)
    
    # Populated after execution
    query_artifact: QueryArtifact | None = None
    retry_count: int = 0


class AnalysisPlan(BaseModel):
    """The investigation plan for a user's analytical request."""
    
    plan_id: str
    goal: str                 # What the user wants to know
    tasks: list[AnalysisTask]
    
    # Budgets
    max_tasks: int = 3        # Hard ceiling from config
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
max_analysis_tasks: int = 3          # Max tasks per user request
max_analysis_queries: int = 5        # Max total SQL queries (including retries)
max_analysis_runtime_seconds: int = 120  # Total wall-clock limit for analytics
```

---

## Phase 3 — Presentation Split

> Split synthesizer.py into independent specialist components.

### Component 3.1: Insight Generator

**File**: `src/agents/analytics/insight_generator.py` (NEW)

**Input**: User question + list of `QueryArtifact` + evidence summary  
**Output**: Structured insight text

```python
class InsightResult(BaseModel):
    summary: str              # 2-3 sentence executive summary
    key_findings: list[str]   # Bullet-point findings with specific numbers
    comparisons: list[str]    # Any notable comparisons (if applicable)
    caveats: list[str]        # Data limitations or assumptions
```

**Implementation**: LLM call (Tier 2) with the artifacts' data as context. The prompt instructs: "Every numerical claim must come directly from the provided data. Do not infer or fabricate numbers."

### Component 3.2: Visualization Planner

**File**: `src/agents/analytics/visualization_planner.py` (NEW)

**Input**: List of `QueryArtifact`  
**Output**: Recharts-compatible visualization config

```python
class VisualizationResult(BaseModel):
    chart_type: Literal["bar", "line", "area", "pie", "table"]
    title: str
    x_key: str
    y_keys: list[str]
    data: list[dict[str, Any]]  # The actual data to render
    series_labels: dict[str, str] | None = None
```

**Implementation**: Can be partially deterministic (heuristic-based chart type selection) + LLM for title and axis labels. Consumes the "best" artifact (most rows, most relevant to the user's question).

### Component 3.3: Response Composer

**File**: `src/agents/analytics/response_composer.py` (NEW)

**Input**: `InsightResult` + `VisualizationResult` + list of `QueryArtifact`  
**Output**: Final `AnalyticsResult` ready for the API

**Responsibility**: Assembles all pieces into the final response. Pure deterministic code, no LLM call.

### Component 3.4: Deprecate synthesizer.py

**File**: `src/agents/synthesizer.py` (DEPRECATE)

**What happens**: The existing synthesizer continues to work for backward compatibility during the transition. Once the analytics subgraph is fully wired, the synthesizer is no longer called for ANALYTICS-route requests. Keep it alive for any edge cases until fully migrated.

---

## Phase 4 — Router + API Evolution

> Add intent routing. Update the API response contract.

### Component 4.1: Intent Router

**File**: `src/agents/router.py` (NEW)

**Responsibility**: Classifies user intent into one of two routes:

```python
class IntentClassification(BaseModel):
    intent: Literal["CONVERSATION", "ANALYTICS"]
    confidence: float
    reasoning: str
```

**Implementation options** (choose one):
- **Option A**: LLM-based (Tier 2, cheapest model) — more flexible, handles edge cases
- **Option B**: Keyword/pattern heuristic with LLM fallback — faster, cheaper

**Examples**:
```
"What is a primary key?"          → CONVERSATION
"Explain what l_discount means"   → CONVERSATION (schema knowledge, no query needed)
"Top 10 customers by revenue"     → ANALYTICS
"Why did sales drop in 1996?"     → ANALYTICS
```

**Integration**: The Supervisor's system prompt is updated to use the router before delegating. CONVERSATION requests get a direct LLM response. ANALYTICS requests go to the analytics subgraph.

### Component 4.2: API Response Contract Evolution

**File**: `src/models/api_schemas.py` (MODIFY)

**New `QueryResponse` structure** (backward-compatible, additive changes):

```python
class QueryResponse(BaseModel):
    # Existing fields (kept for backward compat)
    session_id: str
    status: str
    question: str
    final_answer: str | None
    sql: str | None              # Primary SQL (first artifact's SQL)
    data: list[dict] | None      # Primary data
    columns: list[str] | None
    recharts_config: dict | None
    
    # New fields (v4)
    intent: Literal["CONVERSATION", "ANALYTICS"] | None = None
    
    tasks: list[dict] | None = None           # AnalysisTask summaries
    artifacts: list[dict] | None = None       # QueryArtifact summaries
    
    insight: dict | None = None               # InsightResult
    visualization: dict | None = None         # VisualizationResult
    
    metadata: dict | None = None              # query_count, total_execution_time_ms, etc.
    
    # Existing fields kept
    is_ambiguous: bool = False
    clarification_question: str | None = None
    suggested_options: list[str] = []
    requires_hitl: bool = False
    estimated_cost_bytes: int | None = None
    execution_time_ms: float = 0.0
    error: str | None = None
```

**Frontend impact**: The frontend can progressively adopt new fields. Existing fields continue to work.

---

## New File Structure

```
src/agents/
├── analytics/                    # NEW — Analytics LangGraph subgraph
│   ├── __init__.py
│   ├── graph.py                  # LangGraph analytics subgraph builder
│   ├── planner.py                # AnalysisPlan generation (LLM)
│   ├── task_executor.py          # Single task execution orchestrator
│   ├── evidence_analyzer.py      # "Enough evidence?" decision (LLM)
│   ├── insight_generator.py      # Business insight generation (LLM)
│   ├── visualization_planner.py  # Recharts config generation
│   └── response_composer.py      # Final assembly (deterministic)
├── router.py                     # NEW — Intent classification
├── supervisor.py                 # MODIFY — Add router + analytics subagent
├── synthesizer.py                # DEPRECATE — Replaced by analytics/*
├── schema_retriever.py           # KEEP — Reused by task_executor
├── sql_generator.py              # KEEP — Reused by task_executor
├── clarification.py              # KEEP — Still used by Supervisor
├── self_correction.py            # KEEP — Reused by task_executor
└── control_pipeline/             # KEEP — Reused by task_executor
    ├── nodes.py                  # MODIFY — Add QueryArtifact output
    ├── builder.py
    ├── routers.py
    ├── hitl_evaluator.py
    └── diagnostic.py

src/models/
├── artifacts.py                  # NEW — QueryArtifact, AnalysisPlan, etc.
├── api_schemas.py                # MODIFY — Extended QueryResponse
├── state.py                      # MODIFY — Add QueryArtifact to ControlState
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
LLM (probabilistic):              Deterministic code:
  ├── Intent Router                 ├── AST Validation (sqlglot)
  ├── Analytics Planner             ├── RBAC Policy Check
  ├── Schema Retriever              ├── Cost Guard (dry-run)
  ├── SQL Generator                 ├── HITL Gate (interrupt)
  ├── Evidence Analyzer             ├── Warehouse Executor
  ├── Insight Generator             ├── Audit Logger
  └── Visualization Planner         ├── Response Composer
                                    ├── Task Orchestrator (loop control)
                                    └── Budget enforcement
```

Security-critical decisions remain in deterministic code. No exceptions.

---

## Implementation Order

```
Week 1: Phase 1
├── Day 1-2: Component 1.1 + 1.2 (QueryArtifact model + control pipeline refactor)
├── Day 3:   Component 1.3 (Kill regex in query.py)
└── Day 4:   Component 1.4 (HITL fix) ✅ DONE + Integration test

Week 2: Phase 2
├── Day 1:   Component 2.1 (AnalysisPlan models)
├── Day 2:   Component 2.2 (Planner node)
├── Day 3:   Component 2.3 (Task Executor — wires existing components)
├── Day 4:   Component 2.4 + 2.5 (Evidence Analyzer + subgraph assembly)
└── Day 5:   Component 2.6 (Config) + Integration test

Week 3: Phase 3 + 4
├── Day 1-2: Components 3.1 + 3.2 (Insight + Viz split)
├── Day 3:   Component 3.3 (Response Composer)
├── Day 4:   Component 4.1 (Router)
└── Day 5:   Component 4.2 (API evolution) + End-to-end test
```

This is the fastest path to a working v4 architecture. Each phase produces a testable increment.
