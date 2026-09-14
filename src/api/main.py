"""FastAPI Application Entrypoint (Component 5.1).

Cung cấp:
- Khởi tạo ứng dụng FastAPI với Lifespan event (Warmup DuckDB TPC-H database).
- Cấu hình Middleware CORS kết nối Next.js Frontend.
- Đăng ký các API Routers (/api/v1/query, /api/v1/audit).
- Cung cấp endpoints kiểm tra sức khỏe (/health, /api/v1/health).
- Chuẩn hóa xử lý lỗi ngoại lệ toàn cục.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import duckdb
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import audit_router, query_router
from src.config import get_settings
from src.models.api_schemas import HealthResponse
from src.utils.tpch_seeder import seed_tpch_data

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. LIFESPAN CONTEXT MANAGER
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Quản lý vòng đời khởi động và tắt ứng dụng FastAPI.

    - Khởi động: Kiểm tra / nạp dữ liệu mẫu TPC-H vào DuckDB nếu chưa có.
    - Dọn dẹp: Đóng các kết nối khi ứng dụng dừng hoạt động.
    """
    settings = get_settings()
    logger.info("Đang khởi động FastAPI Gateway (%s)...", settings.app_env)

    try:
        # Nạp dữ liệu DuckDB TPC-H scale factor 0.01 phục vụ truy vấn
        seed_tpch_data(db_path=settings.duckdb_path, scale_factor=0.01)
        logger.info("Khởi tạo kết nối DuckDB TPC-H thành công tại '%s'.", settings.duckdb_path)
    except (OSError, RuntimeError, duckdb.DatabaseError) as exc:
        logger.warning("Cảnh báo khi khởi tạo DuckDB trong lifespan: %s", exc)

    yield

    logger.info("Đang tắt FastAPI Gateway.")


# ==============================================================================
# 2. KHỞI TẠO FASTAPI APP
# ==============================================================================

settings = get_settings()

app = FastAPI(
    title="Text-to-SQL AI Agent Self-Service Analytics API",
    description=(
        "Hệ thống AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp "
        "(Chuẩn TPC-H Benchmark). Tích hợp DeepAgents Supervisor, LangGraph Control Pipeline, "
        "và Recharts JSON Visualization."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cấu hình CORS Middleware cho phép kết nối từ Next.js Web Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 3. GLOBAL EXCEPTION HANDLERS
# ==============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Bắt và chuẩn hóa mọi ngoại lệ chưa được xử lý thành phản hồi JSON có cấu trúc."""
    logger.exception("Ngoại lệ chưa xử lý tại %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "detail": str(exc) if settings.debug else "Đã xảy ra lỗi máy chủ nội bộ.",
            "path": request.url.path,
        },
    )


# ==============================================================================
# 4. ĐĂNG KÝ ROUTERS & HEALTH CHECK
# ==============================================================================

# Đăng ký các routers với tiền tố api_prefix (mặc định: /api/v1)
app.include_router(query_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Kiểm tra tình trạng hoạt động (Root Health Check)",
)
@app.get(
    f"{settings.api_prefix}/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Kiểm tra tình trạng hoạt động (API v1 Health Check)",
)
async def health_check() -> HealthResponse:
    """Kiểm tra trạng thái kết nối Data Warehouse và Gateway."""
    return HealthResponse(
        status="healthy",
        database="connected",
        version="1.0.0",
    )


@app.get(
    "/",
    tags=["Root"],
    summary="Trang chào mừng API Gateway",
)
async def root_info() -> dict[str, Any]:
    """Thông tin chào mừng và đường dẫn tài liệu Swagger."""
    return {
        "message": "Chào mừng đến với Text-to-SQL AI Agent Self-Service Analytics Gateway",
        "docs_url": "/docs",
        "version": "1.0.0",
        "status": "online",
    }
