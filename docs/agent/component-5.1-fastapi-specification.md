# Đặc Tả Kỹ Thuật & Kế Hoạch Triển Khai Component 5.1: FastAPI Gateway & Endpoints

> **Tài liệu căn cứ**:
> - `DETAI.md` (Yêu cầu đồ án)
> - `docs/agent/agent-components-breakdown.md` (Component 5.1)
> - `docs/agent/end2end-execution-flow.md`
> - `AGENTS.md` (Quy ước kỹ thuật)

---

## 1. Mục Tiêu & Phạm Vi

Component 5.1 xây dựng tầng API Gateway của hệ thống **Text-to-SQL Self-Service Analytics**:
- Cung cấp RESTful API bất đồng bộ chuẩn hiệu năng cao (`async/await`) với **FastAPI**, **Pydantic v2**, và **Uvicorn**.
- Đóng vai trò là điểm tiếp nhận yêu cầu từ Web Frontend (Next.js), chuyển tiếp tới **Deep Agent Supervisor** (`arun_supervisor`).
- Hỗ trợ đầy đủ luồng phê duyệt con người **Human-in-the-Loop (HITL)** (`/api/v1/query/approve`).
- Bảo vệ truy cập theo vai trò **RBAC** (ví dụ: chỉ `ADMIN` mới được truy cập `/api/v1/audit/logs`).
- Trả về dữ liệu có cấu trúc: Trạng thái, Bảng dữ liệu, Cấu hình Recharts JSON, và Business Insight.

---

## 2. Đặc Tả Chi Tiết Các Endpoints

### 2.1. Router `/api/v1/query` (`src/api/routes/query.py`)

#### 1. `POST /api/v1/query/ask`
- **Request Body (`AskQueryRequest`)**:
  ```python
  class AskQueryRequest(BaseModel):
      question: str = Field(..., min_length=1, description="Câu hỏi tự nhiên của người dùng")
      session_id: str | None = Field(default=None, description="Mã phiên làm việc")
      user_id: str = Field(default="default_user", description="Định danh người dùng")
      role: UserRole = Field(default=UserRole.ANALYST, description="Vai trò người dùng (ANALYST, ADMIN)")
  ```
- **Xử lý**:
  - Tạo `UserContext(user_id=..., session_id=..., role=...)`.
  - Gọi `arun_supervisor(question, user_context=..., session_id=...)`.
  - Nhận diện trạng thái trả về:
    * `COMPLETED`: Đã có câu trả lời, bảng dữ liệu, cấu hình Recharts JSON và Business insight.
    * `CLARIFICATION_REQUIRED`: Câu hỏi mơ hồ, trả về câu hỏi làm rõ và danh sách tùy chọn gợi ý A, B, C.
    * `PENDING_APPROVAL`: Câu truy vấn chi phí cao kích hoạt HITL, trả về câu lệnh SQL, ước lượng chi phí và cờ `requires_hitl=True`.
    * `ERROR`: Xảy ra sự cố, trả về thông báo lỗi thân thiện.
- **Response Body (`QueryResponse`)**:
  ```python
  class QueryResponse(BaseModel):
      session_id: str
      status: Literal["COMPLETED", "CLARIFICATION_REQUIRED", "PENDING_APPROVAL", "ERROR"]
      question: str
      is_ambiguous: bool = False
      clarification_question: str | None = None
      suggested_options: list[str] = Field(default_factory=list)
      final_answer: str | None = None
      sql: str | None = None
      data: list[dict[str, Any]] | None = None
      columns: list[str] | None = None
      recharts_config: dict[str, Any] | None = None
      execution_time_ms: float = 0.0
  ```

#### 2. `POST /api/v1/query/approve`
- **Request Body (`ApprovalRequest`)**:
  ```python
  class ApprovalRequest(BaseModel):
      session_id: str = Field(..., description="Mã phiên đang tạm dừng chờ duyệt")
      approved: bool = Field(..., description="Quyết định duyệt: True (chấp thuận) hoặc False (từ chối)")
      rejection_reason: str | None = Field(default=None, description="Lý do từ chối nếu approved=False")
  ```
- **Xử lý**:
  - Resume đồ thị StateGraph từ chốt chặn `interrupt()` của LangGraph qua `Command(resume={"approved": approved, ...})`.
  - Tiếp tục thực thi và trả về kết quả truy vấn hoặc trạng thái bị từ chối.

#### 3. `GET /api/v1/query/history`
- **Query params**: `session_id: str`
- **Xử lý**: Đọc danh sách câu hỏi và artifacts trong thư mục `outputs/{timestamp}_{session_id[:8]}/` thông qua `SessionTracer`.

---

### 2.2. Router `/api/v1/audit` (`src/api/routes/audit.py`)

#### 1. `GET /api/v1/audit/logs`
- **Bảo vệ RBAC**: Kiểm tra vai trò của người gọi. Chỉ `UserRole.ADMIN` mới có quyền truy cập. Nếu là `ANALYST`, trả về `HTTP 403 Forbidden`.
- **Query params**: `limit: int = 50`, `offset: int = 0`, `status: str | None = None`.
- **Xử lý**: Đọc các dòng log JSON từ file `data/logs/audit.jsonl` qua `AuditLogger`.

---

### 2.3. Health Check & Middleware (`src/api/main.py`)
- **`GET /health`** & **`GET /api/v1/health`**:
  - Kiểm tra trạng thái DuckDB và hệ thống.
  - Trả về `{"status": "healthy", "database": "connected", "version": "1.0.0"}`.
- **CORS Middleware**: Cho phép Frontend Next.js (`http://localhost:3000`).
- **Global Exception Handler**: Bắt ngoại lệ chưa xử lý, format JSON chuẩn và ghi loguru/logging.

---

## 3. Kế Hoạch Triển Khai Từng Bước (Roadmap 5 Bước TDD)

1. **Bước 1: Cài đặt Dependencies**:
   - Thêm `fastapi>=0.115.0`, `uvicorn[standard]>=0.30.0`, `httpx>=0.27.0` vào `requirements.txt`.
   - Chạy `pip install -r requirements.txt`.
2. **Bước 2: Xây dựng Schemas Pydantic**:
   - Tạo file `src/models/api_schemas.py` chứa các request/response models.
3. **Bước 3: Xây dựng Dependencies Injection (`src/api/dependencies.py`)**:
   - Trích xuất `UserContext` từ headers/body.
   - Kiểm tra quyền `require_admin_role`.
   - Cung cấp singleton `DuckDBConnector` và `AuditLogger`.
4. **Bước 4 (TDD RED)**:
   - Tạo `tests/test_api.py` với test suite hoàn chỉnh dùng `httpx.AsyncClient`.
   - Xác nhận chạy test gặp lỗi đỏ (do chưa có route/main).
5. **Bước 5 (TDD GREEN & VERIFY)**:
   - Triển khai `src/api/routes/query.py`, `src/api/routes/audit.py`, `src/api/main.py`.
   - Chạy `pytest tests/test_api.py` (xanh toàn bộ).
   - Chạy toàn bộ test suite dự án và `ruff check .`.
