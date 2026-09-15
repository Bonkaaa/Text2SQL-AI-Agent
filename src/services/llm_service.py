import logging
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from src.config import get_settings

logger = logging.getLogger(__name__)


def get_chat_model(
    tier: Literal["tier1", "tier2"] = "tier2",
    model_name: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    provider: Literal["openai", "gemini", "deepseek", "mistral"] | None = None,
) -> BaseChatModel | None:
    """Khởi tạo Chat Model trung tâm cho toàn bộ hệ thống thông qua init_chat_model.

    Hỗ trợ 4 nhà cung cấp theo cấu hình (.env / Settings):
      - openai: Dùng cho OpenAI (gpt-4o, gpt-4o-mini, ...)
      - gemini: Dùng cho Google Gemini (gemini-1.5-pro, gemini-1.5-flash, ...)
      - deepseek: Dùng cho DeepSeek API (tương thích giao thức OpenAI qua base_url)
      - mistral: Dùng cho Mistral AI (mistral-large, mistral-small, ...)

    Args:
        tier: Phân tầng model ("tier1" cho SQL Generator, "tier2" cho Diagnostic/Retriever/Synthesizer).
        model_name: Tên model cụ thể nếu muốn ghi đè cấu hình tier mặc định.
        temperature: Độ biến thiên sinh text (mặc định lấy theo Settings).
        max_tokens: Số lượng token tối đa (mặc định lấy theo Settings).
        provider: Ghi đè nhà cung cấp cụ thể (nếu None sẽ lấy settings.llm_provider).

    Returns:
        BaseChatModel | None: Instance Chat Model của LangChain hoặc None nếu thiếu API Key.
    """
    settings = get_settings()
    active_provider = provider or settings.llm_provider
    temp = temperature if temperature is not None else settings.llm_temperature
    max_toks = max_tokens if max_tokens is not None else settings.llm_max_tokens

    # Hỗ trợ trường hợp gọi get_chat_model("model-name") trực tiếp
    if tier not in ("tier1", "tier2") and model_name is None:
        model_name = str(tier)
        tier = "tier2"

    # Xác định model name theo tier nếu không được truyền trực tiếp
    if not model_name:
        provider_model_map = {
            "openai": (settings.openai_tier1_model, settings.openai_tier2_model),
            "gemini": (settings.gemini_tier1_model, settings.gemini_tier2_model),
            "deepseek": (settings.deepseek_tier1_model, settings.deepseek_tier2_model),
            "mistral": (settings.mistral_tier1_model, settings.mistral_tier2_model),
        }
        if provider and provider in provider_model_map:
            t1, t2 = provider_model_map[provider]
            model_name = t1 if tier == "tier1" else t2
        else:
            model_name = (
                settings.tier1_model if tier == "tier1" else settings.tier2_model
            )

    try:
        if active_provider == "openai":
            if not settings.openai_api_key:
                logger.debug(
                    "Bỏ qua init model OpenAI vì chưa cấu hình OPENAI_API_KEY."
                )
                return None
            return init_chat_model(
                model=model_name,
                model_provider="openai",
                api_key=settings.openai_api_key,
                temperature=temp,
                max_tokens=max_toks,
            )

        elif active_provider == "gemini":
            if not settings.gemini_api_key:
                logger.debug(
                    "Bỏ qua init model Gemini vì chưa cấu hình GEMINI_API_KEY."
                )
                return None
            return init_chat_model(
                model=model_name,
                model_provider="google_genai",
                api_key=settings.gemini_api_key,
                temperature=temp,
                max_tokens=max_toks,
            )

        elif active_provider == "deepseek":
            if not settings.deepseek_api_key:
                logger.debug(
                    "Bỏ qua init model DeepSeek vì chưa cấu hình DEEPSEEK_API_KEY."
                )
                return None
            return init_chat_model(
                model=model_name,
                model_provider="deepseek",
                api_key=settings.deepseek_api_key,
                temperature=temp,
                max_tokens=max_toks,
            )

        elif active_provider == "mistral":
            if not settings.mistral_api_key:
                logger.debug(
                    "Bỏ qua init model Mistral vì chưa cấu hình MISTRAL_API_KEY."
                )
                return None
            return init_chat_model(
                model=model_name,
                model_provider="mistralai",
                api_key=settings.mistral_api_key,
                temperature=temp,
                max_tokens=max_toks,
            )

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Lỗi khi khởi tạo Chat Model (%s / %s): %s.",
            active_provider,
            model_name,
            exc,
        )
        return None

    return None
