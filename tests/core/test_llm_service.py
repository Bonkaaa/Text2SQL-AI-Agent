from unittest.mock import patch

from src.config import Settings
from src.services.llm_service import get_chat_model


def test_get_chat_model_missing_keys():
    """Kiểm tra khi chưa cấu hình API Key thì trả về None mà không crash."""
    with patch("src.services.llm_service.get_settings") as mock_get_settings:
        mock_get_settings.return_value = Settings(
            _env_file=None,
            llm_provider="openai",
            openai_api_key=None,
        )
        model = get_chat_model()
        assert model is None


def test_get_chat_model_supported_providers():
    """Kiểm tra gọi init_chat_model đúng tham số cho cả 4 nhà cung cấp."""
    with patch("src.services.llm_service.init_chat_model") as mock_init:
        # 1. OpenAI
        with patch("src.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                _env_file=None,
                llm_provider="openai",
                openai_api_key="sk-test-openai",
                tier1_model="gpt-4o",
                tier2_model="gpt-4o-mini",
            )
            get_chat_model(tier="tier1")
            mock_init.assert_called_with(
                model="gpt-4o",
                model_provider="openai",
                api_key="sk-test-openai",
                temperature=0.0,
                max_tokens=2048,
            )

        # 2. Gemini
        with patch("src.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                _env_file=None,
                llm_provider="gemini",
                gemini_api_key="gemini-key",
                tier2_model="gemini-1.5-flash",
            )
            get_chat_model(tier="tier2")
            mock_init.assert_called_with(
                model="gemini-1.5-flash",
                model_provider="google_genai",
                api_key="gemini-key",
                temperature=0.0,
                max_tokens=2048,
            )

        # 3. DeepSeek
        with patch("src.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                _env_file=None,
                llm_provider="deepseek",
                deepseek_api_key="deepseek-key",
                tier1_model="deepseek-chat",
            )
            get_chat_model(tier="tier1")
            mock_init.assert_called_with(
                model="deepseek-chat",
                model_provider="deepseek",
                api_key="deepseek-key",
                temperature=0.0,
                max_tokens=2048,
            )

        # 4. Mistral
        with patch("src.services.llm_service.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                _env_file=None,
                llm_provider="mistral",
                mistral_api_key="mistral-key",
                tier2_model="mistral-small-latest",
            )
            get_chat_model(tier="tier2")
            mock_init.assert_called_with(
                model="mistral-small-latest",
                model_provider="mistralai",
                api_key="mistral-key",
                temperature=0.0,
                max_tokens=2048,
            )
