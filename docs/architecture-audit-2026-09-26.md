# Architecture Audit — Text2SQL AI Agent (v4 implementation)

> **Auditor**: Codex (static review)
> **Date**: 2026-09-26
> **Scope**: the *implemented* system on disk — `src/agents/**`, `src/api/**`, `src/models/**`, `src/utils/**`, `src/services/**`, `src/frontend/**`, `evals/**`, `tests/**`, `docs/**`, packaging/CI.
> **Repo state at audit time**: `HEAD = 3ed0ea7` (2026-09-25), working tree dirty — **the entire v4.0 Layer-2/3 work (`analytics/`, `guardrails/`, `preflight_gatekeeper.py`, `api/routes/query.py`, `supervisor.py`, prompts, tests) is uncommitted.** Only docs/pyproject/ruff were committed alongside the older v3 code.
> **Verdict in one line**: the *governance layer* (AST → RBAC → Cost → Execute → Audit) is well built and genuinely production-shaped; the *v4 analysis layer* mounted on top of it is **not currently runnable end-to-end** because of one hard `TypeError`, and two of its headline safety guarantees (HITL approval, Zero-Hallucination integrity guard) are **dead code in the default route**.

---

## 0. Method, and what I could not verify

**Reviewed**: ~60 source files + 15 docs, read in full or in the relevant sections. Every finding below cites the exact file and line and names the call chain, so it can be reproduced with one command.

**Could not execute.** I intended to run the suite and a signature probe, but this machine has **no working Python runtime**:

| Attempt | Result |
|---|---|
| `D:\Text2SQL-AI-Agent\.venv\Scripts\python.exe` | `Unable to create process using "C:\Users\kinng\AppData\Local\Microsoft\WindowsApps\...python.exe"` — the venv's base interpreter is the **Windows Store alias stub**, which is not a real interpreter. |
| `.venv\pyvenv.cfg` | `home = C:\Users\kinng\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0` (stub) |
| `py -0p` → `py script.py` | `Unable to create process ... Access is denied` (Store app execution alias blocked) |
| `python` / `python3` / `pip` | All resolve to the same non-functional WindowsApps stub |
| `uv`-managed interpreters | `%LOCALAPPDATA%\uv\python` does not exist |

**Consequence**: every defect below is reported from *code reading*, not from a red test. I have marked the two findings whose runtime behaviour depends on a library-version detail (P0-2) as such. **Recommendation: fix the venv (`py -3.11 -m venv .venv` from a real Python install, or `uv venv`), then re-run the reproduction checklist in Appendix B.**

**Verified facts about repo hygiene** (via `git -c safe.directory=...`):
- `.env` is **not** tracked by git (`git ls-files .env` → no match) and `.gitignore` lists `.env`. Good — real keys currently in that file (Gemini, LangSmith, DeepSeek) are **not** in history.
- `git status --short` shows ~25+ modified files uncommitted; the v4 code is at risk of being lost.
- Note: local `git` needs `git config --global --add safe.directory D:/Text2SQL-AI-Agent` because the repo is owned by `kinng` while the sandbox user is `CodexSandboxOffline`.

---

## 1. Verdict at a glance

| Layer | Assessment | Notes |
|---|---|---|
| SQL safety kernel (`ast_sanitizer`, RBAC, cost guard, executor) | **Strong** | Single-statement enforcement, whole-AST forbidden-node scan, forced `LIMIT`, read-only root check, budget gate, fail-safe audit. Best part of the codebase. |
| Control pipeline graph (`control_pipeline/`) | **Good, with 2 hard edges** | Clean node/router split; but the interrupt node lives in a graph compiled without a checkpointer, and its error branch loses lineage metadata. |
| DeepAgents supervisor (v4 "Pure Orchestrator") | **Structurally right, broken at the seams** | Correct intent-routing design, correct middleware stack; but it re-compiles the whole agent per request and its two guard methods can never fire in the v4 path. |
| Analytics subgraph (v4 Layer 2/3) | **Cannot run** | `run_control_pipeline` is called with a signature that does not exist → `TypeError` on the first attempt of every task. |
| HITL approval (end-to-end) | **Non-functional** | Pause is simulated in the outer wrapper; the resume targets a different graph than the one that "paused". |
| API contract & frontend | **Drifted** | Backend returns rich typed `ResponsePackage`; `types/api.ts` does not model it, and the frontend still parses chart JSON out of Markdown with regex — the exact anti-pattern v4 was written to kill. |
| Config/budgets | **Partially dead** | `max_analysis_queries` and `max_analysis_runtime_seconds` are declared and never read. |
| Tests | **Broad but blind at the seams** | ~180 tests, good per-unit depth; they `patch()` precisely the boundary where the P0 lives. |
| Packaging/CI | **Drifted** | `pyproject.toml` declares only `duckdb` and a `uv_build` backend while `requirements.txt` is the real source of truth; Docker never copies `requirements.txt` into runtime (fine) but also never copies `skills/`, which the supervisor loads at runtime. |

---

## 2. P0 — Blocking defects (fix before any demo)

### P0-1 — `run_control_pipeline()` is called with a signature that does not exist → every analytics task dies with `TypeError`

**The mismatch:**

```python
# src/agents/control_pipeline/builder.py:86
def run_control_pipeline(
    graph: CompiledStateGraph,
    input_data: ControlPipelineInput,
    thread_id: str | None = None,
) -> ControlPipelineOutput:
```

```python
# src/agents/analytics/task_executor.py:111
pipeline_output: ControlPipelineOutput = run_control_pipeline(
    sql=sql_result.sql,
    user_context=user_context,
    session_id=user_context.session_id,
)
```

