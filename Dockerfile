# ==============================================================================
# Multi-stage Dockerfile cho Text-to-SQL AI Agent Backend (FastAPI + LangGraph)
# ==============================================================================

# --- Stage 1: Build & Dependency Resolution ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Cài đặt công cụ biên dịch nếu thư viện yêu cầu build wheel từ source
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt dependencies vào thư mục người dùng
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# --- Stage 2: Minimal & Secure Production Runtime ---
FROM python:3.11-slim AS runtime

WORKDIR /app

# Cài đặt curl phục vụ container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Tạo nhóm và user không có đặc quyền root (Non-root user)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Sao chép các package Python đã cài đặt từ stage builder
COPY --from=builder /root/.local /home/appuser/.local

# Thiết lập biến môi trường
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Tạo sẵn các thư mục dữ liệu và phân quyền cho appuser
RUN mkdir -p /app/data/logs /app/outputs && \
    chown -R appuser:appgroup /app

# Sao chép mã nguồn backend
COPY --chown=appuser:appgroup src/ /app/src/
COPY --chown=appuser:appgroup pyproject.toml /app/

# Chuyển sang user không đặc quyền để bảo mật runtime
USER appuser

# Mở cổng API Gateway
EXPOSE 8000

# Kiểm tra sức khỏe định kỳ container qua endpoint /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Khởi chạy FastAPI server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
