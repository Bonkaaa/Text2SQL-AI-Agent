"""Subagent: Response Synthesizer & Đề Xuất Biểu Đồ (Component 4.2).

Đóng gói theo chuẩn DeepAgents SubAgent dictionary (name="response-synthesizer"):
- Chế độ mode: "isolated" (Context Quarantine: chỉ nhận câu hỏi và dữ liệu bảng).
- Mô hình Tier 2 (gpt-4o-mini / gemini-2.5-flash / claude-3-5-haiku) tối ưu độ trễ & chi phí.
- Công cụ tools: [] (Zero-tool agent: tập trung reasoning dữ liệu và sinh schema).
- Đầu ra có cấu trúc: SynthesizerResult (Pydantic Model) gồm chart_type, recharts_config, business_insight, summary_metrics.
- Hàm thực thi: synthesize_response(question, data, columns=..., llm=...) kèm Fast-path dữ liệu rỗng và Fail-Safe fallback.
"""

import logging
from typing import Any, Final

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import (
    SYNTHESIZER_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
)
from src.config import get_settings
from src.models.state import SynthesizerResult
from src.services import get_chat_model

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. KHAI BÁO SUBAGENT DICTIONARY CHUẨN DEEPAGENTS
# ==============================================================================


def get_synthesizer_subagent(model: str | None = None) -> dict[str, Any]:
    """Tạo cấu hình SubAgent Dictionary cho Response Synthesizer theo chuẩn DeepAgents.

    Args:
        model: Tùy chọn chỉ định model name (mặc định lấy tier2_model từ Settings).

    Returns:
        Dictionary theo đúng đặc tả DeepAgents SubAgent.
    """
    settings = get_settings()
    active_model = model or settings.tier2_model

    return {
        "name": "response-synthesizer",
        "description": (
            "Chuyên gia trực quan hóa và phân tích dữ liệu bảng, đề xuất cấu hình biểu đồ Recharts "
            "chuẩn JSON và diễn giải insight kinh doanh súc tích bằng tiếng Việt."
        ),
        "system_prompt": SYNTHESIZER_SYSTEM_PROMPT,
        "mode": "isolated",
        "tools": [],
        "model": active_model,
        "response_format": SynthesizerResult,
    }


# Instance mặc định dùng sẵn
response_synthesizer_subagent: Final[dict[str, Any]] = get_synthesizer_subagent()


# ==============================================================================
# 2. HÀM THỰC THI (RUNNER FUNCTION)
# ==============================================================================


def synthesize_response(
    question: str,
    data: list[dict[str, Any]],
    columns: list[str] | None = None,
    llm: BaseChatModel | None = None,
) -> SynthesizerResult:
    """Phân tích dữ liệu bảng, đề xuất cấu hình biểu đồ Recharts và diễn giải insight kinh doanh.

    Args:
        question: Câu hỏi nghiệp vụ ban đầu của người dùng.
        data: Danh sách các bản ghi kết quả truy vấn từ database.
        columns: Danh sách các cột (nếu None sẽ tự động suy luận từ record đầu tiên).
        llm: Instance Chat Model (nếu None sẽ tự khởi tạo Tier 2 qua get_chat_model).

    Returns:
        SynthesizerResult: Kết quả trực quan hóa, cấu hình Recharts và insight tiếng Việt.
    """
    # 1. Fast-path: Dữ liệu rỗng -> Trả về cấu hình table mặc định không tốn token LLM
    if not data:
        logger.info("Tập dữ liệu trả về rỗng. Trả về cấu hình table mặc định.")
        return SynthesizerResult(
            chart_type="table",
            recharts_config={},
            business_insight="Không tìm thấy bản ghi dữ liệu nào thỏa mãn điều kiện truy vấn.",
            summary_metrics={"total_rows": 0},
        )

    # 2. Tự động suy luận danh sách cột nếu người gọi không truyền
    active_columns = columns
    if not active_columns:
        active_columns = list(data[0].keys())

    # 3. Giới hạn tối đa 50 dòng mẫu đưa vào prompt để tránh tràn token / chi phí
    sample_records = data[:50]

    # 4. Khởi tạo LLM Tier 2 nếu chưa có
    chat_model = llm
    if chat_model is None:
        settings = get_settings()
        chat_model = get_chat_model(settings.tier2_model)

    # 5. Gọi LLM sinh structured output
    try:
        structured_llm = chat_model.with_structured_output(SynthesizerResult)
        messages = SYNTHESIZER_PROMPT.format_messages(
            question=question,
            columns=str(active_columns),
            data_records=str(sample_records),
        )
        result = structured_llm.invoke(messages)

        if isinstance(result, SynthesizerResult):
            return result
        elif isinstance(result, dict):
            return SynthesizerResult(**result)
        else:
            logger.warning(
                "Structured output trả về kiểu không mong đợi: %s",
                type(result),
            )
            return SynthesizerResult(
                chart_type="table",
                business_insight=f"Đã truy vấn thành công {len(data)} bản ghi dữ liệu.",
                summary_metrics={"total_rows": len(data)},
            )

    except Exception as exc:
        # Cơ chế Fail-Safe an toàn: không làm sập pipeline khi có lỗi LLM API
        logger.exception("Lỗi khi gọi Response Synthesizer LLM. Kích hoạt Fallback.")
        return SynthesizerResult(
            chart_type="table",
            recharts_config={},
            business_insight=f"Truy vấn trả về {len(data)} bản ghi dữ liệu. (Fallback do lỗi: {exc})",
            summary_metrics={"total_rows": len(data)},
        )
