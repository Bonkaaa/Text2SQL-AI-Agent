"""Pre-flight Security & Clarification Gatekeeper Engine (Component 2.5.3).

Đóng vai trò là chốt chặn an ninh và làm rõ câu hỏi hai tầng (Two-Tier Defense-in-Depth):
1. Tier 1: Deterministic Regex Guardrails (< 0.1ms, $0) chặn đứng DDL/DML, prompt injection thô thiển, shell script.
2. Tier 2: Unified LLM Guardrails & Clarification (1 Structured Output Call qua Tier 2 Model)
   đánh giá cả vi phạm ngữ nghĩa, ngoài miền TPC-H và tính mơ hồ của câu hỏi.
3. Hardcoded Refusal Mapping: Tuyệt đối không cho LLM tự do xin lỗi hoặc giải thích dài dòng khi vi phạm.
4. Fail-Open Fallback: Cho phép tiếp tục luồng an toàn khi LLM API gặp lỗi mạng/timeout.
5. Tương thích ngược hoàn toàn với check_clarification_needed.
"""

from __future__ import annotations

import logging
import random
from typing import Final

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.guardrails.regex_guard import evaluate_regex_guardrails
from src.agents.prompts.preflight_prompt import PREFLIGHT_GATEKEEPER_PROMPT
from src.config import get_settings
from src.models.artifacts import (
    InputPreflightEvaluation,
    PreflightDecision,
    PreflightDecisionType,
    SafetyCategory,
)
from src.models.state import ClarificationResult
from src.services import get_chat_model

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. HARDCODED REFUSAL MESSAGES CHO TIER 2
# ==============================================================================

TIER2_REFUSAL_MESSAGES: Final[dict[SafetyCategory, str]] = {
    SafetyCategory.UNSAFE_PROMPT_INJECTION: (
        "Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin và bảo mật chỉ dẫn hệ thống."
    ),
    SafetyCategory.UNSAFE_DATA_MUTATION: (
        "Yêu cầu của bạn bị từ chối do chứa yêu cầu chỉnh sửa hoặc can thiệp dữ liệu. "
        "Hệ thống chỉ hỗ trợ truy vấn đọc dữ liệu phân tích (SELECT)."
    ),
    SafetyCategory.UNSUPPORTED_OUT_OF_DOMAIN: (
        "Hệ thống chỉ hỗ trợ giải đáp và phân tích dữ liệu kinh doanh & chuỗi cung ứng (chuẩn TPC-H). "
        "Vui lòng đặt câu hỏi liên quan đến doanh thu, đơn hàng, khách hàng, nhà cung cấp hoặc tồn kho."
    ),
}

# ==============================================================================
# 1. POOL GỢI Ý PHƯƠNG ÁN LÀM RÕ (TPC-H SUGGESTIONS POOL)
# ==============================================================================

DEFAULT_CLARIFICATION_OPTIONS_POOL: Final[list[str]] = [
    "Xem tổng doanh thu theo từng năm (1992 - 1998)",
    "Top 5 khách hàng có tổng chi tiêu cao nhất",
    "Doanh thu theo từng phân khúc thị trường (Market Segment)",
    "Top 10 mặt hàng (Parts) bán chạy nhất năm 1995",
    "Tổng số đơn đặt hàng theo từng trạng thái (Order Status)",
    "Danh sách các nhà cung cấp có số dư tài khoản cao nhất",
    "Doanh thu và lợi nhuận theo từng khu vực địa lý (Region)",
    "Top 5 quốc gia có doanh số bán hàng lớn nhất",
    "Các đơn hàng có mức ưu tiên khẩn cấp (1-URGENT) trong năm 1996",
    "Mức chiết khấu trung bình theo từng phương thức vận chuyển (Ship Mode)",
]


def get_random_suggested_options(k: int = 3) -> list[str]:
    """Lấy ngẫu nhiên k phương án gợi ý từ pool và đánh số thứ tự A, B, C..."""
    selected = random.sample(
        DEFAULT_CLARIFICATION_OPTIONS_POOL,
        min(k, len(DEFAULT_CLARIFICATION_OPTIONS_POOL)),
    )
    labels = ["A", "B", "C", "D", "E", "F", "G"]
    return [f"{labels[i]}. {opt}" for i, opt in enumerate(selected)]


# ==============================================================================
# 2. HÀM ĐIỀU PHỐI PRE-FLIGHT GATEKEEPER (CORE ENGINE)
# ==============================================================================


