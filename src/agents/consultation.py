"""Subagent: Consultation & Data Catalog Specialist (Component consultation-agent).

Đóng gói theo chuẩn DeepAgents SubAgent dictionary (name="consultation-agent"):
- Chế độ mode: "isolated" (Context Quarantine: cách ly hội thoại và ngữ cảnh khỏi Supervisor).
- Mô hình Tier 2 (gpt-4o-mini / gemini-2.5-flash / claude-3-5-haiku) tối ưu tốc độ & chi phí.
- Công cụ (3 Strategic Metadata Tools):
  1. search_tables_and_columns: Tra cứu DDL và danh sách cột của 8 bảng TPC-H.
  2. get_column_samples_and_values: Tra cứu giá trị danh mục phân loại thực tế.
  3. search_business_definition: Tra cứu công thức dbt Semantic Metrics chuẩn.
- Nhiệm vụ:
  * Trả lời trực tiếp các câu chào hỏi, giao tiếp xã giao thông thường.
  * Sử dụng metadata tools để giải đáp câu hỏi về schema/catalog/metrics mà KHÔNG sinh SQL, KHÔNG query database.
"""

from typing import Any, Final

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.prompts import CONSULTATION_SYSTEM_PROMPT
from src.agents.tools import DIRECT_CHAT_TOOLS
from src.config import get_settings


def get_consultation_subagent(
    model: str | BaseChatModel | None = None,
) -> dict[str, Any]:
    """Tạo cấu hình SubAgent Dictionary cho Consultation Specialist.

    Args:
        model: Tùy chọn chỉ định ChatModel instance hoặc model name string
               (mặc định lấy tier2_model từ Settings).

    Returns:
        Dictionary theo đúng đặc tả DeepAgents SubAgent.
    """
    settings = get_settings()
    active_model = model or settings.tier2_model

    return {
        "name": "consultation-agent",
        "description": (
            "Chuyên gia tư vấn giải đáp giao tiếp xã giao, tra cứu danh mục bảng, "
            "cột, giá trị danh mục hợp lệ và định nghĩa chỉ số dbt metrics của "
            "hệ thống TPC-H mà không cần sinh SQL hay query database."
        ),
        "system_prompt": CONSULTATION_SYSTEM_PROMPT,
        "mode": "isolated",
        "tools": list(DIRECT_CHAT_TOOLS),
        "model": active_model,
    }


# Instance mặc định dùng sẵn
consultation_subagent: Final[dict[str, Any]] = get_consultation_subagent()

__all__ = [
    "consultation_subagent",
    "get_consultation_subagent",
]
