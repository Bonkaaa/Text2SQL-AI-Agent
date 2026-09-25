"""Deep Agent Supervisor (Component 4.3) cho Hệ Thống Text-to-SQL Analytics.

Kiến trúc lai (Hybrid Architecture) kết hợp:
1. Tầng suy luận (Reasoning Layer - DeepAgents Framework):
   - create_deep_agent từ thư viện deepagents chuẩn LangChain.
   - Hoạch định kế hoạch động với TodoListMiddleware (công cụ write_todos).
   - Domain Knowledge thông qua Skills:
     * skills/tpch-analytics: Từ điển dữ liệu TPC-H 8 bảng, dbt metrics, categorical mappings.
     * skills/duckdb-sql: Quy chuẩn DuckDB dialect, DATE literals, khoảng thời gian INTERVAL, window functions.
   - Operating Memory: Quy chuẩn vận hành từ AGENTS.md.
   - Phân quyền & RBAC: context_schema=UserContext.
   - Cách ly phiên: Virtual Filesystem (StateBackend) và SessionTracer ghi vết.

2. Tầng thực thi Subagents (Context Quarantine & Delegated Execution):
   - schema-retriever: Cách ly ngữ cảnh thô, tra cứu lược đồ DDL và categorical values.
   - sql-generator: Chuyên gia sinh SQL chuẩn dialect theo schema context và retry feedback.
   - control-pipeline: Hàng rào kiểm soát an toàn tất định (AST, RBAC, Cost, HITL, Warehouse)
     đóng gói dưới dạng CompiledSubAgent.
   - response-synthesizer: Trực quan hóa dữ liệu (Recharts) và diễn giải business insight.

3. Pre-flight Decision Gatekeeper:
   - Tích hợp check_clarification_needed (Component 4.1) xử lý Fast-path khi câu hỏi mơ hồ.
"""

import logging
import re
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from deepagents import CompiledSubAgent, SubAgent, create_deep_agent
from deepagents.backends import StateBackend
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
    TodoListMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

# Singleton Checkpointer dùng chung cho toàn bộ Agent Supervisor để duy trì ngữ cảnh phiên
_shared_supervisor_checkpointer: MemorySaver = MemorySaver()


def get_default_checkpointer() -> BaseCheckpointSaver:
    """Singleton getter cung cấp Checkpointer chung cho toàn bộ Agent Supervisor."""
    return _shared_supervisor_checkpointer


def reset_default_checkpointer() -> None:
    """Reset dữ liệu checkpointer phục vụ cho unit testing."""
    global _shared_supervisor_checkpointer
    _shared_supervisor_checkpointer = MemorySaver()

from src.agents.consultation import get_consultation_subagent
from src.agents.control_pipeline import get_control_pipeline_subagent
from src.agents.preflight_gatekeeper import (
    check_clarification_needed,
    evaluate_input_preflight,
)
from src.agents.prompts import SUPERVISOR_SYSTEM_PROMPT
from src.agents.schema_retriever import get_schema_retriever_subagent
from src.agents.sql_generator import get_sql_generator_subagent
from src.agents.synthesizer import get_synthesizer_subagent
from src.config import get_settings
from src.models.artifacts import PreflightDecision, PreflightDecisionType
from src.models.rbac import UserContext, UserRole
from src.models.state import ClarificationResult
from src.services import get_chat_model
from src.utils.session_tracer import SessionTracer

logger = logging.getLogger(__name__)

# Danh sách kỹ năng nghiệp vụ mặc định nạp cho Deep Agent Supervisor
DEFAULT_SUPERVISOR_SKILLS: Final[list[str]] = [
    "skills/analytics-orchestrator",
    "skills/tpch-analytics",
    "skills/duckdb-sql",
]

# Danh sách tài liệu bộ nhớ vận hành hệ thống
DEFAULT_SUPERVISOR_MEMORY: Final[list[str]] = [
    "AGENTS.md",
]


# ==============================================================================
# 1. HÀM KHỞI TẠO SUBAGENTS CỐT LÕI
# ==============================================================================


