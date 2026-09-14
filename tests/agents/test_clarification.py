"""Unit tests cho Component 4.1: Khâu Phân Tích & Làm Rõ Câu Hỏi Mơ Hồ (One-shot Gatekeeper)."""

from unittest.mock import MagicMock, patch

from src.agents.clarification import (
    DEFAULT_CLARIFICATION_OPTIONS_POOL,
    check_clarification_needed,
    get_random_suggested_options,
)
from src.models.state import ClarificationResult


def test_check_clarification_ambiguous_question_mock_llm():
    """Kiểm tra xử lý câu hỏi mơ hồ qua Mock LLM."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    expected_result = ClarificationResult(
        needs_clarification=True,
        reason="Câu hỏi thiếu khoảng thời gian và phân khúc cụ thể.",
        clarification_question="Bạn muốn xem doanh thu theo tiêu chí nào sau đây?",
        suggested_options=[
            "A. Theo từng năm (1992 - 1998)",
            "B. Theo từng khu vực (Region)",
            "C. Top 5 khách hàng có doanh số cao nhất",
        ],
    )
    mock_structured.invoke.return_value = expected_result

    result = check_clarification_needed("Doanh thu thế nào?", llm=mock_llm)

    assert result.needs_clarification is True
    assert result.reason == "Câu hỏi thiếu khoảng thời gian và phân khúc cụ thể."
    assert "Bạn muốn xem doanh thu" in result.clarification_question
    assert len(result.suggested_options) == 3
    assert result.suggested_options[0].startswith("A.")
    mock_llm.with_structured_output.assert_called_once_with(ClarificationResult)


def test_check_clarification_clear_question_mock_llm():
    """Kiểm tra xử lý câu hỏi đã rõ ràng qua Mock LLM."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured

    expected_result = ClarificationResult(
        needs_clarification=False,
        reason=None,
        clarification_question=None,
        suggested_options=[],
    )
    mock_structured.invoke.return_value = expected_result

    result = check_clarification_needed(
        "Top 5 khách hàng mua nhiều nhất năm 1995 tại Châu Á",
        llm=mock_llm,
    )

    assert result.needs_clarification is False
    assert result.reason is None
    assert result.clarification_question is None
    assert result.suggested_options == []


def test_random_suggested_options_pool():
    """Kiểm tra pool gợi ý có ít nhất 10 lựa chọn và hàm random lấy ra 3 options hợp lệ."""
    assert len(DEFAULT_CLARIFICATION_OPTIONS_POOL) >= 10
    options = get_random_suggested_options(3)
    assert len(options) == 3
    assert options[0].startswith("A. ")
    assert options[1].startswith("B. ")
    assert options[2].startswith("C. ")

    # Đảm bảo các options trích xuất nằm trong pool
    for opt in options:
        content = opt[3:]  # Bỏ "A. ", "B. ", "C. "
        assert content in DEFAULT_CLARIFICATION_OPTIONS_POOL


def test_check_clarification_empty_or_whitespace_question():
    """Kiểm tra câu hỏi rỗng hoặc chỉ có khoảng trắng được bắt trực tiếp với 3 gợi ý ngẫu nhiên."""
    result = check_clarification_needed("   ")
    assert result.needs_clarification is True
    assert "rỗng" in result.reason.lower() or "thiếu" in result.reason.lower()
    assert result.clarification_question is not None
    assert len(result.suggested_options) == 3
    assert result.suggested_options[0].startswith("A. ")
    assert result.suggested_options[1].startswith("B. ")
    assert result.suggested_options[2].startswith("C. ")


def test_check_clarification_fallback_on_llm_exception():
    """Kiểm tra cơ chế fail-open: khi LLM ném ngoại lệ, pipeline không bị crash mà tiếp tục luồng."""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.invoke.side_effect = RuntimeError("LLM API Timeout")

    result = check_clarification_needed(
        "Cho tôi xem doanh thu năm 1995",
        llm=mock_llm,
    )

    # Fail-open: Cho phép tiếp tục câu hỏi sang các bước sau
    assert result.needs_clarification is False
    assert result.reason is not None
    assert "LLM API Timeout" in result.reason or "Fallback" in result.reason


@patch("src.agents.clarification.get_chat_model")
def test_check_clarification_default_llm_initialization(mock_get_chat_model):
    """Kiểm tra việc tự động lấy chat model Tier 2 khi không truyền llm."""
    mock_llm_instance = MagicMock()
    mock_structured = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured
    mock_get_chat_model.return_value = mock_llm_instance

    mock_structured.invoke.return_value = ClarificationResult(
        needs_clarification=False,
    )

    result = check_clarification_needed("Tổng đơn hàng năm 1996?")

    assert result.needs_clarification is False
    mock_get_chat_model.assert_called_once()