def evaluate_input_preflight(
    question: str,
    llm: BaseChatModel | None = None,
) -> PreflightDecision:
    """Đánh giá toàn diện an toàn và độ rõ ràng của câu hỏi qua 2 tầng kiểm duyệt.

    Args:
        question: Câu hỏi tự nhiên từ người dùng.
        llm: Instance Chat Model (nếu None sẽ tự khởi tạo Tier 2 từ get_settings).

    Returns:
        PreflightDecision: Quyết định phân luồng (ALLOWED, CLARIFICATION_REQUIRED, SECURITY_BLOCKED).
    """
    cleaned_question = question.strip() if question else ""

    # Bước 0: Kiểm tra câu hỏi rỗng hoặc chỉ có khoảng trắng
    if not cleaned_question:
        logger.warning("[PreflightGatekeeper] Câu hỏi rỗng hoặc chỉ có khoảng trắng.")
        return PreflightDecision(
            decision=PreflightDecisionType.CLARIFICATION_REQUIRED,
            is_safe=True,
            needs_clarification=True,
            clarification_question="Bạn có thể nhập câu hỏi cụ thể về dữ liệu bán hàng hoặc chuỗi cung ứng TPC-H không?",
            suggested_options=get_random_suggested_options(3),
            tier="tier1_regex",
        )

    # Bước 1: Tier 1 - Fast Deterministic Regex Guardrails (< 0.1ms, $0)
    regex_result = evaluate_regex_guardrails(cleaned_question)
    if not regex_result.is_safe:
        logger.warning(
            f"[PreflightGatekeeper] Chặn bởi Tier 1 Regex: {regex_result.violation_type} "
            f"cho câu hỏi: '{cleaned_question}'"
        )
        return PreflightDecision(
            decision=PreflightDecisionType.SECURITY_BLOCKED,
            is_safe=False,
            safety_category=regex_result.violation_type.value if regex_result.violation_type else "REGEX_VIOLATION",
            refusal_message=regex_result.refusal_message,
            needs_clarification=False,
            tier="tier1_regex",
        )

    # Bước 2: Khởi tạo mô hình Tier 2 nếu chưa truyền vào
    chat_model = llm
    if chat_model is None:
        settings = get_settings()
        chat_model = get_chat_model(settings.tier2_model)

    # Bước 3: Tier 2 - Gọi LLM với Structured Output (InputPreflightEvaluation)
    try:
        structured_llm = chat_model.with_structured_output(InputPreflightEvaluation)
        messages = PREFLIGHT_GATEKEEPER_PROMPT.format_messages(question=cleaned_question)
        eval_result = structured_llm.invoke(messages)

        if isinstance(eval_result, dict):
            eval_result = InputPreflightEvaluation(**eval_result)
        elif not isinstance(eval_result, InputPreflightEvaluation):
            logger.warning(
                f"[PreflightGatekeeper] LLM trả về kiểu dữ liệu không mong đợi: {type(eval_result)}. Chuyển sang fallback an toàn."
            )
            return PreflightDecision(
                decision=PreflightDecisionType.ALLOWED,
                is_safe=True,
                needs_clarification=False,
                tier="fallback",
            )

    except Exception:
        # Cơ chế Fail-Open an toàn: khi có lỗi LLM API/mạng, cho phép tiếp tục luồng an toàn
        logger.exception("[PreflightGatekeeper] Lỗi khi gọi LLM Preflight. Kích hoạt Fail-Open.")
        return PreflightDecision(
            decision=PreflightDecisionType.ALLOWED,
            is_safe=True,
            needs_clarification=False,
            tier="fallback",
        )

    # Bước 4: Hậu kiểm tất định (Deterministic Post-Check & Routing)

    # 4.1. Nếu LLM phát hiện không an toàn hoặc ngoài miền
    if not eval_result.is_safe:
        category_enum = eval_result.safety_category
        refusal_msg = TIER2_REFUSAL_MESSAGES.get(
            category_enum,
            TIER2_REFUSAL_MESSAGES[SafetyCategory.UNSAFE_PROMPT_INJECTION],
        )
        logger.warning(
            f"[PreflightGatekeeper] Chặn bởi Tier 2 LLM: category={category_enum}, reason={eval_result.safety_reason}"
        )
        return PreflightDecision(
            decision=PreflightDecisionType.SECURITY_BLOCKED,
            is_safe=False,
            safety_category=category_enum.value if hasattr(category_enum, "value") else str(category_enum),
            refusal_message=refusal_msg,
            needs_clarification=False,
            evaluation=eval_result,
            tier="tier2_llm",
        )

    # 4.2. Nếu an toàn nhưng mơ hồ -> Yêu cầu làm rõ
    if eval_result.needs_clarification:
        options = eval_result.suggested_options or get_random_suggested_options(3)
        clarify_q = (
            eval_result.clarification_question
            or "Câu hỏi của bạn chưa đủ thông tin rõ ràng. Vui lòng chọn một trong các gợi ý bên dưới."
        )
        logger.info(
            f"[PreflightGatekeeper] Yêu cầu làm rõ: reason={eval_result.clarification_reason}"
        )
        return PreflightDecision(
            decision=PreflightDecisionType.CLARIFICATION_REQUIRED,
            is_safe=True,
            safety_category="SAFE",
            needs_clarification=True,
            clarification_question=clarify_q,
            suggested_options=options,
            evaluation=eval_result,
            tier="tier2_llm",
        )

    # 4.3. An toàn và rõ ràng -> Cho phép đi tiếp vào Master Supervisor
    return PreflightDecision(
        decision=PreflightDecisionType.ALLOWED,
        is_safe=True,
        safety_category="SAFE",
        needs_clarification=False,
        evaluation=eval_result,
        tier="tier2_llm",
    )


# ==============================================================================
# 3. ADAPTER TƯƠNG THÍCH NGƯỢC (BACKWARD COMPATIBILITY)
# ==============================================================================


def check_clarification_needed(
    question: str,
    llm: BaseChatModel | None = None,
) -> ClarificationResult:
    """Hàm adapter giữ tương thích với contract cũ của Component 4.1."""
    decision = evaluate_input_preflight(question=question, llm=llm)

    if decision.decision == PreflightDecisionType.CLARIFICATION_REQUIRED:
        reason = (
            decision.evaluation.clarification_reason
            if decision.evaluation
            else "Câu hỏi mơ hồ hoặc thiếu phạm vi lọc"
        )
        return ClarificationResult(
            needs_clarification=True,
            reason=reason,
            clarification_question=decision.clarification_question,
            suggested_options=decision.suggested_options,
        )

    if decision.decision == PreflightDecisionType.SECURITY_BLOCKED:
        return ClarificationResult(
            needs_clarification=True,
            reason=decision.refusal_message or "Yêu cầu bị từ chối do vi phạm an ninh",
            clarification_question=decision.refusal_message,
            suggested_options=[],
        )

    return ClarificationResult(
        needs_clarification=False,
        reason=None,
        clarification_question=None,
        suggested_options=[],
    )