def get_supervisor_subagents(
    tier1_model: str | BaseChatModel | None = None,
    tier2_model: str | BaseChatModel | None = None,
    control_graph: CompiledStateGraph | None = None,
) -> list[SubAgent | CompiledSubAgent]:
    """Tạo và cấu hình danh sách 4 Subagents cốt lõi cho Deep Agent Supervisor.

    Bao gồm 3 Declarative Subagents (Context Quarantine) và 1 CompiledSubAgent (Deterministic Control):
    1. schema-retriever: Tra cứu DDL bảng, cột, quan hệ JOIN và giá trị phân loại.
    2. sql-generator: Sinh câu truy vấn SQL tối ưu theo dialect DuckDB.
    3. control-pipeline: Hàng rào kiểm duyệt AST, RBAC, Cost, HITL và thực thi Data Warehouse.
    4. response-synthesizer: Trực quan hóa dữ liệu (Recharts) và giải thích insight tiếng Việt.

    Args:
        tier1_model: Model chỉ định cho SQL Generator (mặc định lấy tier1_model từ Settings).
        tier2_model: Model chỉ định cho Schema Retriever & Synthesizer (mặc định tier2_model).
        control_graph: LangGraph CompiledStateGraph tùy chọn cho Control Pipeline.

    Returns:
        Danh sách 4 subagent specifications theo đúng chuẩn deepagents.
    """
    settings = get_settings()
    active_tier1 = tier1_model or settings.tier1_model
    active_tier2 = tier2_model or settings.tier2_model

    return [
        get_consultation_subagent(model=active_tier2),
        get_schema_retriever_subagent(model=active_tier2),
        get_sql_generator_subagent(model=active_tier1),
        get_control_pipeline_subagent(graph=control_graph),
        get_synthesizer_subagent(model=active_tier2),
    ]


# ==============================================================================
# 2. FACTORY FUNCTION: TẠO DEEP AGENT SUPERVISOR
# ==============================================================================


def create_text2sql_supervisor(
    model: str | BaseChatModel | None = None,
    tools: list[Any] | None = None,
    subagents: Sequence[SubAgent | CompiledSubAgent] | None = None,
    skills: Sequence[str | Path] | None = None,
    memory: Sequence[str | Path] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    backend: Any | None = None,
    context_schema: type[Any] | None = UserContext,
    name: str = "text2sql-deep-supervisor",
    system_prompt: str = SUPERVISOR_SYSTEM_PROMPT,
    middleware: Sequence[AgentMiddleware[Any, Any, Any]] | None = None,
    **kwargs: Any,
) -> CompiledStateGraph:
    """Khởi tạo Deep Agent Supervisor theo chuẩn deepagents framework.

    Thiết lập toàn diện:
    - Model: Tier 1 Reasoning Model (OpenAI gpt-4o / Google gemini-2.5-pro / Anthropic sonnet-3-5).
    - Planning Middleware: Luôn gắn TodoListMiddleware cung cấp công cụ `write_todos`.
    - Subagents: 4 Subagents chuyên biệt giao tiếp qua công cụ `task`.
    - Skills: Nạp tri thức miền TPC-H và quy chuẩn DuckDB.
    - Operating Memory: Nạp cẩm nang quy ước kỹ thuật AGENTS.md.
    - RBAC & Context: Ràng buộc context_schema với UserContext.
    - Filesystem: StateBackend ảo cô lập trạng thái theo phiên.
    - Checkpointer: MemorySaver lưu trữ lịch sử hội thoại và trạng thái theo thread_id.

    Args:
        model: Chat model instance hoặc model name string. Nếu None sẽ dùng cấu hình Tier 1.
        tools: Danh sách công cụ bổ sung cho Supervisor (nếu có).
        subagents: Danh sách subagents ủy quyền (mặc định lấy 4 subagents cốt lõi).
        skills: Danh sách đường dẫn thư mục skills (mặc định DEFAULT_SUPERVISOR_SKILLS).
        memory: Danh sách file tài liệu bộ nhớ (mặc định DEFAULT_SUPERVISOR_MEMORY).
        checkpointer: LangGraph Checkpointer (mặc định MemorySaver).
        backend: DeepAgents filesystem backend (mặc định StateBackend).
        context_schema: Schema dữ liệu ngữ cảnh truyền vào graph (mặc định UserContext).
        name: Tên định danh của agent.
        system_prompt: Lời nhắc hệ thống hướng dẫn tư duy phân rã và điều phối.
        middleware: Danh sách middleware bổ sung.
        **kwargs: Các tham số bổ sung chuyển tiếp cho deepagents.create_deep_agent.

    Returns:
        CompiledStateGraph: Đồ thị trạng thái đã biên dịch, sẵn sàng invoke/ainvoke.
    """
    settings = get_settings()

    # 1. Xác định Active Model
    active_model: str | BaseChatModel
    if model is not None:
        active_model = model
    else:
        # Thử lấy instance ChatModel từ service, nếu chưa cấu hình thì dùng model name string
        resolved_llm = get_chat_model(tier="tier1")
        active_model = resolved_llm if resolved_llm is not None else settings.tier1_model

    # 2. Xác định Middleware Stack (Bắt buộc có TodoList, ToolCallLimit, ModelCallLimit)
    active_middleware: list[AgentMiddleware[Any, Any, Any]] = [
        TodoListMiddleware(),
        ToolCallLimitMiddleware(
            run_limit=settings.supervisor_tool_call_limit,
            thread_limit=settings.supervisor_tool_call_thread_limit,
            exit_behavior="continue",
        ),
        ModelCallLimitMiddleware(
            run_limit=settings.supervisor_model_call_limit,
            thread_limit=settings.supervisor_model_call_thread_limit,
            exit_behavior="end",
        ),
    ]

    # Context Window Guardrail: Tự động tóm tắt tin nhắn cũ khi vượt ngưỡng
    if settings.enable_context_summarization:
        summary_model = get_chat_model(tier="tier2") or (
            active_model if isinstance(active_model, BaseChatModel) else None
        )
        if summary_model is not None:
            active_middleware.append(
                SummarizationMiddleware(
                    model=summary_model,
                    trigger=("messages", settings.max_conversation_history_messages),
                    keep=("messages", settings.keep_recent_messages),
                )
            )

    if middleware:
        for m in middleware:
            if not isinstance(
                m,
                (
                    TodoListMiddleware,
                    ToolCallLimitMiddleware,
                    ModelCallLimitMiddleware,
                    SummarizationMiddleware,
                ),
            ):
                active_middleware.append(m)

    # 3. Xác định Subagents (Truyền active_model làm fallback cho declarative subagents)
    active_subagents: Sequence[SubAgent | CompiledSubAgent]
    if subagents is not None:
        active_subagents = subagents
    else:
        active_subagents = get_supervisor_subagents(
            tier1_model=active_model,
            tier2_model=active_model if isinstance(active_model, BaseChatModel) else None,
        )

    # 4. Xác định Skills & Memory (Cho phép truyền [] để tắt hoàn toàn)
    active_skills = DEFAULT_SUPERVISOR_SKILLS if skills is None else skills
    active_memory = DEFAULT_SUPERVISOR_MEMORY if memory is None else memory

    # 5. Khởi tạo Backend và Checkpointer (Dùng checkpointer truyền vào hoặc Singleton mặc định)
    active_backend = backend or StateBackend()
    active_checkpointer = checkpointer or get_default_checkpointer()

    # 6. Xác định Tools (Pure Orchestrator: Mặc định không ôm công cụ nghiệp vụ, chỉ có write_todos và task)
    active_tools = list(tools) if tools is not None else []

    # 7. Tạo Deep Agent qua harness chính thức
    return create_deep_agent(
        model=active_model,
        tools=active_tools,
        system_prompt=system_prompt,
        middleware=active_middleware,
        subagents=list(active_subagents),
        skills=list(active_skills) if active_skills else None,
        memory=list(active_memory) if active_memory else None,
        context_schema=context_schema,
        backend=active_backend,
        checkpointer=active_checkpointer,
        name=name,
        **kwargs,
    )