`run_control_pipeline` is defined **once** (verified: `rg "def run_control_pipeline"` → only `builder.py:86`) and re-exported unchanged by `src/agents/control_pipeline/__init__.py`. The keyword arguments `sql`, `user_context`, `session_id` are not parameters of it, and neither `graph` nor `input_data` is supplied. The result is:

```
TypeError: run_control_pipeline() got an unexpected keyword argument 'sql'
```

**Impact**: this is the single execution path used by the v4 analytics subgraph. `executor_node` (`src/agents/analytics/nodes.py`) → `aexecute_analysis_task` → line 111. The exception is **not** caught inside the task loop (see P2-5), so it propagates out of the node, through the subgraph, through the DeepAgent `task()` tool, and lands in the supervisor's blanket `except Exception` → the user gets `status="ERROR"` with a raw Python message. **The v4 architecture cannot produce a single successful answer today.**

**Correct call** (matches `self_correction.py:93`, which does it right):

```python
from src.agents.control_pipeline import build_control_pipeline_graph

graph = build_control_pipeline_graph()
pipeline_output = run_control_pipeline(
    graph,
    {
        "sql": sql_result.sql,
        "user_context": user_context,
        "session_id": user_context.session_id,
    },
)
```

Better: give `run_control_pipeline` a default graph (`graph=None` + lazy build + module-level cache) so both call styles work, and add a type-checked wrapper.

**Why CI is green anyway**: `tests/agents/test_task_executor.py` patches `src.agents.analytics.task_executor.run_control_pipeline` in **every** test (lines 74, 151, 188, 240, 324). The mock accepts any kwargs. The one integration point that would have caught this is the one that is always mocked.

---

### P0-2 — HITL approval cannot work end-to-end

There are three independent breaks in the approval chain.

**(a) The pause is simulated, not a real graph interrupt.** `run_supervisor` / `arun_supervisor` call `check_hitl_pending(messages)` (`supervisor.py:361`) which **regex-scans message text** for `"TẠM DỪNG CHỜ PHÊ DUYỆT"`. If found, the supervisor returns a plain dict with `status="PENDING_APPROVAL"` (`supervisor.py:600-618`). The LangGraph run has already completed at that point — nothing is suspended.

**(b) The real `interrupt()` happens in a graph that has no checkpointer.** `hitl_gate_node` calls `interrupt(interrupt_payload)` (`src/agents/control_pipeline/nodes.py:136`). That node belongs to the graph built by `build_control_pipeline_graph()`, and in the v4 path it is built with **no checkpointer**:

- `create_control_pipeline_runnable()` → `build_control_pipeline_graph()` (no args) → `checkpointer=None`
- `get_analytics_subagent(graph=None)` → `build_analytics_graph()` (no args) → `checkpointer=None`
- `create_text2sql_supervisor` only attaches the MemorySaver to the **outer** supervisor graph (`supervisor.py:271`).

