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
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

from deepagents import CompiledSubAgent, SubAgent, create_deep_agent
from deepagents.backends import StateBackend
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    TodoListMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from src.agents.clarification import check_clarification_needed
from src.agents.control_pipeline import get_control_pipeline_subagent
from src.agents.prompts import SUPERVISOR_SYSTEM_PROMPT
from src.agents.schema_retriever import get_schema_retriever_subagent
from src.agents.sql_generator import get_sql_generator_subagent
from src.agents.synthesizer import get_synthesizer_subagent
from src.config import get_settings
from src.models.rbac import UserContext, UserRole
from src.models.state import ClarificationResult
from src.services import get_chat_model
from src.utils.session_tracer import SessionTracer

logger = logging.getLogger(__name__)

# Danh sách kỹ năng nghiệp vụ mặc định nạp cho Deep Agent Supervisor
DEFAULT_SUPERVISOR_SKILLS: Final[list[str]] = [
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
    if middleware:
        for m in middleware:
            if not isinstance(
                m,
                (
                    TodoListMiddleware,
                    ToolCallLimitMiddleware,
                    ModelCallLimitMiddleware,
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

    # 5. Khởi tạo Backend và Checkpointer
    active_backend = backend or StateBackend()
    active_checkpointer = checkpointer or MemorySaver()

    # 6. Tạo Deep Agent qua harness chính thức
    return create_deep_agent(
        model=active_model,
        tools=tools,
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


def run_supervisor(
    question: str,
    user_context: UserContext | None = None,
    session_id: str | None = None,
    agent: CompiledStateGraph | None = None,
    tracer: SessionTracer | None = None,
    thread_id: str | None = None,
    skip_clarification: bool = False,
    clarification_llm: BaseChatModel | None = None,
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

    # 2. Stage 1: Pre-flight Decision Gatekeeper (Làm rõ câu hỏi mơ hồ)
    if not skip_clarification:
        clarification: ClarificationResult = check_clarification_needed(
            question=question,
            llm=clarification_llm,
        )
        active_tracer.log_artifact("01_clarification.json", clarification)

        if clarification.is_ambiguous:
            logger.info(
                f"Phát hiện câu hỏi mơ hồ ('{question}'). Kích hoạt Fast-Path yêu cầu làm rõ."
            )
            active_tracer.log_summary(
                status="CLARIFICATION_REQUIRED",
                question=question,
            )
            return {
                "status": "CLARIFICATION_REQUIRED",
                "question": question,
                "session_id": active_session_id,
                "is_ambiguous": True,
                "clarification_question": clarification.clarification_question,
                "suggested_options": clarification.suggested_options or [],
                "ambiguity_type": clarification.reason or "AMBIGUOUS_QUESTION",
                "messages": [
                    AIMessage(
                        content=clarification.clarification_question
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
    active_agent = agent or create_text2sql_supervisor()
    config = {"configurable": {"thread_id": active_thread_id}}
    input_state = {
        "messages": [HumanMessage(content=question)],
    }

    try:
        output_state = active_agent.invoke(
            input_state,
            config=config,
            context=active_user_context,
        )

        messages = output_state.get("messages", [])
        final_answer = messages[-1].content if messages else ""
        files = output_state.get("files", {})

        # Ghi nhận artifacts từ virtual filesystem
        if isinstance(files, dict):
            for fname, fcontent in files.items():
                active_tracer.log_artifact(fname, fcontent)

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

    # 1. Pre-flight Gatekeeper
    if not skip_clarification:
        clarification: ClarificationResult = check_clarification_needed(
            question=question,
            llm=clarification_llm,
        )
        active_tracer.log_artifact("01_clarification.json", clarification)

        if clarification.is_ambiguous:
            active_tracer.log_summary(
                status="CLARIFICATION_REQUIRED",
                question=question,
            )
            return {
                "status": "CLARIFICATION_REQUIRED",
                "question": question,
                "session_id": active_session_id,
                "is_ambiguous": True,
                "clarification_question": clarification.clarification_question,
                "suggested_options": clarification.suggested_options or [],
                "ambiguity_type": clarification.reason or "AMBIGUOUS_QUESTION",
                "messages": [
                    AIMessage(
                        content=clarification.clarification_question
                        or "Câu hỏi của bạn cần được làm rõ thêm."
                    )
                ],
                "data": None,
                "columns": None,
                "sql": None,
                "recharts_config": None,
                "tracer": active_tracer,
            }

    # 2. Invoke Agent bất đồng bộ qua ainvoke
    active_agent = agent or create_text2sql_supervisor()
    config = {"configurable": {"thread_id": active_thread_id}}
    input_state = {
        "messages": [HumanMessage(content=question)],
    }

    try:
        output_state = await active_agent.ainvoke(
            input_state,
            config=config,
            context=active_user_context,
        )

        messages = output_state.get("messages", [])
        final_answer = messages[-1].content if messages else ""
        files = output_state.get("files", {})

        if isinstance(files, dict):
            for fname, fcontent in files.items():
                active_tracer.log_artifact(fname, fcontent)

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
    "create_text2sql_supervisor",
    "get_supervisor_subagents",
    "run_supervisor",
]