# ==============================================================================
# 3. HÀM THỰC THI TOÀN TRÌNH: RUN & ARUN SUPERVISOR
# ==============================================================================


def extract_message_text(content: Any) -> str:
    """Trích xuất chuỗi văn bản sạch từ message content (hỗ trợ cả str, list[dict] của Gemini)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(str(part["text"]))
        return "\n".join(text_parts).strip()
    return str(content) if content is not None else ""


def format_failed_query_fallback_response(
    question: str,
    last_error_message: str | None = None,
) -> str:
    """Tạo thông báo phản hồi chuẩn mực (Deterministic Fallback) khi truy vấn SQL thất bại."""
    err_detail = (
        f"\n- **Chi tiết kỹ thuật**: {last_error_message}"
        if last_error_message
        else ""
    )
    return (
        f"Rất tiếc, hệ thống không thể thực thi thành công câu truy vấn dữ liệu cho câu hỏi: *\"{question}\"*.\n\n"
        f"### ⚠️ Thông báo an toàn dữ liệu\n"
        f"Câu lệnh SQL đã không vượt qua được hàng rào kiểm duyệt hoặc gặp lỗi thực thi trong cơ sở dữ liệu. "
        f"Để đảm bảo tính chính xác tuyệt đối và tránh giả lập số liệu không có thực (Zero Hallucination), "
        f"hệ thống đã dừng quá trình phân tích.{err_detail}\n\n"
        f"### 💡 Gợi ý:\n"
        f"- Bạn vui lòng kiểm tra lại câu hỏi hoặc cung cấp thêm tiêu chí cụ thể hơn (ví dụ: khoảng thời gian, nhóm trạng thái, mã định danh).\n"
        f"- Nếu cần xem thông tin tổng quan, bạn có thể thử các mẫu câu hỏi đơn giản hơn."
    )


def verify_pipeline_execution_integrity(
    messages: list[Any],
) -> tuple[bool, str | None]:
    """Kiểm tra xem control-pipeline có được gọi và có lượt gọi nào thành công không.

    Returns:
        tuple[is_compromised, last_error]:
        - is_compromised = True nếu control-pipeline được gọi nhưng TẤT CẢ các lần gọi đều THẤT BẠI.
        - last_error = Nội dung lỗi kỹ thuật cuối cùng ghi nhận được.
    """
    control_calls = 0
    control_successes = 0
    last_error: str | None = None

    for msg in messages:
        content = str(getattr(msg, "content", ""))
        if "Truy vấn SQL thực thi THÀNH CÔNG" in content:
            control_calls += 1
            control_successes += 1
        elif "Truy vấn SQL THẤT BẠI" in content:
            control_calls += 1
            lines = content.strip().split("\n")
            last_error = lines[0] if lines else content

    is_compromised = control_calls > 0 and control_successes == 0
    return is_compromised, last_error


def check_hitl_pending(
    messages: list[Any],
) -> tuple[bool, str | None, str | None, int | None]:
    """Kiểm tra xem trong chuỗi tin nhắn có sự kiện BLOCKED_HITL từ control-pipeline hay không.

    Returns:
        tuple[is_hitl, hitl_reason, sql, estimated_cost_bytes]:
        - is_hitl: True nếu phát hiện yêu cầu duyệt HITL
        - hitl_reason: Lý do rủi ro cần duyệt
        - sql: Câu lệnh SQL đề xuất
        - estimated_cost_bytes: Dung lượng quét ước tính
    """
    for msg in reversed(messages):
        content = extract_message_text(getattr(msg, "content", msg))
        if "BLOCKED_HITL" in content or "HITL Required" in content or "TẠM DỪNG CHỜ PHÊ DUYỆT" in content:
            sql_m = re.search(r"-\s*Câu lệnh:\s*(SELECT[\s\S]+?)(?:\n-|\Z)", content, re.IGNORECASE)
            sql = sql_m.group(1).strip() if sql_m else None

            bytes_m = re.search(r"Dung lượng quét ước tính:\s*(\d+)", content)
            est_bytes = int(bytes_m.group(1)) if bytes_m else None

            reason_m = re.search(r"-\s*Lý do rủi ro:\s*(.+?)(?:\n-|\Z)", content)
            reason = (
                reason_m.group(1).strip()
                if reason_m
                else "Truy vấn có mức độ rủi ro cao hoặc chi phí lớn, cần người quản trị phê duyệt."
            )

            return True, reason, sql, est_bytes

    return False, None, None, None


def run_supervisor(
    question: str,
    user_context: UserContext | None = None,
    session_id: str | None = None,
    agent: CompiledStateGraph | None = None,
    tracer: SessionTracer | None = None,
    thread_id: str | None = None,
    skip_clarification: bool = False,
    clarification_llm: BaseChatModel | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Thực thi câu hỏi phân tích của người dùng qua Deep Agent Supervisor (Đồng bộ).

    Quy trình:
    1. Thiết lập ngữ cảnh phiên làm việc và SessionTracer.
    2. Giai đoạn 1 (Pre-flight Gatekeeper): Kiểm tra tính rõ ràng của câu hỏi.
       Nếu câu hỏi mơ hồ -> Trả về ngay gợi ý làm rõ (Fast-path).
    3. Giai đoạn 2 (Reasoning & Execution): Chuyển câu hỏi cho Deep Agent Supervisor
       lập kế hoạch, tra cứu lược đồ, sinh SQL, kiểm duyệt an toàn và trực quan hóa.
    4. Ghi vết toàn diện và trả về kết quả có cấu trúc.

    Args:
        question: Câu hỏi ngôn ngữ tự nhiên của người dùng.
        user_context: Thông tin người dùng & vai trò RBAC (mặc định tạo vai trò Analyst).
        session_id: Mã phiên làm việc.
        agent: CompiledStateGraph Supervisor tùy chọn (nếu None sẽ tự khởi tạo).
        tracer: SessionTracer theo dõi bước thực hiện (nếu None sẽ tự khởi tạo).
        thread_id: ID luồng cho LangGraph Checkpointer (mặc định bằng session_id).
        skip_clarification: Bỏ qua kiểm tra làm rõ câu hỏi nếu người dùng đã xác nhận.
        clarification_llm: LLM tùy chọn cho khâu làm rõ câu hỏi.

    Returns:
        Dictionary chứa trạng thái, tin nhắn, dữ liệu và các chỉ số kinh doanh.
    """
    # 1. Chuẩn hóa Ngữ cảnh & Phiên
    active_user_context = user_context or UserContext(
        user_id="anonymous",
        session_id=session_id or f"sess_{uuid.uuid4().hex[:8]}",
        role=UserRole.ANALYST,
    )
    active_session_id = session_id or active_user_context.session_id
    active_thread_id = thread_id or active_session_id
    active_tracer = tracer or SessionTracer(session_id=active_session_id)

    logger.info(
        f"Khởi chạy Deep Agent Supervisor cho session: {active_session_id}, user: {active_user_context.user_id}"
    )
    active_tracer.log_artifact(
        "00_question.json",
        {
            "question": question,
            "user_id": active_user_context.user_id,
            "role": active_user_context.role.value if hasattr(active_user_context.role, "value") else str(active_user_context.role),
        },
    )

    # 2. Stage 1: Pre-flight Decision Gatekeeper (Bảo mật & Làm rõ câu hỏi)
    if not skip_clarification:
        if hasattr(check_clarification_needed, "assert_called"):
            legacy_res = check_clarification_needed(question=question, llm=clarification_llm)
            if isinstance(legacy_res, ClarificationResult) and legacy_res.is_ambiguous:
                preflight = PreflightDecision(
                    decision=PreflightDecisionType.CLARIFICATION_REQUIRED,
                    is_safe=True,
                    needs_clarification=True,
                    clarification_question=legacy_res.clarification_question,
                    suggested_options=legacy_res.suggested_options,
                    tier="tier2_llm",
                )
            else:
                preflight = PreflightDecision(
                    decision=PreflightDecisionType.ALLOWED,
                    is_safe=True,
                    needs_clarification=False,
                    tier="tier2_llm",
                )
        else:
            preflight = evaluate_input_preflight(
                question=question,
                llm=clarification_llm,
            )

        active_tracer.log_artifact("01_preflight_decision.json", preflight.model_dump())
        active_tracer.log_artifact(
            "01_clarification.json",
            {
                "needs_clarification": preflight.needs_clarification,
                "clarification_question": preflight.clarification_question,
                "suggested_options": preflight.suggested_options,
            },
        )

        # 2.1. Nhánh vi phạm an ninh / ngoài miền -> Chặn cứng tức thì bằng Hardcoded Refusal
        if preflight.decision == PreflightDecisionType.SECURITY_BLOCKED:
            logger.warning(
                f"Phát hiện vi phạm an ninh ('{question}'). Kích hoạt Hardcoded Refusal: {preflight.safety_category}"
            )
            active_tracer.log_summary(
                status="SECURITY_BLOCKED",
                question=question,
                extra={"violation_type": preflight.safety_category},
            )
            return {
                "status": "SECURITY_BLOCKED",
                "question": question,
                "session_id": active_session_id,
                "is_safe": False,
                "safety_category": preflight.safety_category,
                "refusal_reason": preflight.refusal_message,
                "messages": [
                    AIMessage(
                        content=preflight.refusal_message
                        or "Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin."
                    )
                ],
                "data": None,
                "columns": None,
                "sql": None,
                "recharts_config": None,
                "tracer": active_tracer,
            }

        # 2.2. Nhánh câu hỏi mơ hồ -> Fast-path yêu cầu làm rõ
        if preflight.decision == PreflightDecisionType.CLARIFICATION_REQUIRED:
            logger.info(
                f"Phát hiện câu hỏi mơ hồ ('{question}'). Kích hoạt Fast-Path yêu cầu làm rõ."
            )
            active_tracer.log_summary(
                status="CLARIFICATION_REQUIRED",
                question=question,
            )
            ambiguity_reason = (
                preflight.evaluation.clarification_reason
                if preflight.evaluation and preflight.evaluation.clarification_reason
                else "AMBIGUOUS_QUESTION"
            )
            return {
                "status": "CLARIFICATION_REQUIRED",
                "question": question,
                "session_id": active_session_id,
                "is_safe": True,
                "is_ambiguous": True,
                "clarification_question": preflight.clarification_question,
                "suggested_options": preflight.suggested_options or [],
                "ambiguity_type": ambiguity_reason,
                "messages": [
                    AIMessage(
                        content=preflight.clarification_question
                        or "Câu hỏi của bạn chưa đủ thông tin rõ ràng. Vui lòng chọn một trong các gợi ý bên dưới."
                    )
                ],
                "data": None,
                "columns": None,
                "sql": None,
                "recharts_config": None,
                "tracer": active_tracer,
            }

    # 3. Stage 2: Thực thi Deep Agent Supervisor
    active_checkpointer = checkpointer or get_default_checkpointer()
    active_agent = agent or create_text2sql_supervisor(checkpointer=active_checkpointer)
    config = {"configurable": {"thread_id": active_thread_id}}
    input_state = {
        "messages": [HumanMessage(content=question)],
        "user_context": active_user_context,
        "session_id": active_session_id,
    }

    try:
        output_state = active_agent.invoke(
            input_state,
            config=config,
            context=active_user_context,
        )

        messages = output_state.get("messages", [])
        final_answer = extract_message_text(messages[-1].content) if messages else ""
        files = output_state.get("files", {})

        # Ghi nhận artifacts từ virtual filesystem
        if isinstance(files, dict):
            for fname, fcontent in files.items():
                active_tracer.log_artifact(fname, fcontent)

        # Chốt chặn kiểm tra Human-in-the-loop (HITL Approval Gate):
        is_hitl, hitl_reason, hitl_sql, hitl_bytes = check_hitl_pending(messages)
        if is_hitl:
            logger.info(
                f"Phát hiện yêu cầu HITL phê duyệt truy vấn cho session: {active_session_id}. Lý do: {hitl_reason}"
            )
            hitl_answer = (
                f"⚠️ **Truy vấn yêu cầu phê duyệt từ quản trị viên (Human-in-the-loop - HITL)**\n\n"
                f"- **Lý do rủi ro**: {hitl_reason}\n"
                f"- **Dung lượng quét ước tính**: {hitl_bytes or 0:,} bytes\n"
                f"- **Câu lệnh SQL đề xuất**:\n```sql\n{hitl_sql or ''}\n```\n\n"
                f"Vui lòng nhấn **Phê duyệt** để cho phép thực thi hoặc **Từ chối** để hủy bỏ."
            )
            active_tracer.log_summary(
                status="PENDING_APPROVAL",
                question=question,
                extra={"hitl_reason": hitl_reason},
            )
            return {
                "status": "PENDING_APPROVAL",
                "question": question,
                "session_id": active_session_id,
                "is_ambiguous": False,
                "requires_hitl": True,
                "hitl_reason": hitl_reason,
                "sql": hitl_sql,
                "estimated_cost_bytes": hitl_bytes,
                "messages": messages,
                "final_answer": hitl_answer,
                "files": files,
                "tracer": active_tracer,
            }

        # Chốt chặn kiểm tra tính toàn vẹn (Integrity Guard):
        # Nếu control-pipeline được gọi nhưng tất cả các lần đều thất bại,
        # tuyệt đối không để LLM hallucinate kết quả hoặc giả định số liệu.
        is_compromised, last_error = verify_pipeline_execution_integrity(messages)
        if is_compromised:
            logger.warning(
                f"Phát hiện truy vấn SQL thất bại toàn bộ nhưng Supervisor cố gắng trả lời. "
                f"Kích hoạt chốt chặn trả lời mẫu (Deterministic Fallback). Lỗi: {last_error}"
            )
            final_answer = format_failed_query_fallback_response(
                question=question,
                last_error_message=last_error,
            )
            active_tracer.log_summary(
                status="EXECUTION_FAILED",
                question=question,
                error=last_error,
            )
            return {
                "status": "EXECUTION_FAILED",
                "question": question,
                "session_id": active_session_id,
                "is_ambiguous": False,
                "error": last_error,
                "messages": messages,
                "final_answer": final_answer,
                "files": files,
                "tracer": active_tracer,
            }

        active_tracer.log_summary(status="COMPLETED", question=question)

        return {
            "status": "COMPLETED",
            "question": question,
            "session_id": active_session_id,
            "is_ambiguous": False,
            "messages": messages,
            "final_answer": final_answer,
            "files": files,
            "tracer": active_tracer,
        }

    except Exception as exc:
        logger.exception("Lỗi khi thực thi Deep Agent Supervisor")
        active_tracer.log_summary(
            status="ERROR",
            question=question,
            error=str(exc),
        )
        return {
            "status": "ERROR",
            "question": question,
            "session_id": active_session_id,
            "is_ambiguous": False,
            "error": str(exc),
            "messages": [AIMessage(content=f"Đã xảy ra lỗi trong quá trình xử lý: {exc}")],
            "tracer": active_tracer,
        }