`interrupt()` requires the graph that contains it to be compiled with a checkpointer; resuming is done by re-invoking that same compiled graph with `Command(resume=...)`. Neither condition holds here. *(Runtime message depends on the installed `langgraph` version — which I could not check because `uv.lock` contains no resolved `langgraph`/`deepagents` entries and the venv is unusable. Either it raises at the `interrupt()` call, or `run_control_pipeline`'s `final_state.get("__interrupt__")` branch is never reached.)*

**(c) The resume targets the wrong graph/thread.** `POST /api/v1/query/approve` (`src/api/routes/query.py:299-340`) does:

```python
checkpointer = get_shared_checkpointer()
config = {"configurable": {"thread_id": request.session_id}}
checkpoint_tuple = checkpointer.get_tuple(config)
...
agent = create_text2sql_supervisor(checkpointer=checkpointer)
output_state = await agent.ainvoke(
    Command(resume={"hitl_approved": ...}), config=config
)
```

This looks up a checkpoint on the **supervisor** thread and resumes the **supervisor** graph. But the supervisor graph was never interrupted (see (a)) — the interrupt, if any, belongs to a nested control-pipeline graph that is (i) checkpointer-less, (ii) created fresh inside a subagent runnable, and (iii) not keyed by `session_id` at all. Even in the lucky case where a supervisor checkpoint exists for the thread, `Command(resume=...)` resumes a *new* supervisor turn rather than the pending query.

**Net effect**: a risky query either errors out or the approval endpoint returns "Đã tiếp nhận phê duyệt thành công" without any query ever being executed. Both paths are silent to the user.

**Suggested direction** (pick one, don't mix):
1. **Real interrupts**: compile the control-pipeline subgraph with a checkpointer; mount it as a real subgraph (not a `RunnableLambda` that swallows the run); propagate the interrupt up to the API as a proper `__interrupt__` payload; resume the *same* graph with `Command(resume=...)`.
2. **Explicit approval token**: keep the pipeline non-interrupting, but have `cost_guard_node` emit a signed/persisted "pending approval" record (`{session_id, sql_hash, estimated_bytes, expires_at}`), have `execute_node` refuse to run without a matching approved token, and have `/approve` flip that record. This is simpler, stateless-friendly, and easy to test.

Either way, `tests/` needs a genuine round-trip test (see §7).

---

### P0-3 — The Zero-Hallucination and HITL integrity guards are dead code in the v4 route

`supervisor.py` contains two "chốt chặn" (guard) methods:

```python
# supervisor.py:333
def verify_pipeline_execution_integrity(messages):   # looks for "Truy vấn SQL thực thi THÀNH CÔNG" / "THẤT BẠI"
# supervisor.py:361
def check_hitl_pending(messages):                    # looks for "TẠM DỪNG CHỜ PHÊ DUYỆT" / "BLOCKED_HITL"
```

Both **regex-scan the supervisor's own `messages` list**. Those exact strings are produced by `create_control_pipeline_runnable` (`builder.py:243`, `builder.py:250`), which only runs when the `control-pipeline` **subagent** is registered. The v4 default registers only two subagents:

```python
# supervisor.py:129-132
subagents = [
    get_consultation_subagent(model=active_tier2),
    get_analytics_subagent(graph=analytics_graph),
]
if include_legacy_subagents:   # <-- False by default
    ... schema-retriever, sql-generator, control-pipeline, response-synthesizer
```

In the v4 flow the control pipeline is invoked **inside** the analytics subgraph, and the only thing that crosses the context-quarantine boundary back to the supervisor is the subagent's summary string — which the analytics runnable sets to `response_package.direct_answer` (`analytics/graph.py:145-149`). The literal strings `"Truy vấn SQL thực thi THÀNH CÔNG"`, `"Truy vấn SQL THẤT BẠI"` and `"TẠM DỪNG CHỜ PHÊ DUYỆT"` therefore **never appear in `messages`**, so:

- `verify_pipeline_execution_integrity()` always returns `(False, None)` → the deterministic "we could not execute your query" fallback never triggers;
- `check_hitl_pending()` always returns `(False, ...)` → the entire PENDING_APPROVAL branch never triggers either.

Note the irony: v4's stated goal was *"triệt tiêu hoàn toàn regex scraping"*, yet the two most safety-critical decisions in the supervisor are still Vietnamese-prose regex matches over LLM-authored text — and they no longer even match.

**Fix**: make integrity a **typed signal**, not prose. The analytics runnable already returns `status`, `artifacts`, `execution_result`; have the supervisor read `output_state["status"]` / the artifact list (`any(a.status == "SUCCESS")`) instead of scanning strings. Same for HITL: return a structured `hitl: {required, reason, sql, estimated_bytes}` object.

---

### P0-4 — A completely failed analysis is reported to the client as `COMPLETED`

In `arun_supervisor`, the success return is hard-coded:

```python
# supervisor.py:~700
active_tracer.log_summary(status="COMPLETED", question=question)
return {
    "status": "COMPLETED",
    ...
    "response_package": output_state.get("response_package"),
```

and the analytics runnable *does* propagate an inner status (`analytics/graph.py:194`), but the supervisor **never reads `output_state["status"]`**. `presentation_node` sets `"status": "FAILED"` when no artifact succeeded (`analytics/nodes.py`), and `ResponseSynthesizer.synthesize` produces a polite Vietnamese failure `direct_answer` — all of which is then wrapped and returned as `status="COMPLETED"`.

Downstream, `query.py` reads `result.get("status")` → `QueryResponse.status = "COMPLETED"`, and `types/api.ts` has no `"EXECUTION_FAILED"` mapping in the client state machine (it *is* in `QueryStatus`, but the backend never emits it in the v4 path because of this bug).

**Fix**: derive the outer status from the inner one (`COMPLETED` / `PARTIAL` / `FAILED` / `EXECUTION_FAILED`) instead of hard-coding it.

---

### P0-5 — `UserRole.BUSINESS_USER` does not exist → 500 on a documented role

```python
# src/api/dependencies.py:71
elif normalized_role in ["business_user", "business"]:
    role = UserRole.BUSINESS_USER      # AttributeError
```

`UserRole` (`src/models/rbac.py:7-11`) defines **only** `ANALYST` and `ADMIN`. `UserRole.BUSINESS_USER` raises `AttributeError: BUSINESS_USER` inside a FastAPI dependency, which the global handler (`src/api/main.py:90`) turns into a **500**, not a 422/403. Meanwhile `AskQueryRequest.role` advertises the role in its description (`api_schemas.py:44`).

`rg -n "BUSINESS_USER"` finds exactly two hits: this line and that description string.

**Fix**: either add `BUSINESS_USER` to the enum with its own allowed-tables/denied-columns matrix, or remove the branch and the description. Adding the role is the better choice if the frontend `RoleSwitcher` exposes it — check `src/frontend/components/layout/RoleSwitcher.tsx` (it currently types only `"Analyst" | "Admin"`, so today the simplest correct fix is deletion).

---

## 3. P1 — Correctness, contract and reliability issues

### P1-1 — Data lineage is silently dropped from every v4 artifact

`QueryArtifact` has `tables_used`, `columns_used`, `row_count` (`src/models/artifacts.py:36-79`). `task_executor.py:118-131` tries to populate them from the pipeline output:

```python
tables_used = (pipeline_output.get("tables_used", []),)
columns_used = (pipeline_output.get("columns_used", []),)
row_count = (pipeline_output.get("row_count", 0),)
```

but `ControlPipelineOutput` (`src/models/state.py:193-216`) has **none of those keys** — they live on `ControlState` and are never copied into the output by `execute_node` (`nodes.py:~205-232`). So **every v4 `QueryArtifact` reports empty lineage**, and `ResponsePackage.executed_queries` / the audit trail lose the "which tables did this touch" signal that RBAC and cost review depend on.

**Fix**: add `tables_used`, `columns_used`, `row_count` to `ControlPipelineOutput` and set them in `execute_node` and `err_node`.

### P1-2 — Synchronous LLM and DB calls inside `async` nodes block the whole server

`aexecute_analysis_task` is `async`, but the three expensive calls inside its loop are **synchronous**:

```python
# src/agents/analytics/task_executor.py
schema_res = retrieve_schema_context(task.description)  # sync, ~line 84
sql_result = generate_sql(...)  # sync → agent.invoke(), 1+ LLM round trips
pipeline_output = run_control_pipeline(
    ...
)  # sync → graph.invoke() → DuckDB EXPLAIN + query
```

`generate_sql` ends in `active_agent.invoke(...)` (`sql_generator.py:289`) — a blocking network call taking seconds per attempt, up to 4 attempts per task, up to 3 tasks. Because `/api/v1/query/ask` is an `async def` handler awaited by the same event loop, **one user's analysis freezes every other request** for the duration. With several tasks this is a multi-second total stall per request, and the "async" `arun_supervisor` gives a false sense of concurrency.

**Fix**: use the async variants that already exist (`agenerate_sql` at `sql_generator.py:296`; `graph.ainvoke` for the pipeline) or wrap the blocking calls in `anyio.to_thread.run_sync` / `asyncio.to_thread`. Note `analytics/graph.py:198-206` already does the thread-pool dance for the sync entry point, so the intent is there — it is just missing on the inner calls.

### P1-3 — The whole agent stack is rebuilt on every request

```python
# src/agents/supervisor.py:564 and :836
active_agent = agent or create_text2sql_supervisor(checkpointer=active_checkpointer)
```

`arun_supervisor` is called per HTTP request with `agent=None` (`api/routes/query.py:73`), so each request re-runs `create_deep_agent(...)` — which re-reads the three skill directories, re-reads `AGENTS.md` as operating memory, re-instantiates middleware, and re-compiles the supervisor graph plus the analytics and control-pipeline subgraphs. Nothing is cached.

**Fix**: cache the compiled supervisor per `(model, checkpointer)` with `functools.lru_cache` / a module-level singleton (the checkpointer is already a singleton, so a single cached agent is usually correct), and expose a `reset` for tests.

### P1-4 — A single global `MemorySaver` is the only session store

```python
# supervisor.py:48
_shared_supervisor_checkpointer: MemorySaver = MemorySaver()
```

Consequences:
- **Unbounded growth**: no eviction. Every conversation ever handled stays in process memory for the life of the process.
- **No durability**: a restart wipes all sessions; the multi-turn context feature silently degrades.
- **Weak isolation**: `thread_id` defaults to the client-supplied `session_id`. Two clients that send the same value share one conversation history — the checkpointer is a raw dict keyed by that string.
- **Multi-worker hazard**: with `uvicorn --workers N` (or the compose setup scaled out) each worker holds a *different* history, so multi-turn context breaks non-deterministically.

**Fix**: move to a durable checkpointer (`PostgresSaver`/SQLite) and derive `thread_id` server-side from an authenticated identity rather than a client-supplied string.

### P1-5 — Declared budgets are never enforced; retry constant diverges from config

```python
# src/config.py:228
max_analysis_queries: int = Field(default=5, ...)          # never read anywhere
# src/config.py:233
max_analysis_runtime_seconds: int = Field(default=120, ...) # never read anywhere
```

Verified by `rg`: only `max_analysis_tasks` is consumed (`planner.py:62`). So the "Dual-Budget Guardrails" table in `docs/agent-architecture-v4.md §6` is partly aspirational: the per-session **query budget** and **wall-clock budget** do not exist in code.

Separately, `MAX_TASK_RETRIES = 3` is hard-coded (`task_executor.py:23`) while `settings.max_retries` exists (`config.py:135`) and is only used by the legacy `self_correction.py`. `AGENTS.md` says "MAX_RETRIES = 3"; there are now **two** independent retry knobs, one of which ignores the environment. `note.txt` explicitly flags this class of problem ("phải cấu hình động ... không hardcode cố định").

**Fix**: read both from settings, enforce the query count in `executor_node`, and enforce wall-clock with a deadline checked at the top of each loop iteration (fail gracefully into whatever artifacts already exist).

### P1-6 — The typed v4 output never reaches the UI; the frontend still regex-parses Markdown

The v4 contract was written to eliminate regex scraping. It has not reached the client:

- `src/frontend/types/api.ts:43-72` models `QueryResponse` **without** `response_package`, `artifacts`, `tasks`, `intent`, `visualization`, `is_safe`, `safety_category`, `refusal_reason`, `metadata`, `artifact_bundle` — all of which the backend can now return (`api_schemas.py:95-160`).
- `QueryStatus` omits `"SUCCESS"` and `"SECURITY_BLOCKED"`, which `QueryResponse.status` can emit.
- `rg "response_package|output_artifacts|safety_category|is_safe" src/frontend` → **zero hits**. The v4 artifacts are never rendered.
- `src/frontend/utils/markdownChartParser.ts` (300+ lines) + `ChatMessageItem.tsx:43` still extract chart config by *parsing JSON out of Markdown* — the very anti-pattern `docs/architecture-v4.md §1.1.3` calls out as the reason for the rewrite.
- `src/api/routes/query.py:119-137` still carries a regex fallback that re-parses ```` ```json ```` blocks out of `final_answer` to recover a `recharts_config`. So the removal is incomplete on **both** sides.

**Fix**: either finish the migration (map `ResponsePackage.artifacts` → the existing `DataTable`/`DynamicChart`/`InsightCard` components, extend `types/api.ts`, delete `markdownChartParser.ts` and the `query.py` regex fallback), or explicitly declare the typed output an internal/benchmark-only contract. Right now it is a half-migration, which is the worst of the three options.

### P1-7 — Two clarification engines and a still-wired legacy tier

- `src/agents/clarification.py` (152 lines: `check_clarification_needed`, `DEFAULT_CLARIFICATION_OPTIONS_POOL`, `get_random_suggested_options`) and `src/agents/preflight_gatekeeper.py` (which **also** defines `DEFAULT_CLARIFICATION_OPTIONS_POOL` and `get_random_suggested_options`, plus its own backward-compat `check_clarification_needed`) both exist. `src/agents/__init__.py:4-6` exports the **deprecated** one; `supervisor.py:70-73` imports the **new** one. Two option pools, two prompts (`CLARIFICATION_PROMPT` vs `PREFLIGHT_GATEKEEPER_PROMPT`), two behaviours.
- The supervisor even contains a runtime branch to support both (`hasattr(check_clarification_needed, "assert_called")` at `supervisor.py:~480` and again at `:~760`) — production code branching on whether a function has been monkeypatched by a test.

**Fix**: delete `clarification.py` and `clarification_prompt.py`, point `src/agents/__init__.py` at the preflight gatekeeper, and remove the `hasattr(..., "assert_called")` branches (they are unreachable in production and untestable in principle).

### P1-8 — CORS allows credentials with a wildcard origin

```python
# src/api/main.py:79-83
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
```

A wildcard `Access-Control-Allow-Origin` cannot be combined with credentials; compliant browsers reject the response, and non-compliant clients get an over-permissive policy. It is also hard-coded rather than settings-driven.

**Fix**: read an explicit origin list from `Settings` and default to the dev frontend origin(s).

### P1-9 — RBAC is client-supplied and spoofable; `require_admin_role` has a broken signature

- Identity comes entirely from request headers: `X-User-Id`, `X-User-Role` (`dependencies.py:52-77`), and the request body may override the role again (`AskQueryRequest.role`, used at `query.py:52`). Any caller can send `X-User-Role: Admin` and read `/api/v1/audit/logs`, or send `role=Admin` on `/ask` and bypass the `c_phone`/`c_acctbal` column denials (`rbac.py:36-48`). For an academic demo this may be acceptable, but it means **the RBAC matrix is decorative against a hostile client** — and the AST/RBAC nodes will faithfully report "policy passed".
- `require_admin_role(user_context: Annotated[UserContext, Header()] = None, ...)` (`dependencies.py:80-83`) is not a valid FastAPI dependency shape: `UserContext` is a Pydantic model, not a header type, so FastAPI will try to build it from a `user_context` **header**. The `if user_context is not None` / fallback-construct branch exists purely to paper over this. It is used at `audit.py:33`.

**Fix**: (a) derive `role` from a verified token/session, never from the body; (b) rewrite `require_admin_role` to depend on `get_current_user_context`:

```python
def require_admin_role(
    user: Annotated[UserContext, Depends(get_current_user_context)],
) -> UserContext:
    if user.role != UserRole.ADMIN:
        raise HTTPException(403, ...)
    return user
```

### P1-10 — Packaging and container drift

- `pyproject.toml` declares a single dependency (`duckdb>=1.5.5`) and a `uv_build` backend with `text2sql_agent = "text2sql_agent:main"` — a script entry point that **does not exist** in the tree. `requirements.txt` (35 lines) is the real dependency list; the two are unreconciled. `uv.lock` therefore does not describe the application (and appears to contain no `langgraph`/`deepagents`/`langchain` pins at all).
- `Dockerfile` copies `src/` and `pyproject.toml` only. `create_text2sql_supervisor` loads `skills/...` and `AGENTS.md` **at runtime** (`supervisor.py:84-93`), and `SessionTracer` writes to `outputs/`. Neither `skills/` nor `AGENTS.md` is copied → the container starts with `create_deep_agent(skills=None, memory=None)`-style degradation or a load error, silently losing all domain knowledge. `data/` is created but the TPC-H seed also needs `scripts/`-adjacent paths (`seed_tpch_data`), so this needs a deliberate decision.
- `docker-compose.yml` sets `TRACE_OUTPUT_DIR=/app/outputs` — but `Settings.trace_output_dir` reads the env var `TRACE_OUTPUT_DIR`, and `Settings` is `env_file=".env"` + environment; that part works. Volume wiring is fine.
- `.dockerignore` exists; good.

**Fix**: make `requirements.txt` the single source of truth (or move deps into `pyproject.toml` and delete the requirements file), remove the phantom script entry point, and `COPY skills/ AGENTS.md` into the image with a smoke test that asserts the skills were loaded.

---

## 4. P2 — Design risks worth a decision (not necessarily a rewrite)

### P2-1 — Tier-1 regex guard is both over- and under-inclusive, and disagrees with the AST policy

`src/agents/guardrails/regex_guard.py` blocks `\bunion\s+(all\s+)?select\b` (line ~96) and `information_schema` (line ~99), while `ast_sanitizer.sanitize_and_validate_sql` **explicitly accepts** `exp.Union` as a valid root (`ast_sanitizer.py:88`). So a legitimate multi-query answer that unions two result sets is rejected at the front door with a *security* refusal ("vi phạm quy tắc an toàn thông tin"), never reaching the AST layer that would have allowed it. Contradictory policy in two places is a bug magnet: whichever layer a reviewer reads first becomes "the" policy.

It is also under-inclusive: `_DDL_DML_PATTERNS` matches `update <ident> set`, so Vietnamese phrasing like *"cập nhật doanh thu theo tháng"* is fine, but `delete from` inside a legitimate phrase ("xóa các đơn hàng bị hủy" would be Vietnamese and pass) is fine too while English *"how many orders were deleted from the system"* is **blocked**. And the security refusal text is returned as a normal answer, so a false positive is indistinguishable from a genuine violation to the user.

**Fix**: make the AST the single source of truth for SQL-shaped policy; keep regex only for prompt-injection/script patterns; add an explicit allow-list test corpus of ~50 real Vietnamese analytics questions asserting `is_safe=True` (some exist in `tests/agents/test_regex_guard.py` — extend it).

### P2-2 — Preflight is fail-open by design

`evaluate_input_preflight` returns `decision=ALLOWED, tier="fallback"` on **any** LLM exception (`preflight_gatekeeper.py:~176-190`). Fail-open is a defensible choice for availability, and it is documented. But combined with P1-9 (client-supplied role) it means: when the Tier-2 model is rate-limited or mis-keyed, **both** the semantic guardrail *and* the clarification check silently disappear, and requests flow straight through to the analytics path. Note also `.env` sets `LLM_PROVIDER=gemini` with `GEMINI_TIER1_MODEL=gemini-3.5-flash-lite` / `GEMINI_TIER2_MODEL=gemini-3.1-flash-lite` — if those model ids are not valid, `init_chat_model` raises, `get_chat_model` swallows it and returns `None` (`llm_service.py:~118-125`), `evaluate_input_preflight` then... fails open. That failure mode is worth an explicit startup assertion.

**Fix**: add a `preflight_fail_mode: Literal["open","closed"]` setting (default `open`), log a distinctive warning when fallback is taken, and add a `/health` field reporting whether the Tier-2 model actually resolved.

### P2-3 — HITL risk model: hard-coded weights, substring date matching, estimate-based numbers

`hitl_evaluator.py` is a genuine improvement over a single budget check, and `hitl_heavy_tables` / `hitl_time_columns` are properly config-driven (that was the right call — `note.txt` asked for exactly this). Remaining concerns:

- The weights `45 / 30 / 25 / 35 / 40` and the trigger threshold `>= 50` (lines 132-176) are hard-coded, so the "Risk Score formula (% budget, scan ratio, partition key)" that `note.txt` says must apply after deployment to a 1–2M row DB cannot be retuned without a code change.
- `has_time_filter_in_where` uses **substring** matching: `any(tc in col_name for tc in time_columns)` (line ~36). A column named `l_receiptdate_time` matches `date` correctly, but so would `last_update` or `o_updated_date` — i.e. a query that merely mentions a time-ish column anywhere in the WHERE gets credit for having a partition filter. Prefer exact column-name matching against the retrieved schema, plus an explicit check for a *comparison* on that column.
- The whole score is driven by `estimate.estimated_bytes` / `estimated_rows`, which come from parsing DuckDB `EXPLAIN (FORMAT JSON)` and multiplying by a fixed `AVG_BYTES_PER_COLUMN_CELL = 12` `bytes` heuristic (`db_connector.py:17`). That is fine for a demo, but the numbers presented to a human approver ("Dung lượng quét ước tính: 1,234,567 bytes") look authoritative while being a heuristic. Label them as estimates in the UI text.

### P2-4 — SQL generation rebuilds a DeepAgent on every retry, and can silently produce empty SQL

`generate_sql` → `create_sql_generator_agent()` on every call (`sql_generator.py:283-289`), inside a loop that runs up to `max_retries + 1 = 4` times per task (`task_executor.py:92`). Each rebuild loads skills and compiles a graph. On a 3-task plan that is up to 12 agent compilations plus 12 LLM calls per user question.

Also, `_extract_sql_result_from_output` falls back to `SQLGenerationResult(sql="", ...)` (`sql_generator.py:~236`) when the model returns no structured output and no message content. An empty SQL is then handed to the control pipeline, which rejects it as `EMPTY_QUERY` and burns a retry. Better: treat "no SQL produced" as a distinct, diagnosable error and feed *that* back to the generator.

### P2-5 — Exceptions inside the task loop are unhandled

`aexecute_analysis_task`'s `for attempt in range(...)` loop has no `try/except`. Any raise — the P0-1 `TypeError`, `generate_sql`'s `RuntimeError("Không thể khởi tạo mô hình Chat Model Tier 1...")` (`sql_generator.py:277`), a DuckDB connection error, a network timeout from the LLM — aborts the whole task, then the node, then the subgraph. The `QueryArtifact` that the architecture promises ("mọi kết quả trung gian ... trong Pydantic Models") is never created, and the user sees a raw Python string via the supervisor's `except Exception` branch.

**Fix**: wrap the attempt body; convert exceptions into a `QueryArtifact(status="DB_ERROR")` plus a structured `error_context` so the next attempt can self-correct, and keep the run going.

### P2-6 — The evidence loop is bounded by count but not by identity or cost

`evidence_node` appends the LLM-proposed `next_task` when `len(plan.tasks) < plan.max_tasks` (`analytics/nodes.py:~115-135`). There is **no check** that the proposed `task_id` is new (the prompt asks for it, nothing enforces it) and no check that the SQL is not a near-duplicate of an already-executed query. With `max_tasks=3` the blast radius is small, but the loop can still burn the budget re-asking a question it already answered. Consider de-duplicating on `(description, tables)` and passing the list of already-run task descriptions explicitly.

### P2-7 — The presentational LLM is the final author of the user-facing answer, with no output guard

`presentation_node` → `ResponseSynthesizer.synthesize` → `SynthesisDecision.direct_answer`, and the analytics runnable turns exactly that string into the supervisor's final answer (`analytics/graph.py:145-149`). The `direct_answer` is free-form LLM text about real data. "Zero Data = Zero Insight" is enforced (correctly) by the **prompt** and by the empty-artifact fast paths, but there is no mechanical verification that a number quoted in `direct_answer` actually appears in the hydrated artifact data. Given v4's own goal of eliminating trust-me prose, a cheap numeric-claim check (every number-like token in `direct_answer`/`detailed_insight` should be traceable to a hydrated artifact cell, else flag/replace) would be a high-value addition — and it is deterministic, so it fits the architecture's stated philosophy.

### P2-8 — `analytics/nodes.py` status handling is inconsistent

`presentation_node` sets `status = "COMPLETED" if has_success else "FAILED"`, but `AnalyticsState.status` is typed `Literal["COMPLETED","PARTIAL","FAILED"]` and `PARTIAL` is never produced even though the executor happily mixes SUCCESS and failed artifacts (`executor_node`). A plan where task 1 succeeded and task 2 failed reports `FAILED` and the user loses the successful evidence in the status, even though the `ResponsePackage` still contains it.

---

## 5. What is genuinely good — do not regress these

1. **`ast_sanitizer.py`** — the best file in the repo. `sqlglot.parse` → reject multiple statements → root must be `Select`/`Union` → walk the **whole** tree for `Insert/Update/Delete/Drop/Alter/Create/TruncateTable/Command/Transaction` → strip CTE names from `tables_used` → force/overwrite `LIMIT`. This is the correct way to enforce SELECT-only, and it is enforced in the deterministic layer where `AGENTS.md` requires it.
2. **`audit_logger.py`** — append-only JSONL, `query_id` UUID, UTC timestamps, and a genuine fail-safe (`except` → log and return `False`, never raise). Audit logging that cannot break the pipeline is a real engineering decision, and it is honoured in `audit_node`.
3. **`db_connector.py`** — the `BaseWarehouseConnector` ABC with DuckDB and BigQuery implementations (real `dry_run=True` + `total_bytes_billed`) is clean strategy-pattern work, and `CostEstimateResult` makes the budget decision explicit.
4. **`models/artifacts.py`** — the typed contract is well designed: discriminated `ArtifactItem` union, `ArtifactSpec` (spec) separated from hydrated artifacts (data), `AnalysisPlan.validate_budget_ceiling`, `ResponsePackage.layout`. This is exactly the right shape and worth finishing rather than abandoning.
5. **Config-driven HITL tables/columns** — `heavy_tables_set` / `time_columns_set` as properties over comma-separated settings directly answers the `note.txt` requirement about not hard-coding `lineitem, orders`.
6. **Test breadth** — ~180 tests across `tests/agents`, `tests/utils`, `tests/prompts`, `tests/core`, plus frontend vitest suites. The per-unit depth (e.g. `test_control_pipeline.py` at 20KB across all five gate branches) is above typical project quality. The gap is at the *seams*, not in the units.
7. **Routers as pure functions** — `control_pipeline/routers.py` is 5 small predicates reading state flags. Deterministic, trivially testable, exactly as `AGENTS.md` requires for the safety layer.

---

## 6. Documentation vs code drift

| Document claim | Reality |
|---|---|
| `docs/agent-architecture-v4.md` §7: warehouse abstraction is `src/utils/warehouse_client.py` | **File does not exist.** Actual: `src/utils/db_connector.py`. |
| `AGENTS.md` §1: "Đề tài & yêu cầu chấm điểm: `DETAI.md`" | `DETAI.md` does not exist at root. Closest: `docs/DETAI_OLD.md`. |
| `AGENTS.md` §1: "`docs/agent-architecture-v2.md`" | Path is now `docs/agent/agent-architecture-v2.md`. |
| `docs/agent-architecture-v4.md` §6 "Dual-Budget Guardrails" table | `max_analysis_queries` and `max_analysis_runtime_seconds` are unimplemented (P1-5). |
| `docs/architecture_review.md` (prior review) marks the HITL resume bug as "Confirmed ... should be fixed" | A fix attempt exists in `query.py:290-340`, but the flow is still non-functional for different reasons (P0-2). The prior review's *conclusion* is still accurate; its "fixed" implication is not. |
| `AGENTS.md` §3: `.venv\Scripts\Activate.ps1` as the standard workflow | The venv is **broken** on this machine (Windows Store base interpreter). Anyone following `AGENTS.md` cannot run the tests. |
| `note.txt` items marked `(DONE)` | Verified DONE: dynamic heavy-table config, TPC-DS/multi-SQL decision, input guardrails, first-route plan/answer node. **NOT** done: MCP sql knowledge (correctly still marked NOT IMPLEMENTED); "Check kỹ skill cho deepagent nhé" — the skills are loaded but the container never ships them (P1-10). |
| `docs/agent-architecture-v4.md` §1.1.3: regex parsing is an anti-pattern to eliminate | `query.py:119-137` and `frontend/utils/markdownChartParser.ts` still do exactly that (P1-6). |

---

## 7. Test gaps that let the P0s through

| Gap | Why it matters | Suggested test |
|---|---|---|
| `tests/agents/test_task_executor.py` mocks `run_control_pipeline` in **every** test | The P0-1 signature error is invisible | One test that builds the *real* graph (`build_control_pipeline_graph()`) against the in-memory TPC-H fixture and runs one task end-to-end. |
| No test drives `build_analytics_graph()` with a real control pipeline | The subgraph has never been executed as a whole | `graph.ainvoke({"question": ..., "user_context": ...})` with a stub LLM returning a fixed `AnalysisPlan`; assert `response_package.artifacts` is non-empty and `artifacts[0].tables_used` is populated (catches P1-1 too). |
| No HITL round-trip test | P0-2/P0-3 are invisible | `POST /ask` (forced risky SQL) → assert `PENDING_APPROVAL` + a pending record exists → `POST /approve {approved: true}` → assert the query executed and the audit log contains exactly one SUCCESS row. |
| No test asserts a **failed** analysis maps to a non-COMPLETED API status | P0-4 | Patch `generate_sql` to always return invalid SQL; assert `QueryResponse.status != "COMPLETED"`. |
| No contract test between `api_schemas.QueryResponse` and `frontend/types/api.ts` | P1-6 drift will keep growing | Generate TS types from the Pydantic model (or assert a shared JSON-schema fixture) in CI. |
| No test exercises `role=business_user` / `X-User-Role: business_user` | P0-5 | Parametrise `get_current_user_context` over every documented role string. |
| No startup/health assertion that the configured LLM actually resolved | P2-2 silent fail-open | Assert `get_chat_model("tier2") is not None` in CI with a dummy key, and expose it on `/health`. |

---

## 8. Recommended order of work

**Stage 0 — unblock (hours)**
1. `P0-1` fix the `run_control_pipeline` call site (+ make `graph` optional / cached). Then add the end-to-end task test so it cannot regress.
2. `P0-5` remove or implement `BUSINESS_USER`.
3. Repair `.venv` and commit the v4 work — **the whole v4 layer is currently uncommitted.**

**Stage 1 — make the safety story true (1–2 days)**
4. `P0-2` pick real-interrupt *or* approval-token, implement it once, wire `/approve` to the same object, add the round-trip test.
5. `P0-3` replace the two prose-regex guards with typed signals (`status`, `artifacts`, a `hitl` object). Delete `check_hitl_pending`/`verify_pipeline_execution_integrity` entirely once the typed path is in.
6. `P0-4` propagate the inner status to the API.
7. `P1-1` add `tables_used`/`columns_used`/`row_count` to `ControlPipelineOutput`.

**Stage 2 — make it hold up under use (2–3 days)**
8. `P1-2` async-ify the inner calls (or `to_thread`) — this is a user-visible latency/scale bug.
9. `P1-3` cache the compiled supervisor.
10. `P1-5` enforce `max_analysis_queries` / `max_analysis_runtime_seconds`; read retries from settings.
11. `P2-5` wrap the task loop; produce failed artifacts instead of exceptions.

**Stage 3 — finish the migration or declare it (2–3 days)**
12. `P1-6` either render `ResponsePackage` in the UI and delete the Markdown regex, or mark the typed contract internal-only.
13. `P1-7` delete `clarification.py`, remove the `hasattr(..., "assert_called")` branches.
14. `P1-9` stop trusting client-supplied roles (minimum: stop accepting `role` in the request body).
15. `P1-10` one dependency manifest; copy `skills/` + `AGENTS.md` into the image.

**Stage 4 — quality (as time allows)**
16. `P2-1` align regex guard with AST policy + a false-positive corpus.
17. `P2-3` move risk weights into config; tighten the time-filter check.
18. `P2-7` deterministic numeric-claim verification for `direct_answer`.
19. Documentation: fix the stale paths in `AGENTS.md` and `docs/agent-architecture-v4.md`.

---

## Appendix A — Files reviewed

**Backend agents**: `supervisor.py`, `analytics/{graph,nodes,planner,task_executor,evidence_analyzer,response_synthesizer,__init__}.py`, `control_pipeline/{builder,nodes,routers,diagnostic,hitl_evaluator,__init__}.py`, `guardrails/{regex_guard,__init__}.py`, `preflight_gatekeeper.py`, `clarification.py`, `consultation.py`, `schema_retriever.py`, `sql_generator.py`, `self_correction.py`, `synthesizer.py`, `prompts/{supervisor,preflight,sql_generator,evidence_analyzer,analytics_planner,analytics_presentation,__init__}.py`, `tools/{metadata_tools,__init__}.py`, `agents/__init__.py`

**Models/services**: `models/{state,artifacts,rbac,api_schemas}.py`, `services/{llm_service,__init__}.py`, `config.py`, `prompts.py`

**Utils**: `utils/{ast_sanitizer,rbac_enforcer,db_connector,audit_logger,session_tracer,schema_context,categorical_search,table_keywords,tpch_seeder}.py`

**API**: `api/{main,dependencies}.py`, `api/routes/{query,audit}.py`

**Frontend (targeted)**: `types/api.ts`, `services/api.ts`, `utils/markdownChartParser.ts`, `components/chat/ChatMessageItem.tsx`, `components/layout/RoleSwitcher.tsx`

**Tests (targeted)**: `tests/conftest.py`, `test_api.py`, `agents/test_task_executor.py`, `agents/test_control_pipeline.py`, `agents/test_preflight_gatekeeper.py`, `agents/test_regex_guard.py`

**Docs**: `AGENTS.md`, `README.md`, `note.txt`, `docs/agent-architecture-v4.md`, `docs/architecture_review.md`, `docs/PRD.md`, `docs/decisions/0003-*.md`, `skills/*/SKILL.md`

**Packaging**: `pyproject.toml`, `requirements.txt`, `uv.lock`, `ruff.toml`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.gitignore`, `.env.example`, `.env` (keys only), `.github/workflows/ci.yaml`

## Appendix B — Reproduction checklist (run once the venv works)

```powershell
# 0. Repair the environment first (see §0)
py -3.11 -m venv .venv          # or: uv venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 1. P0-1 — prove the signature mismatch without running the graph
python -c "import inspect; from src.agents.control_pipeline import run_control_pipeline; print(inspect.signature(run_control_pipeline))"
python -m pytest tests/agents/test_task_executor.py -q          # passes only because of patch()

# 2. P0-5
python -c "from src.models.rbac import UserRole; print(list(UserRole))"

# 3. Full suite (baseline)
python -m pytest tests/ -q

# 4. Full-stack smoke (needs a real API key in .env)
uvicorn src.api.main:app --port 8000
curl -X POST http://localhost:8000/api/v1/query/ask -H "Content-Type: application/json" `
     -d '{"question":"Top 5 khach hang co tong chi tieu cao nhat nam 1995","session_id":"smoke1"}'
```

**One-command sanity check for P0-1** (no graph execution needed): the two signatures below must agree —

```powershell
rg -n "def run_control_pipeline" src/agents/control_pipeline/builder.py
rg -n "run_control_pipeline\(" src/agents/analytics/task_executor.py src/agents/self_correction.py
```
