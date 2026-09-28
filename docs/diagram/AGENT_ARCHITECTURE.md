# Báo Cáo Kiến Trúc Hệ Thống & Luồng Hoạt Động Agent (v4.0)

> **Tuyên bố phương pháp**: Tài liệu và các sơ đồ trực quan dưới đây được trích xuất và phân tích **100% từ mã nguồn thực tế** của repository (không sử dụng hay đối chiếu với các tệp thiết kế tài liệu cũ trong thư mục `docs/`).  
> Định dạng trực quan tuân thủ tuyệt đối quy chuẩn **`/documd-visuals`** (Bare HTML/CSS Layouts và PlantUML Fences theo bảng màu Slate Theme).

---

## 1. SƠ ĐỒ KIẾN TRÚC TỔNG THỂ (AGENT ARCHITECTURE BLUEPRINT)

Hệ thống được thiết kế theo mô hình **Hybrid Architecture**: kết hợp tầng suy luận tác tử phân cấp ([`deepagents`](file:///d:/Text2SQL-AI-Agent/src/agents/supervisor.py)) với đường ống kiểm soát an toàn tất định ([`LangGraph`](file:///d:/Text2SQL-AI-Agent/src/agents/control_pipeline/builder.py)).

<div style="max-width: 1140px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-cs { background: #f8fafc; padding: 24px; color: #1f2937; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; border: 1px solid #cbd5e1; border-radius: 8px; }
    .arch-cs-title { margin: 0 0 6px; text-align: center; font-size: 24px; font-weight: 700; color: #0f172a; }
    .arch-cs-sub { margin: 0 0 16px; text-align: center; font-size: 13px; color: #475569; }
    .arch-cs-body { display: grid; grid-template-columns: 210px 1fr 210px; gap: 12px; align-items: stretch; }
    .arch-cs-wing { display: flex; flex-direction: column; gap: 8px; padding: 12px; border-radius: 6px; background: #f1f5f9; border: 2px solid #334155; }
    .arch-cs-wing-head { font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; text-align: center; padding-bottom: 6px; border-bottom: 1px solid #94a3b8; color: #0f172a; }
    .arch-cs-group { padding: 7px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; }
    .arch-cs-group-title { font-size: 11px; font-weight: 700; text-align: center; margin-bottom: 5px; color: #1e293b; }
    .arch-cs-group-items { display: grid; gap: 4px; }
    .arch-cs-group-item { padding: 4px 6px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 3px; font-size: 10px; line-height: 1.25; text-align: center; color: #334155; font-weight: 500; }
    .arch-cs-core { display: grid; gap: 8px; align-content: stretch; }
    .arch-cs-layer { padding: 8px 10px; border-radius: 5px; border: 1px solid #94a3b8; }
    .arch-cs-layer.api { background: #e0e7ff; border-color: #6366f1; }
    .arch-cs-layer.preflight { background: #fee2e2; border-color: #ef4444; }
    .arch-cs-layer.supervisor { background: #dbeafe; border-color: #3b82f6; }
    .arch-cs-layer.analytics { background: #fef3c7; border-color: #f59e0b; }
    .arch-cs-layer.control { background: #ccfbf1; border-color: #14b8a6; }
    .arch-cs-layer.warehouse { background: #f3e8ff; border-color: #a855f7; }
    .arch-cs-layer-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; }
    .arch-cs-layer-name { font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #0f172a; }
    .arch-cs-layer-note { font-size: 10px; color: #475569; }
    .arch-cs-items { display: grid; gap: 6px; }
    .arch-cs-items.c2 { grid-template-columns: repeat(2, 1fr); }
    .arch-cs-items.c3 { grid-template-columns: repeat(3, 1fr); }
    .arch-cs-items.c4 { grid-template-columns: repeat(4, 1fr); }
    .arch-cs-items.c5 { grid-template-columns: repeat(5, 1fr); }
    .arch-cs-box { padding: 6px 6px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 10px; font-weight: 600; line-height: 1.25; text-align: center; color: #0f172a; }
    .arch-cs-box small { display: block; font-size: 9px; font-weight: 400; color: #64748b; margin-top: 2px; }
    .arch-cs-box.entry { border: 2px solid #2563eb; }
    .arch-cs-box.highlight { border: 2px solid #d97706; background: #fffbeb; }
    .arch-cs-box.danger { border: 2px solid #dc2626; background: #fef2f2; }
    .arch-cs-box.secure { border: 2px solid #059669; background: #ecfdf5; }
    .arch-cs-foot { margin: 10px 0 0; padding-top: 8px; border-top: 1px solid #cbd5e1; font-size: 11px; color: #64748b; text-align: center; }
  </style>
  <section class="arch-cs">
    <h1 class="arch-cs-title">Text2SQL AI Agent: Hệ Thống Kiến Trúc Thực Tế (v4.0)</h1>
    <p class="arch-cs-sub">Kiến trúc đa tầng kết hợp suy luận tác tử (DeepAgents) và đường ống kiểm soát tất định (LangGraph)</p>
    <div class="arch-cs-body">
      <aside class="arch-cs-wing">
        <div class="arch-cs-wing-head">An ninh &amp; Vận hành<br>(Cross-Cutting)</div>
        <div class="arch-cs-group">
          <div class="arch-cs-group-title">Ngữ cảnh &amp; Quyền hạn</div>
          <div class="arch-cs-group-items">
            <div class="arch-cs-group-item">UserContext (RBAC)</div>
            <div class="arch-cs-group-item">Thread / Session ID</div>
          </div>
        </div>
        <div class="arch-cs-group">
          <div class="arch-cs-group-title">Bộ nhớ &amp; Trạng thái</div>
          <div class="arch-cs-group-items">
            <div class="arch-cs-group-item">MemorySaver Checkpointer</div>
            <div class="arch-cs-group-item">StateBackend Virtual FS</div>
          </div>
        </div>
        <div class="arch-cs-group">
          <div class="arch-cs-group-title">Quan sát &amp; Ghi vết</div>
          <div class="arch-cs-group-items">
            <div class="arch-cs-group-item">SessionTracer (Artifacts)</div>
            <div class="arch-cs-group-item">AuditLogger (JSON Logs)</div>
          </div>
        </div>
      </aside>
      <div class="arch-cs-core">
        <div class="arch-cs-layer api">
          <div class="arch-cs-layer-head">
            <span class="arch-cs-layer-name">Tầng 1: Interface &amp; API Layer</span>
            <span class="arch-cs-layer-note">Cổng giao tiếp FastAPI &amp; Frontend</span>
          </div>
          <div class="arch-cs-items c3">
            <div class="arch-cs-box entry">POST /api/v1/query/ask<small>Tiếp nhận truy vấn tự nhiên</small></div>
            <div class="arch-cs-box">POST /api/v1/query/approve<small>Phê duyệt HITL (Command Resume)</small></div>
            <div class="arch-cs-box">GET /api/v1/query/history<small>Tra cứu Session Trace &amp; Artifacts</small></div>
          </div>
        </div>
        <div class="arch-cs-layer preflight">
          <div class="arch-cs-layer-head">
            <span class="arch-cs-layer-name">Tầng 2: Pre-Flight Gatekeeper Engine</span>
            <span class="arch-cs-layer-note">Chốt chặn an toàn 2 tầng &amp; Fast-Path Clarification</span>
          </div>
          <div class="arch-cs-items c3">
            <div class="arch-cs-box danger">Tier 1: Regex Guardrails<small>&lt;0.1ms, chặn DDL/DML &amp; Injection</small></div>
            <div class="arch-cs-box highlight">Tier 2: Unified LLM Guard<small>Đánh giá mơ hồ &amp; ngoài miền TPC-H</small></div>
            <div class="arch-cs-box secure">Decision Router<small>ALLOWED | CLARIFICATION | BLOCKED</small></div>
          </div>
        </div>
        <div class="arch-cs-layer supervisor">
          <div class="arch-cs-layer-head">
            <span class="arch-cs-layer-name">Tầng 3: Master Deep Agent Supervisor</span>
            <span class="arch-cs-layer-note">Điều phối tối cao (Pure Orchestration via deepagents)</span>
          </div>
          <div class="arch-cs-items c3">
            <div class="arch-cs-box">Tier 1 Reasoning LLM<small>OpenAI / Gemini 2.5 Pro</small></div>
            <div class="arch-cs-box">TodoListMiddleware<small>Lập kế hoạch động (write_todos)</small></div>
            <div class="arch-cs-box">Context &amp; Loop Guard<small>ToolCallLimit &amp; Summarization</small></div>
          </div>
          <div class="arch-cs-items c2" style="margin-top: 6px;">
            <div class="arch-cs-box">Subagent: consultation-agent<small>Giao tiếp xã giao &amp; tra cứu danh mục TPC-H (No SQL)</small></div>
            <div class="arch-cs-box entry">Subagent: analytics-subagent<small>CompiledSubAgent đóng gói Analytics LangGraph Subgraph</small></div>
          </div>
        </div>
        <div class="arch-cs-layer analytics">
          <div class="arch-cs-layer-head">
            <span class="arch-cs-layer-name">Tầng 4: Analytics LangGraph Subgraph (v4.0)</span>
            <span class="arch-cs-layer-note">Quy trình phân tích dữ liệu đa nhiệm &amp; Đóng gói phản hồi</span>
          </div>
          <div class="arch-cs-items c4">
            <div class="arch-cs-box">planner_node<small>Sinh AnalysisPlan (1-3 tasks)</small></div>
            <div class="arch-cs-box highlight">executor_node<small>Schema + SQLGen + Control Pipeline</small></div>
            <div class="arch-cs-box">evidence_node<small>Evidence Analyzer &amp; Drill-down</small></div>
            <div class="arch-cs-box secure">presentation_node<small>ResponseSynthesizer + Data Hydration</small></div>
          </div>
        </div>
        <div class="arch-cs-layer control">
          <div class="arch-cs-layer-head">
            <span class="arch-cs-layer-name">Tầng 5: Deterministic Control Pipeline Subgraph</span>
            <span class="arch-cs-layer-note">Hàng rào an ninh tất định &amp; Tự chẩn đoán lỗi</span>
          </div>
          <div class="arch-cs-items c5">
            <div class="arch-cs-box secure">ast_check<small>sqlglot SELECT only</small></div>
            <div class="arch-cs-box secure">rbac_check<small>Bảo vệ cột nhạy cảm</small></div>
            <div class="arch-cs-box highlight">cost_guard<small>Dry-run &amp; Quét dung lượng</small></div>
            <div class="arch-cs-box danger">hitl_gate<small>interrupt() chờ duyệt</small></div>
            <div class="arch-cs-box">execute<small>Warehouse limit/timeout</small></div>
          </div>
          <div class="arch-cs-items c2" style="margin-top: 6px;">
            <div class="arch-cs-box danger">err_node &amp; diagnostic<small>LLM phân tích nguyên nhân lỗi &amp; gợi ý sửa</small></div>
            <div class="arch-cs-box secure">audit_node<small>Ghi log kiểm toán toàn diện trước khi END</small></div>
          </div>
        </div>
        <div class="arch-cs-layer warehouse">
          <div class="arch-cs-layer-head">
            <span class="arch-cs-layer-name">Tầng 6: Data &amp; Warehouse Layer</span>
            <span class="arch-cs-layer-note">Cơ sở dữ liệu TPC-H Benchmark</span>
          </div>
          <div class="arch-cs-items c4">
            <div class="arch-cs-box">DuckDB Engine<small>OLAP In-Memory / Local DB</small></div>
            <div class="arch-cs-box">8 Bảng TPC-H<small>CUSTOMER, ORDERS, LINEITEM...</small></div>
            <div class="arch-cs-box">dbt Semantic Layer<small>Công thức Metrics chuẩn</small></div>
            <div class="arch-cs-box">Vector/Keyword Index<small>Tra cứu Categorical Values</small></div>
          </div>
        </div>
      </div>
      <aside class="arch-cs-wing">
        <div class="arch-cs-wing-head">Kỹ Năng &amp; Tri Thức<br>(Domain Knowledge)</div>
        <div class="arch-cs-group">
          <div class="arch-cs-group-title">Kỹ năng DeepAgents</div>
          <div class="arch-cs-group-items">
            <div class="arch-cs-group-item">skills/tpch-analytics</div>
            <div class="arch-cs-group-item">skills/duckdb-sql</div>
            <div class="arch-cs-group-item">skills/analytics-orchestrator</div>
          </div>
        </div>
        <div class="arch-cs-group">
          <div class="arch-cs-group-title">Quy chuẩn Vận hành</div>
          <div class="arch-cs-group-items">
            <div class="arch-cs-group-item">AGENTS.md Memory</div>
            <div class="arch-cs-group-item">DuckDB Dialect Rules</div>
          </div>
        </div>
        <div class="arch-cs-group">
          <div class="arch-cs-group-title">Metadata Tools</div>
          <div class="arch-cs-group-items">
            <div class="arch-cs-group-item">search_tables_and_columns</div>
            <div class="arch-cs-group-item">get_column_samples_and_values</div>
            <div class="arch-cs-group-item">find_join_path (BFS)</div>
            <div class="arch-cs-group-item">search_business_definition</div>
          </div>
        </div>
      </aside>
    </div>
    <p class="arch-cs-foot">Cấu trúc thực tế bóc tách từ mã nguồn: Hai cánh hỗ trợ kéo dài bao bọc toàn bộ chu trình xử lý của tác tử.</p>
  </section>
</div>

---

## 2. LUỒNG TIẾN TRÌNH END-TO-END (PIPELINE STAGES FLOW)

Toàn bộ quá trình từ khi tiếp nhận câu hỏi của người dùng cho đến khi trả về kết quả số liệu, biểu đồ Recharts và bài phân tích trải qua 5 giai đoạn nghiêm ngặt:

<div style="max-width: 1140px; box-sizing: border-box; position: relative;">
  <style scoped>
    .arch-pipe { background: #f8fafc; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1f2937; border: 1px solid #cbd5e1; border-radius: 8px; }
    .arch-pipe-title { margin: 0 0 6px; text-align: center; font-size: 24px; font-weight: 700; color: #0f172a; }
    .arch-pipe-sub { margin: 0 0 16px; text-align: center; font-size: 13px; color: #475569; }
    .arch-pipe-io { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px; }
    .arch-pipe-source { padding: 8px 10px; text-align: center; font-size: 11px; font-weight: 600; background: #ffffff; border: 1px dashed #64748b; border-radius: 4px; color: #1e293b; }
    .arch-pipe-row { display: flex; align-items: stretch; gap: 0; }
    .arch-pipe-stage { flex: 1; padding: 10px; border-radius: 6px; background: #f1f5f9; border: 1px solid #94a3b8; }
    .arch-pipe-stage.landing { background: #fee2e2; border-color: #ef4444; }
    .arch-pipe-stage.orchestrate { background: #dbeafe; border-color: #3b82f6; }
    .arch-pipe-stage.analyze { background: #fef3c7; border-color: #f59e0b; }
    .arch-pipe-stage.control { background: #ccfbf1; border-color: #14b8a6; }
    .arch-pipe-stage.serve { background: #ede9fe; border-color: #8b5cf6; }
    .arch-pipe-num { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: #1e293b; color: #ffffff; font-size: 10px; font-weight: 700; margin-right: 6px; }
    .arch-pipe-head { font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #0f172a; margin-bottom: 8px; }
    .arch-pipe-item { padding: 6px 8px; margin-bottom: 6px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 3px; font-size: 11px; line-height: 1.3; color: #1e293b; font-weight: 500; }
    .arch-pipe-item:last-child { margin-bottom: 0; }
    .arch-pipe-item small { display: block; font-size: 9px; color: #64748b; margin-top: 2px; }
    .arch-pipe-item.dead { border-style: dashed; color: #dc2626; border-color: #f87171; background: #fef2f2; }
    .arch-pipe-arrow { display: flex; align-items: center; justify-content: center; width: 28px; flex-shrink: 0; font-size: 18px; color: #64748b; }
    .arch-pipe-sla { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 14px; }
    .arch-pipe-kpi { padding: 8px; text-align: center; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; }
    .arch-pipe-kpi b { display: block; font-size: 16px; font-weight: 700; color: #0f172a; }
    .arch-pipe-kpi span { font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }
    .arch-pipe-note { margin-top: 10px; font-size: 11px; color: #64748b; text-align: center; }
  </style>
  <section class="arch-pipe">
    <h1 class="arch-pipe-title">Luồng Hoạt Động Xử Lý Truy Vấn End-to-End</h1>
    <p class="arch-pipe-sub">Tiến trình 5 giai đoạn từ lúc gửi câu hỏi đến khi nhận bảng dữ liệu và biểu đồ trực quan</p>
    <div class="arch-pipe-io">
      <div class="arch-pipe-source">Đầu vào 1: Câu hỏi phân tích (NL Question)</div>
      <div class="arch-pipe-source">Đầu vào 2: User Context (ID, Role, Session ID)</div>
      <div class="arch-pipe-source">Đầu vào 3: HITL Decision (Approved / Rejected)</div>
    </div>
    <div class="arch-pipe-row">
      <div class="arch-pipe-stage landing">
        <div class="arch-pipe-head"><span class="arch-pipe-num">1</span>Pre-Flight</div>
        <div class="arch-pipe-item">Tier 1 Regex Guard<small>&lt;0.1ms, chặn DDL/DML</small></div>
        <div class="arch-pipe-item">Tier 2 LLM Guard<small>Kiểm tra mơ hồ / ngoài miền</small></div>
        <div class="arch-pipe-item dead">Chặn vi phạm<small>SECURITY_BLOCKED</small></div>
        <div class="arch-pipe-item dead">Fast-Path làm rõ<small>CLARIFICATION_REQUIRED</small></div>
      </div>
      <div class="arch-pipe-arrow">→</div>
      <div class="arch-pipe-stage orchestrate">
        <div class="arch-pipe-head"><span class="arch-pipe-num">2</span>Supervisor</div>
        <div class="arch-pipe-item">Context Isolation<small>Tracer &amp; StateBackend</small></div>
        <div class="arch-pipe-item">TodoList Planning<small>Phân bổ tác vụ động</small></div>
        <div class="arch-pipe-item">Consultation Agent<small>Xã giao / tra cứu metadata</small></div>
        <div class="arch-pipe-item">Delegate Analytics<small>Gọi analytics-subagent</small></div>
      </div>
      <div class="arch-pipe-arrow">→</div>
      <div class="arch-pipe-stage analyze">
        <div class="arch-pipe-head"><span class="arch-pipe-num">3</span>Analytics Subgraph</div>
        <div class="arch-pipe-item">Planner Node<small>Sinh AnalysisPlan (1-3 tasks)</small></div>
        <div class="arch-pipe-item">Schema &amp; Categorical<small>Top-k tables &amp; values</small></div>
        <div class="arch-pipe-item">SQL Generator<small>DuckDB dialect + 4 tools</small></div>
        <div class="arch-pipe-item">Self-Correction<small>Vòng lặp sửa lỗi ≤ 3 lần</small></div>
      </div>
      <div class="arch-pipe-arrow">→</div>
      <div class="arch-pipe-stage control">
        <div class="arch-pipe-head"><span class="arch-pipe-num">4</span>Control Pipeline</div>
        <div class="arch-pipe-item">AST Sanitizer<small>sqlglot SELECT only</small></div>
        <div class="arch-pipe-item">RBAC Policy<small>Kiểm soát quyền truy cập</small></div>
        <div class="arch-pipe-item">Cost &amp; Risk Guard<small>Dry-run &amp; Cartesian check</small></div>
        <div class="arch-pipe-item dead">HITL Gatekeeper<small>interrupt() PENDING_APPROVAL</small></div>
        <div class="arch-pipe-item">Warehouse Executor<small>Timeout 30s &amp; Limit 5000</small></div>
      </div>
      <div class="arch-pipe-arrow">→</div>
      <div class="arch-pipe-stage serve">
        <div class="arch-pipe-head"><span class="arch-pipe-num">5</span>Synthesis &amp; Serve</div>
        <div class="arch-pipe-item">Evidence Analyzer<small>Đánh giá đủ dữ liệu / Drill-down</small></div>
        <div class="arch-pipe-item">Response Synthesizer<small>Nhịp 1: Direct answer &amp; Specs</small></div>
        <div class="arch-pipe-item">Data Hydrator<small>Nhịp 2: Rót data thật 100%</small></div>
        <div class="arch-pipe-item">Final Response<small>KPI, Recharts, Data Table, SQL</small></div>
      </div>
    </div>
    <div class="arch-pipe-sla">
      <div class="arch-pipe-kpi"><b>&lt; 0.1 ms</b><span>Tier 1 Regex Latency</span></div>
      <div class="arch-pipe-kpi"><b>Tối đa 3 lần</b><span>Self-Correction Retry</span></div>
      <div class="arch-pipe-kpi"><b>100% Thực tế</b><span>Data Hydration Accuracy</span></div>
      <div class="arch-pipe-kpi"><b>SELECT Only</b><span>Cấm tuyệt đối DDL/DML</span></div>
    </div>
    <p class="arch-pipe-note">Các ô nét đứt màu đỏ là các lối thoát rẽ nhánh an toàn (Chặn an ninh, Fast-Path yêu cầu làm rõ, hoặc Tạm dừng chờ duyệt HITL).</p>
  </section>
</div>

---

## 3. BIỂU ĐỒ TUẦN TỰ TƯƠNG TÁC (PLANTUML SEQUENCE FLOW)

```puml
@startuml
skinparam handwritten false
skinparam monochrome false
skinparam shadowing false
skinparam defaultFontName "Segoe UI"
skinparam roundcorner 4
skinparam participantBorderColor #334155
skinparam participantBackgroundColor #F8FAFC
skinparam sequenceLifeLineBorderColor #64748B

actor "Người Dùng (Client)" as User
participant "FastAPI\n(/query/ask)" as API
participant "PreflightGatekeeper\n(Regex & LLM)" as Gatekeeper
participant "Master Supervisor\n(DeepAgent Tier 1)" as Supervisor
participant "Analytics Subgraph\n(LangGraph v4.0)" as Analytics
participant "Task Executor &\nSQL Generator" as Executor
participant "Control Pipeline\n(Deterministic Subgraph)" as Control
participant "HITL Gatekeeper\n(interrupt)" as HITL
database "Warehouse\n(DuckDB Engine)" as Warehouse

User -> API: POST /ask (question, user_context, session_id)
activate API

API -> Gatekeeper: evaluate_input_preflight(question)
activate Gatekeeper
alt Phát hiện DDL/DML / Prompt Injection
    Gatekeeper --> API: PreflightDecision(SECURITY_BLOCKED, refusal_message)
    API --> User: QueryResponse(status="SECURITY_BLOCKED", refusal_reason)
else Phát hiện câu hỏi mơ hồ
    Gatekeeper --> API: PreflightDecision(CLARIFICATION_REQUIRED, options)
    API --> User: QueryResponse(status="CLARIFICATION_REQUIRED", suggested_options)
else Câu hỏi hợp lệ (ALLOWED)
    Gatekeeper --> API: PreflightDecision(ALLOWED)
end
deactivate Gatekeeper

API -> Supervisor: arun_supervisor(question, user_context, checkpointer)
activate Supervisor

Supervisor -> Supervisor: TodoListMiddleware: lập kế hoạch phân bổ tác vụ

alt Intent = CONVERSATION / METADATA
    Supervisor -> Supervisor: Giao cho consultation-agent (Metadata Tools)
    Supervisor --> API: Tra cứu danh mục / Trả lời xã giao (No SQL)
else Intent = ANALYTICS
    Supervisor -> Analytics: ainvoke() Analytics Subgraph
    activate Analytics

    Analytics -> Analytics: planner_node: sinh AnalysisPlan (1-3 tasks)

    loop Cho từng Task trong AnalysisPlan (Tối đa 3 lần Retry nếu lỗi)
        Analytics -> Executor: aexecute_analysis_task(task, prior_artifacts)
        activate Executor

        Executor -> Executor: Schema Retriever: DDL bảng & Categorical Values
        Executor -> Executor: SQL Generator: sinh câu lệnh DuckDB SQL

        Executor -> Control: run_control_pipeline(sql, user_context)
        activate Control

        Control -> Control: ast_check: sqlglot kiểm tra gốc cú pháp SELECT
        Control -> Control: rbac_check: kiểm tra quyền bảng/cột nhạy cảm
        Control -> Control: cost_guard: EXPLAIN dry-run & quét dung lượng

        alt Truy vấn vượt ngưỡng rủi ro (Composite Risk > Threshold)
            Control -> HITL: hitl_gate: kích hoạt interrupt()
            activate HITL
            HITL --> Supervisor: Trạng thái PENDING_APPROVAL
            Supervisor --> API: Phản hồi yêu cầu phê duyệt
            API --> User: QueryResponse(status="PENDING_APPROVAL", requires_hitl=True)
            
            note over User, HITL
              Người dùng gửi POST /approve (approved=True)
              API resume graph: Command(resume={"hitl_approved": True})
            end note
            
            User -> API: POST /approve (session_id, approved=True)
            API -> HITL: Resume graph với Command(resume=True)
            HITL --> Control: Cho phép tiếp tục thực thi
            deactivate HITL
        end

        Control -> Warehouse: Thực thi truy vấn (Timeout 30s, Row Limit)
        activate Warehouse
        Warehouse --> Control: Kết quả dữ liệu thô (Rows, Columns, Scanned Bytes)
        deactivate Warehouse

        alt Thực thi thành công
            Control -> Control: audit_node: ghi log kiểm toán
            Control --> Executor: ControlPipelineOutput(is_valid=True, data, columns)
        else Gặp lỗi cú pháp / schema / runtime
            Control -> Control: err_node -> diagnostic (LLM phân tích & gợi ý sửa)
            Control --> Executor: ControlPipelineOutput(is_valid=False, error_context)
            note over Executor: Tự sửa lỗi (Self-Correction Loop attempt <= 3)
        end
        deactivate Control

        Executor --> Analytics: QueryArtifact(status="SUCCESS" / "FAILED", sql, data)
        deactivate Executor
    end

    Analytics -> Analytics: evidence_node: đánh giá tính đầy đủ của dữ liệu
    Analytics -> Analytics: presentation_node: ResponseSynthesizer (2 nhịp)
    Analytics -> Analytics: Data Hydration: rót dữ liệu thật 100% vào KPI & Recharts
    Analytics --> Supervisor: ResponsePackage(direct_answer, artifacts, insights)
    deactivate Analytics
end

Supervisor -> Supervisor: Zero-Hallucination Integrity Guard: kiểm tra tính toàn vẹn
Supervisor --> API: Kết quả tổng hợp cuối cùng
deactivate Supervisor

API --> User: QueryResponse(status="COMPLETED", data, columns, recharts_config, artifacts)
deactivate API
@enduml
```

---

## 4. BẢNG ĐỐI CHIẾU MÃ NGUỒN CÁC MODULE CHỦ CHỐT

| Thành phần | Đường dẫn mã nguồn | Trách nhiệm chính |
|---|---|---|
| **API Endpoints** | [`src/api/routes/query.py`](file:///d:/Text2SQL-AI-Agent/src/api/routes/query.py) | Xử lý `/ask`, `/approve` (resume checkpoint), `/history` |
| **Preflight Gatekeeper** | [`src/agents/preflight_gatekeeper.py`](file:///d:/Text2SQL-AI-Agent/src/agents/preflight_gatekeeper.py) | Phòng thủ 2 tầng: Regex (<0.1ms) + Tier 2 LLM đánh giá mơ hồ |
| **Regex Guardrails** | [`src/agents/guardrails/regex_guard.py`](file:///d:/Text2SQL-AI-Agent/src/agents/guardrails/regex_guard.py) | Chặn DDL/DML, prompt injection thô thiển |
| **Master Supervisor** | [`src/agents/supervisor.py`](file:///d:/Text2SQL-AI-Agent/src/agents/supervisor.py) | DeepAgent Tier 1 điều phối, TodoListMiddleware, Zero-Hallucination Guard |
| **Consultation Subagent** | [`src/agents/consultation.py`](file:///d:/Text2SQL-AI-Agent/src/agents/consultation.py) | Giao tiếp xã giao & giải thích metadata TPC-H không chạy SQL |
| **Analytics Subagent** | [`src/agents/analytics/graph.py`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/graph.py) | LangGraph Subgraph điều phối quy trình phân tích đa nhiệm |
| **Analysis Planner** | [`src/agents/analytics/planner.py`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/planner.py) | Sinh kế hoạch `AnalysisPlan` (1 - 3 nhiệm vụ) |
| **Task Executor** | [`src/agents/analytics/task_executor.py`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/task_executor.py) | Thực thi task với vòng lặp Self-Correction (tối đa 3 lần) |
| **Evidence Analyzer** | [`src/agents/analytics/evidence_analyzer.py`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/evidence_analyzer.py) | Đánh giá tính đầy đủ của dữ liệu thu thập & kích hoạt drill-down |
| **Response Synthesizer** | [`src/agents/analytics/response_synthesizer.py`](file:///d:/Text2SQL-AI-Agent/src/agents/analytics/response_synthesizer.py) | Tổng hợp phản hồi 2 nhịp & Data Hydration 100% dữ liệu thực |
| **Control Pipeline** | [`src/agents/control_pipeline/builder.py`](file:///d:/Text2SQL-AI-Agent/src/agents/control_pipeline/builder.py) | Đồ thị LangGraph an ninh: AST, RBAC, Cost, HITL, Execute, Audit |
| **HITL Risk Evaluator** | [`src/agents/control_pipeline/hitl_evaluator.py`](file:///d:/Text2SQL-AI-Agent/src/agents/control_pipeline/hitl_evaluator.py) | Chấm điểm rủi ro (Cartesian join, quét bảng lớn không partition) |
| **Error Diagnostic** | [`src/agents/control_pipeline/diagnostic.py`](file:///d:/Text2SQL-AI-Agent/src/agents/control_pipeline/diagnostic.py) | LLM phân tích nguyên nhân gốc của lỗi và sinh `suggested_fix` |
| **Warehouse Connector** | [`src/utils/db_connector.py`](file:///d:/Text2SQL-AI-Agent/src/utils/db_connector.py) | DuckDB In-Memory / OLAP Warehouse Adapter (Timeout, Row limits) |
| **Session Tracer** | [`src/utils/session_tracer.py`](file:///d:/Text2SQL-AI-Agent/src/utils/session_tracer.py) | Ghi vết artifact đa phiên độc lập trên virtual filesystem |
| **Audit Logger** | [`src/utils/audit_logger.py`](file:///d:/Text2SQL-AI-Agent/src/utils/audit_logger.py) | Ghi log JSON có cấu trúc phục vụ tuân thủ và audit |