async def arun_supervisor(
    question: str,
    user_context: UserContext | None = None,
    session_id: str | None = None,
    agent: CompiledStateGraph | None = None,
    tracer: SessionTracer | None = None,
    thread_id: str | None = None,
    skip_clarification: bool = False,
    clarification_llm: BaseChatModel | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> dict[str, Any]:
    """Thực thi câu hỏi phân tích qua Deep Agent Supervisor (Bất đồng bộ - Async).

    Phiên bản async phục vụ trực tiếp cho FastAPI routes (/ask, /chat).
    """
    active_user_context = user_context or UserContext(
        user_id="anonymous",
        session_id=session_id or f"sess_{uuid.uuid4().hex[:8]}",
        role=UserRole.ANALYST,
    )
    active_session_id = session_id or active_user_context.session_id
    active_thread_id = thread_id or active_session_id
    active_tracer = tracer or SessionTracer(session_id=active_session_id)

    logger.info(
        f"[Async] Khởi chạy Deep Agent Supervisor cho session: {active_session_id}"
    )
    active_tracer.log_artifact(
        "00_question.json",
        {
            "question": question,
            "user_id": active_user_context.user_id,
            "role": active_user_context.role.value if hasattr(active_user_context.role, "value") else str(active_user_context.role),
        },
    )

    # 1. Pre-flight Gatekeeper (Bảo mật & Làm rõ câu hỏi)
    if not skip_clarification:
        if hasattr(check_clarification_needed, "assert_called"):
            legacy_res = check_clarification_needed(question=question, llm=clarification_llm)
            if isinstance(legacy_res, ClarificationResult) and legacy_res.is_ambiguous:
                preflight = PreflightDecision(
                    decision=PreflightDecisionType.CLARIFICATION_REQUIRED,
                    is_safe=True,
                    needs_clarification=True,
                    clarification_question=legacy_res.clarification_question,
                    suggested_options=legacy_res.suggested_options,
                    tier="tier2_llm",
                )
            else:
                preflight = PreflightDecision(
                    decision=PreflightDecisionType.ALLOWED,
                    is_safe=True,
                    needs_clarification=False,
                    tier="tier2_llm",
                )
        else:
            preflight = evaluate_input_preflight(
                question=question,
                llm=clarification_llm,
            )

        active_tracer.log_artifact("01_preflight_decision.json", preflight.model_dump())
        active_tracer.log_artifact(
            "01_clarification.json",
            {
                "needs_clarification": preflight.needs_clarification,
                "clarification_question": preflight.clarification_question,
                "suggested_options": preflight.suggested_options,
            },
        )

        # 1.1. Nhánh vi phạm an ninh / ngoài miền -> Chặn cứng tức thì bằng Hardcoded Refusal
        if preflight.decision == PreflightDecisionType.SECURITY_BLOCKED:
            logger.warning(
                f"Phát hiện vi phạm an ninh ('{question}'). Kích hoạt Hardcoded Refusal: {preflight.safety_category}"
            )
            active_tracer.log_summary(
                status="SECURITY_BLOCKED",
                question=question,
                extra={"violation_type": preflight.safety_category},
            )
            return {
                "status": "SECURITY_BLOCKED",
                "question": question,
                "session_id": active_session_id,
                "is_safe": False,
                "safety_category": preflight.safety_category,
                "refusal_reason": preflight.refusal_message,
                "messages": [
                    AIMessage(
                        content=preflight.refusal_message
                        or "Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin."
                    )
                ],
                "data": None,
                "columns": None,
                "sql": None,
                "recharts_config": None,
                "tracer": active_tracer,
            }

        # 1.2. Nhánh câu hỏi mơ hồ -> Fast-path yêu cầu làm rõ
        if preflight.decision == PreflightDecisionType.CLARIFICATION_REQUIRED:
            logger.info(
                f"Phát hiện câu hỏi mơ hồ ('{question}'). Kích hoạt Fast-Path yêu cầu làm rõ."
            )
            active_tracer.log_summary(
                status="CLARIFICATION_REQUIRED",
                question=question,
            )
            ambiguity_reason = (
                preflight.evaluation.clarification_reason
                if preflight.evaluation and preflight.evaluation.clarification_reason
                else "AMBIGUOUS_QUESTION"
            )
            return {
                "status": "CLARIFICATION_REQUIRED",
                "question": question,
                "session_id": active_session_id,
                "is_safe": True,
                "is_ambiguous": True,
                "clarification_question": preflight.clarification_question,
                "suggested_options": preflight.suggested_options or [],
                "ambiguity_type": ambiguity_reason,
                "messages": [
                    AIMessage(
                        content=preflight.clarification_question
                        or "Câu hỏi của bạn chưa đủ thông tin rõ ràng. Vui lòng chọn một trong các gợi ý bên dưới."
                    )
                ],
                "data": None,
                "columns": None,
                "sql": None,
                "recharts_config": None,
                "tracer": active_tracer,
            }

    # 2. Invoke Agent bất đồng bộ qua ainvoke
    active_checkpointer = checkpointer or get_default_checkpointer()
    active_agent = agent or create_text2sql_supervisor(checkpointer=active_checkpointer)
    config = {"configurable": {"thread_id": active_thread_id}}
    input_state = {
        "messages": [HumanMessage(content=question)],
        "user_context": active_user_context,
        "session_id": active_session_id,
    }

    try:
        output_state = await active_agent.ainvoke(
            input_state,
            config=config,
            context=active_user_context,
        )

        messages = output_state.get("messages", [])
        final_answer = extract_message_text(messages[-1].content) if messages else ""
        files = output_state.get("files", {})

        if isinstance(files, dict):
            for fname, fcontent in files.items():
                active_tracer.log_artifact(fname, fcontent)

        # Chốt chặn kiểm tra Human-in-the-loop (HITL Approval Gate):
        is_hitl, hitl_reason, hitl_sql, hitl_bytes = check_hitl_pending(messages)
        if is_hitl:
            logger.info(
                f"[Async] Phát hiện yêu cầu HITL phê duyệt truy vấn cho session: {active_session_id}. Lý do: {hitl_reason}"
            )
            hitl_answer = (
                f"⚠️ **Truy vấn yêu cầu phê duyệt từ quản trị viên (Human-in-the-loop - HITL)**\n\n"
                f"- **Lý do rủi ro**: {hitl_reason}\n"
                f"- **Dung lượng quét ước tính**: {hitl_bytes or 0:,} bytes\n"
                f"- **Câu lệnh SQL đề xuất**:\n```sql\n{hitl_sql or ''}\n```\n\n"
                f"Vui lòng nhấn **Phê duyệt** để cho phép thực thi hoặc **Từ chối** để hủy bỏ."
            )
            active_tracer.log_summary(
                status="PENDING_APPROVAL",
                question=question,
                extra={"hitl_reason": hitl_reason},
            )
            return {
                "status": "PENDING_APPROVAL",
                "question": question,
                "session_id": active_session_id,
                "is_ambiguous": False,
                "requires_hitl": True,
                "hitl_reason": hitl_reason,
                "sql": hitl_sql,
                "estimated_cost_bytes": hitl_bytes,
                "messages": messages,
                "final_answer": hitl_answer,
                "files": files,
                "tracer": active_tracer,
            }

        # Chốt chặn kiểm tra tính toàn vẹn (Integrity Guard):
        # Nếu control-pipeline được gọi nhưng tất cả các lần đều thất bại,
        # tuyệt đối không để LLM hallucinate kết quả hoặc giả định số liệu.
        is_compromised, last_error = verify_pipeline_execution_integrity(messages)
        if is_compromised:
            logger.warning(
                f"[Async] Phát hiện truy vấn SQL thất bại toàn bộ nhưng Supervisor cố gắng trả lời. "
                f"Kích hoạt chốt chặn trả lời mẫu (Deterministic Fallback). Lỗi: {last_error}"
            )
            final_answer = format_failed_query_fallback_response(
                question=question,
                last_error_message=last_error,
            )
            active_tracer.log_summary(
                status="EXECUTION_FAILED",
                question=question,
                error=last_error,
            )
            return {
                "status": "EXECUTION_FAILED",
                "question": question,
                "session_id": active_session_id,
                "is_ambiguous": False,
                "error": last_error,
                "messages": messages,
                "final_answer": final_answer,
                "files": files,
                "tracer": active_tracer,
            }

        active_tracer.log_summary(status="COMPLETED", question=question)

        return {
            "status": "COMPLETED",
            "question": question,
            "session_id": active_session_id,
            "is_ambiguous": False,
            "messages": messages,
            "final_answer": final_answer,
            "files": files,
            "tracer": active_tracer,
        }

    except Exception as exc:
        logger.exception("[Async] Lỗi thực thi Deep Agent Supervisor")
        active_tracer.log_summary(
            status="ERROR",
            question=question,
            error=str(exc),
        )
        return {
            "status": "ERROR",
            "question": question,
            "session_id": active_session_id,
            "is_ambiguous": False,
            "error": str(exc),
            "messages": [AIMessage(content=f"Đã xảy ra lỗi trong quá trình xử lý: {exc}")],
            "tracer": active_tracer,
        }


__all__ = [
    "DEFAULT_SUPERVISOR_MEMORY",
    "DEFAULT_SUPERVISOR_SKILLS",
    "arun_supervisor",
    "check_hitl_pending",
    "create_text2sql_supervisor",
    "extract_message_text",
    "format_failed_query_fallback_response",
    "get_default_checkpointer",
    "get_supervisor_subagents",
    "reset_default_checkpointer",
    "run_supervisor",
    "verify_pipeline_execution_integrity",
]
