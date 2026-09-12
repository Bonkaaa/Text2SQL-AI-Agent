from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình tập trung cho AI Agent Text-to-SQL đọc từ biến môi trường (.env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Ứng Dụng (Application) ---
    app_name: str = Field(default="text2sql-agent", description="Tên ứng dụng")
    app_env: Literal["development", "production", "testing"] = Field(
        default="development", description="Môi trường chạy"
    )
    debug: bool = Field(default=True, description="Chế độ debug")
    log_level: str = Field(default="INFO", description="Mức độ log")

    # --- API Gateway ---
    api_host: str = Field(default="0.0.0.0", description="Host lắng nghe của FastAPI")
    api_port: int = Field(default=8000, description="Port chạy server")
    api_prefix: str = Field(default="/api/v1", description="Prefix đường dẫn API")

    # --- LLM Providers & Tiering Strategy ---
    llm_provider: Literal["openai", "gemini", "deepseek", "mistral"] = Field(
        default="openai", description="Nhà cung cấp LLM mặc định"
    )
    openai_api_key: str | None = Field(default=None, description="Khóa API OpenAI")
    gemini_api_key: str | None = Field(
        default=None, description="Khóa API Google Gemini"
    )
    deepseek_api_key: str | None = Field(default=None, description="Khóa API DeepSeek")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="Base URL của DeepSeek API",
    )
    mistral_api_key: str | None = Field(default=None, description="Khóa API Mistral AI")

    # Tier 1 Model: Dành cho tác vụ suy luận & sinh SQL phức tạp
    tier1_model: str = Field(
        default="gpt-4o", description="Model mạnh mẽ cho SQL Generator"
    )
    # Tier 2 Model: Dành cho tác vụ nhẹ như Schema Retriever & Response Synthesizer
    tier2_model: str = Field(
        default="gpt-4o-mini", description="Model nhẹ tối ưu chi phí"
    )
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Nhiệt độ sinh LLM (0.0 cho SQL tất định)",
    )
    llm_max_tokens: int = Field(
        default=2048, gt=0, description="Số token tối đa sinh ra"
    )

    # --- Database & Warehouse ---
    duckdb_path: str = Field(
        default="./data/tpch.duckdb", description="Đường dẫn file DuckDB local"
    )
    bigquery_project: str | None = Field(
        default=None, description="Google Cloud Project ID"
    )
    bigquery_dataset: str | None = Field(
        default=None, description="BigQuery Dataset ID"
    )

    # --- Governance & Guardrails ---
    default_row_limit: int = Field(
        default=1000, gt=0, description="Giới hạn số dòng tối đa cho phép trả về"
    )
    max_retries: int = Field(
        default=3, gt=0, description="Số lần tối đa tự sửa lỗi SQL khi gặp ngoại lệ"
    )
    max_bytes_scanned: int = Field(
        default=1073741824,
        gt=0,
        description="Ngưỡng dung lượng quét tối đa (1GB = 1073741824 bytes)",
    )
    query_timeout_seconds: int = Field(
        default=30,
        gt=0,
        description="Thời gian timeout tối đa cho 1 truy vấn SQL (giây)",
    )


@lru_cache
def get_settings() -> Settings:
    """Hàm singleton lấy đối tượng cấu hình Settings được cache qua lru_cache."""
    return Settings()
