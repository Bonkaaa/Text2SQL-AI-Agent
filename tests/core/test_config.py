import pytest
from pydantic import ValidationError

from src.config import Settings, get_settings


def test_default_settings():
    """Kiểm tra giá trị mặc định của Settings khi không đọc file .env."""
    settings = Settings(_env_file=None)

    assert settings.app_name == "text2sql-agent"
    assert settings.app_env in ["development", "production", "testing"]
    assert settings.tier1_model is not None
    assert settings.tier2_model is not None
    assert settings.default_row_limit == 1000
    assert settings.max_retries == 3
    assert settings.query_timeout_seconds == 30
    assert settings.max_bytes_scanned > 0


def test_custom_settings_override():
    """Kiểm tra ghi đè cấu hình qua tham số hoặc biến môi trường."""
    custom_settings = Settings(
        _env_file=None,
        app_name="custom-agent",
        max_retries=5,
        default_row_limit=500,
        tier1_model="gpt-4o",
    )

    assert custom_settings.app_name == "custom-agent"
    assert custom_settings.max_retries == 5
    assert custom_settings.default_row_limit == 500
    assert custom_settings.tier1_model == "gpt-4o"


def test_guardrail_validation_positive_integers():
    """Kiểm tra các ràng buộc an toàn: max_retries và default_row_limit phải là số nguyên dương."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_retries=0)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, default_row_limit=-10)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, query_timeout_seconds=0)


def test_get_settings_singleton(monkeypatch):
    """Kiểm tra hàm get_settings sử dụng lru_cache trả về cùng một instance."""
    # Xóa cache trước khi test
    get_settings.cache_clear()

    settings_1 = get_settings()
    settings_2 = get_settings()

    assert settings_1 is settings_2


def test_llm_providers_validation():
    """Kiểm tra cấu hình 4 nhà cung cấp LLM hợp lệ (openai, gemini, deepseek, mistral)."""
    for provider in ["openai", "gemini", "deepseek", "mistral"]:
        s = Settings(_env_file=None, llm_provider=provider)
        assert s.llm_provider == provider

    # Provider không nằm trong danh sách phải ném ValidationError
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="anthropic")
