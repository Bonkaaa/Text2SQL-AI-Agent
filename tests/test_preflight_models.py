"""Unit tests cho các Pre-Flight Guardrails & Clarification Models (Component 2.5.2).

Kiểm tra:
- Khởi tạo và ràng buộc dữ liệu cho SafetyCategory Enum.
- Khởi tạo và validation cho InputPreflightEvaluation (Structured Output Model).
- Khởi tạo PreflightDecisionType và PreflightDecision model.
- Tuần tự hóa JSON (model_dump, model_dump_json).
"""

import pytest
from pydantic import ValidationError

from src.models.artifacts import (
    InputPreflightEvaluation,
    PreflightDecision,
    PreflightDecisionType,
    SafetyCategory,
)


def test_safety_category_enum():
    """Kiểm tra các giá trị định nghĩa sẵn trong SafetyCategory."""
    assert SafetyCategory.SAFE.value == "SAFE"
    assert SafetyCategory.UNSAFE_PROMPT_INJECTION.value == "UNSAFE_PROMPT_INJECTION"
    assert SafetyCategory.UNSAFE_DATA_MUTATION.value == "UNSAFE_DATA_MUTATION"
    assert SafetyCategory.UNSUPPORTED_OUT_OF_DOMAIN.value == "UNSUPPORTED_OUT_OF_DOMAIN"


def test_input_preflight_evaluation_safe_and_clear():
    """Kiểm tra khởi tạo InputPreflightEvaluation khi câu hỏi an toàn và rõ ràng."""
    eval_result = InputPreflightEvaluation(
        is_safe=True,
        safety_category=SafetyCategory.SAFE,
        safety_reason=None,
        needs_clarification=False,
        clarification_reason=None,
        clarification_question=None,
        suggested_options=[],
    )

    assert eval_result.is_safe is True
    assert eval_result.safety_category == SafetyCategory.SAFE
    assert eval_result.needs_clarification is False
    assert eval_result.suggested_options == []

    # Test serialization
    dump = eval_result.model_dump()
    assert dump["is_safe"] is True
    assert dump["safety_category"] == "SAFE"


def test_input_preflight_evaluation_unsafe():
    """Kiểm tra khởi tạo InputPreflightEvaluation khi câu hỏi vi phạm an toàn thông tin."""
    eval_result = InputPreflightEvaluation(
        is_safe=False,
        safety_category=SafetyCategory.UNSAFE_PROMPT_INJECTION,
        safety_reason="Phát hiện nỗ lực trích xuất system prompt",
        needs_clarification=False,
    )

    assert eval_result.is_safe is False
    assert eval_result.safety_category == SafetyCategory.UNSAFE_PROMPT_INJECTION
    assert eval_result.safety_reason == "Phát hiện nỗ lực trích xuất system prompt"
    assert eval_result.needs_clarification is False


def test_input_preflight_evaluation_clarification_required():
    """Kiểm tra khởi tạo InputPreflightEvaluation khi câu hỏi mơ hồ cần làm rõ."""
    options = ["A. Năm 1994", "B. Năm 1995", "C. Toàn bộ thời gian"]
    eval_result = InputPreflightEvaluation(
        is_safe=True,
        safety_category=SafetyCategory.SAFE,
        needs_clarification=True,
        clarification_reason="Chưa xác định mốc thời gian phân tích doanh thu",
        clarification_question="Bạn muốn xem doanh thu trong giai đoạn nào?",
        suggested_options=options,
    )

    assert eval_result.is_safe is True
    assert eval_result.needs_clarification is True
    assert eval_result.clarification_question == "Bạn muốn xem doanh thu trong giai đoạn nào?"
    assert len(eval_result.suggested_options) == 3
    assert eval_result.suggested_options[0] == "A. Năm 1994"


def test_input_preflight_evaluation_defaults_and_validation():
    """Kiểm tra giá trị mặc định và xác thực kiểu dữ liệu."""
    eval_result = InputPreflightEvaluation(
        is_safe=True,
        needs_clarification=False,
    )
    assert eval_result.safety_category == SafetyCategory.SAFE
    assert eval_result.suggested_options == []

    # Bắt buộc phải có is_safe và needs_clarification
    with pytest.raises(ValidationError):
        InputPreflightEvaluation()  # type: ignore


def test_preflight_decision_allowed():
    """Kiểm tra PreflightDecision với trạng thái ALLOWED."""
    decision = PreflightDecision(
        decision=PreflightDecisionType.ALLOWED,
        is_safe=True,
        safety_category="SAFE",
        tier="tier2_llm",
    )
    assert decision.decision == PreflightDecisionType.ALLOWED
    assert decision.is_safe is True
    assert decision.tier == "tier2_llm"
    assert decision.refusal_message is None


def test_preflight_decision_security_blocked():
    """Kiểm tra PreflightDecision với trạng thái SECURITY_BLOCKED."""
    decision = PreflightDecision(
        decision=PreflightDecisionType.SECURITY_BLOCKED,
        is_safe=False,
        safety_category="UNSAFE_PROMPT_INJECTION",
        refusal_message="Yêu cầu của bạn bị từ chối do vi phạm quy tắc an toàn thông tin.",
        tier="tier1_regex",
    )
    assert decision.decision == PreflightDecisionType.SECURITY_BLOCKED
    assert decision.is_safe is False
    assert decision.refusal_message is not None
    assert decision.tier == "tier1_regex"


def test_preflight_decision_clarification_required():
    """Kiểm tra PreflightDecision với trạng thái CLARIFICATION_REQUIRED."""
    decision = PreflightDecision(
        decision=PreflightDecisionType.CLARIFICATION_REQUIRED,
        is_safe=True,
        needs_clarification=True,
        clarification_question="Bạn muốn xem doanh thu của năm nào?",
        suggested_options=["A. 1994", "B. 1995"],
        tier="tier2_llm",
    )
    assert decision.decision == PreflightDecisionType.CLARIFICATION_REQUIRED
    assert decision.is_safe is True
    assert decision.needs_clarification is True
    assert len(decision.suggested_options) == 2
