from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from dotenv import load_dotenv
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Tự động nạp các biến môi trường vào os.environ cho LangChain/LangSmith
load_dotenv()


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
    # 1. OpenAI
    openai_api_key: str | None = Field(default=None, description="Khóa API OpenAI")
    openai_tier1_model: str = Field(
        default="gpt-4o", description="Model Tier 1 của OpenAI"
    )
    openai_tier2_model: str = Field(
        default="gpt-4o-mini", description="Model Tier 2 của OpenAI"
    )

    # 2. Google Gemini
    gemini_api_key: str | None = Field(
        default=None, description="Khóa API Google Gemini"
    )
    gemini_tier1_model: str = Field(
        default="gemini-1.5-pro", description="Model Tier 1 của Google Gemini"
    )
    gemini_tier2_model: str = Field(
        default="gemini-1.5-flash", description="Model Tier 2 của Google Gemini"
    )

    # 3. DeepSeek
    deepseek_api_key: str | None = Field(default=None, description="Khóa API DeepSeek")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="Base URL của DeepSeek API",
    )
    deepseek_tier1_model: str = Field(
        default="deepseek-reasoner", description="Model Tier 1 của DeepSeek"
    )
    deepseek_tier2_model: str = Field(
        default="deepseek-chat", description="Model Tier 2 của DeepSeek"
    )

    # 4. Mistral AI
    mistral_api_key: str | None = Field(default=None, description="Khóa API Mistral AI")
    mistral_tier1_model: str = Field(
        default="mistral-large-latest", description="Model Tier 1 của Mistral AI"
    )
    mistral_tier2_model: str = Field(
        default="mistral-small-latest", description="Model Tier 2 của Mistral AI"
    )

    # Tier 1 & 2 Models: Nếu để None hoặc rỗng, sẽ tự động phân giải theo provider được chọn
    tier1_model: str | None = Field(
        default=None,
        description="Model mạnh mẽ cho SQL Generator (nếu không set sẽ lấy theo provider)",
    )
    tier2_model: str | None = Field(
        default=None,
        description="Model nhẹ tối ưu chi phí (nếu không set sẽ lấy theo provider)",
    )

    @model_validator(mode="after")
    def resolve_tier_models(self) -> Self:
        provider_defaults = {
            "openai": (self.openai_tier1_model, self.openai_tier2_model),
            "gemini": (self.gemini_tier1_model, self.gemini_tier2_model),
            "deepseek": (self.deepseek_tier1_model, self.deepseek_tier2_model),
            "mistral": (self.mistral_tier1_model, self.mistral_tier2_model),
        }
        default_t1, default_t2 = provider_defaults.get(
            self.llm_provider, (self.openai_tier1_model, self.openai_tier2_model)
        )
        if not self.tier1_model:
            self.tier1_model = default_t1
        if not self.tier2_model:
            self.tier2_model = default_t2
        return self
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
    supervisor_tool_call_limit: int = Field(
        default=20,
        gt=0,
        description="Giới hạn số lần gọi công cụ (tool calls) tối đa cho Supervisor trong một lần chạy",
    )
    supervisor_tool_call_thread_limit: int = Field(
        default=100,
        gt=0,
        description="Giới hạn số lần gọi công cụ (tool calls) tối đa cho Supervisor trong toàn bộ thread",
    )
    supervisor_model_call_limit: int = Field(
        default=20,
        gt=0,
        description="Giới hạn số lần gọi LLM (model calls) tối đa cho Supervisor trong một lần chạy",
    )
    supervisor_model_call_thread_limit: int = Field(
        default=100,
        gt=0,
        description="Giới hạn số lần gọi LLM (model calls) tối đa cho Supervisor trong toàn bộ thread",
    )
    max_conversation_history_messages: int = Field(
        default=40,
        gt=0,
        description="Ngưỡng số lượng tin nhắn tối đa kích hoạt tóm tắt để tránh tràn context window",
    )
    keep_recent_messages: int = Field(
        default=20,
        gt=0,
        description="Số lượng tin nhắn hội thoại gần nhất được giữ nguyên vẹn khi tóm tắt",
    )
    enable_context_summarization: bool = Field(
        default=True,
        description="Bật/tắt tính năng tự động tóm tắt ngữ cảnh cũ khi hội thoại kéo dài nhiều lượt",
    )

    # --- Dynamic Risk-based HITL Gatekeeper Policy ---
    hitl_enabled: bool = Field(
        default=True,
        description="Bật/tắt cơ chế đánh giá rủi ro và phê duyệt Human-In-The-Loop (HITL)",
    )
    hitl_budget_ratio_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Tỷ lệ dung lượng quét so với max_bytes_scanned kích hoạt HITL (mặc định: 0.4 = 40%)",
    )
    hitl_rows_threshold: int = Field(
        default=500_000,
        gt=0,
        description="Số lượng dòng quét ước tính tối đa cho phép chạy tự động mà không cần duyệt HITL",
    )
    hitl_heavy_tables: str = Field(
        default="lineitem,orders",
        description="Danh sách các bảng kích thước lớn (Heavy Tables) phân tách bằng dấu phẩy, cấu hình linh hoạt theo từng DB",
    )
    hitl_time_columns: str = Field(
        default="shipdate,orderdate,date,created_at,timestamp",
        description="Danh sách các cột phân vùng / mốc thời gian dùng để kiểm tra tính đầy đủ của bộ lọc WHERE",
    )

    @property
    def heavy_tables_set(self) -> set[str]:
        """Tập hợp các bảng lớn có rủi ro chi phí cao (chuẩn hóa viết thường)."""
        return {t.strip().lower() for t in self.hitl_heavy_tables.split(",") if t.strip()}

    @property
    def time_columns_set(self) -> set[str]:
        """Tập hợp tên các cột thời gian/phân vùng để kiểm tra điều kiện lọc (chuẩn hóa viết thường)."""
        return {c.strip().lower() for c in self.hitl_time_columns.split(",") if c.strip()}

    # --- Observability & Execution Traces ---
    enable_trace_logging: bool = Field(
        default=True,
        description="Bật/tắt tính năng lưu vết thực thi các Subagents vào thư mục outputs/",
    )
    trace_output_dir: str = Field(
        default="outputs",
        description="Đường dẫn thư mục lưu vết thực thi phiên truy vấn",
    )

    # --- LangSmith Tracing & Observability ---
    langchain_tracing_v2: bool = Field(
        default=False, description="Bật/tắt tính năng LangSmith Tracing v2"
    )
    langchain_api_key: str | None = Field(
        default=None, description="Khóa API của LangSmith"
    )
    langchain_project: str = Field(
        default="text2sql-agent", description="Tên project lưu vết trên LangSmith"
    )
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="Endpoint của LangSmith API",
    )


@lru_cache
def get_settings() -> Settings:
    """Hàm singleton lấy đối tượng cấu hình Settings được cache qua lru_cache."""
    return Settings()
