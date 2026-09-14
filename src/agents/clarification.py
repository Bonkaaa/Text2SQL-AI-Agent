"""Khâu Phân Tích & Làm Rõ Câu Hỏi Mơ Hồ (Component 4.1).

Đóng vai trò là Pre-flight Decision Gatekeeper (One-shot Prompt) trước khi kích hoạt
toàn bộ luồng DeepAgents Supervisor / Pipeline:
- Mô hình Tier 2 (gpt-4o-mini / gemini-2.5-flash / claude-3-5-haiku) tối ưu độ trễ & chi phí.
- Đầu ra có cấu trúc: ClarificationResult (Pydantic Model).
- Hàm thực thi: check_clarification_needed(question, llm=...) với Fast-path và cơ chế Fail-Open fallback an toàn.
"""

import logging
import random
from typing import Final

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import CLARIFICATION_PROMPT
from src.config import get_settings
from src.models.state import ClarificationResult
from src.services import get_chat_model

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. DANH SÁCH GỢI Ý MẪU (SUGGESTED OPTIONS POOL)
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
    """Lấy ngẫu nhiên k phương án gợi ý từ pool và đánh số thứ tự A, B, C...

    Args:
        k: Số lượng phương án cần lấy (mặc định 3).

    Returns:
        Danh sách các phương án gợi ý có tiền tố A., B., C...
    """
    selected = random.sample(
        DEFAULT_CLARIFICATION_OPTIONS_POOL,
        min(k, len(DEFAULT_CLARIFICATION_OPTIONS_POOL)),
    )
    labels = ["A", "B", "C", "D", "E", "F", "G"]
    return [f"{labels[i]}. {opt}" for i, opt in enumerate(selected)]


# ==============================================================================
# 1. HÀM THỰC THI KIỂM TRA ĐỘ RÕ RÀNG (ONE-SHOT GATEKEEPER)
# ==============================================================================


def check_clarification_needed(
    question: str,
    llm: BaseChatModel | None = None,
) -> ClarificationResult:
    """Đánh giá xem câu hỏi người dùng có cần làm rõ thêm điều kiện lọc hay không.

    Args:
        question: Chuỗi câu hỏi tự nhiên từ người dùng.
        llm: Instance Chat Model (nếu None sẽ tự khởi tạo Tier 2 qua get_chat_model).

    Returns:
        ClarificationResult: Kết quả phân tích (needs_clarification, reason, question, options).
    """
    # 1. Kiểm tra nhanh chuỗi rỗng / whitespace
    cleaned_question = question.strip() if question else ""
    if not cleaned_question:
        logger.warning("Câu hỏi người dùng rỗng hoặc chỉ có khoảng trắng.")
        return ClarificationResult(
            needs_clarification=True,
            reason="Câu hỏi rỗng hoặc thiếu nội dung yêu cầu.",
            clarification_question="Bạn có thể nhập câu hỏi cụ thể về dữ liệu bán hàng hoặc chuỗi cung ứng TPC-H không?",
            suggested_options=get_random_suggested_options(3),
        )

    # 2. Khởi tạo LLM nếu chưa được truyền
    chat_model = llm
    if chat_model is None:
        settings = get_settings()
        chat_model = get_chat_model(settings.tier2_model)

    # 3. Gọi mô hình với Structured Output
    try:
        structured_llm = chat_model.with_structured_output(ClarificationResult)
        messages = CLARIFICATION_PROMPT.format_messages(question=cleaned_question)
        result = structured_llm.invoke(messages)

        # Đảm bảo trả về đúng kiểu ClarificationResult
        if isinstance(result, ClarificationResult):
            return result
        elif isinstance(result, dict):
            return ClarificationResult(**result)
        else:
            logger.warning(
                "Structured output trả về kiểu không mong đợi: %s",
                type(result),
            )
            return ClarificationResult(needs_clarification=False)

    except Exception as exc:
        # Cơ chế Fail-Open an toàn: khi có lỗi LLM API/mạng, cho phép tiếp tục luồng
        logger.exception("Lỗi khi gọi Clarification Agent LLM. Kích hoạt Fail-Open.")
        return ClarificationResult(
            needs_clarification=False,
            reason=f"Fallback do lỗi LLM API: {exc}",
            clarification_question=None,
            suggested_options=[],
        )
