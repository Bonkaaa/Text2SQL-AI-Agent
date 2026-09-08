# AGENTS.md — AI Agent Operating Manual & Repository Guide

> **Mục đích**: Tệp tin này đóng vai trò là bản quy ước kỹ thuật và hướng dẫn cố định cho AI Coding Assistants (đặc biệt là Antigravity Agent) khi đọc hiểu, sinh code, chỉnh sửa và kiểm thử trong repository `text2sql-agent`.

---

## 1. TỔNG QUAN DỰ ÁN & KIẾN TRÚC

- **Tên dự án**: AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp (Chuẩn TPC-H Benchmark - Phân phối & Chuỗi cung ứng).
- **Tài liệu nghiệp vụ & kiến trúc gốc**:
  - Đề tài & yêu cầu chấm điểm: `DETAI.md`
  - Thiết kế kiến trúc chi tiết v2.0: `docs/agent-architecture-v2.md`
  - Đặc tả yêu cầu sản phẩm: `docs/PRD.md`
  - Thiết kế kiến trúc hệ thống 3 tầng: `docs/ARCHITECTURE.md`
  - Từ điển dữ liệu & Schema 8 bảng TPC-H: `docs/DATABASE_SCHEMA.md`
- **Mô hình cốt lõi (Hybrid Architecture)**:
  1. **Tầng suy luận (DeepAgents Harness)**: Supervisor điều phối + Question Clarification + Schema & Categorical Value Retriever + SQL Generator + Response Synthesizer.
  2. **Tầng kiểm soát tất định (LangGraph Control Pipeline)**: Đóng gói dưới dạng Subgraph kiểm duyệt cứng: AST Sanitizer (`sqlglot`), RBAC Policy, Cost Guard (Dry-run), HITL Approval (`interrupt`), Warehouse Executor (Timeout/Limit) và Audit Logger.

---

## 2. QUY TẮC CỐT LÕI & ĐIỀU TUYỆT ĐỐI TRÁNH (CRITICAL GUARDRAILS)

Các nguyên tắc an toàn này có độ ưu tiên cao nhất, Agent phải tuân thủ tuyệt đối:

1. **CHỈ CHO PHÉP TRUY VẤN ĐỌC (`SELECT` ONLY)**:
   - Tuyệt đối không sinh hoặc cho phép thực thi bất kỳ câu lệnh biến đổi dữ liệu nào: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`.
   - Luôn sử dụng AST parser (`sqlglot`) để kiểm tra root expression trước khi gửi truy vấn đến warehouse.
2. **KHÔNG HARDCODE THÔNG TIN NHẠY CẢM**:
   - Tuyệt đối không hardcode API keys, mật khẩu database, connection strings trong code hoặc commits. Mọi cấu hình đọc qua `src/config.py` (sử dụng `pydantic-settings` và `.env`).
3. **CÔ LẬP PHIÊN TRÊN VIRTUAL FILESYSTEM / STATE**:
   - Khi xử lý context hoặc file trung gian (`schema_context.md`, `draft_sql.sql`), **luôn gắn liền với `thread_id` / `session_id`** của request.
   - Tuyệt đối không dùng file tĩnh dùng chung trên ổ đĩa để tránh ghi đè dữ liệu khi có nhiều người dùng đồng thời.
4. **VÒNG LẶP SỬA LỖI CÓ CHẶN NGƯỠNG (`MAX_RETRIES = 3`)**:
   - Cơ chế tự sửa lỗi truy vấn (Self-correction) không được vượt quá 3 lần retry. Nếu thất bại sau 3 lần, bắt buộc kích hoạt graceful failure và log audit.
5. **GIỮ NGUYÊN KIẾN TRÚC TẤT ĐỊNH**:
   - Không chuyển các bước kiểm duyệt an toàn (RBAC, Dry-run cost, Audit Log) sang cho LLM tự quyết. Các bước này bắt buộc nằm trong LangGraph deterministic nodes bằng code thuần.

---

## 3. MÔI TRƯỜNG & LỆNH THỰC THI (ENVIRONMENT & COMMANDS)

Hệ điều hành môi trường: **Windows (PowerShell)**. AI Agent sử dụng các lệnh chuẩn sau:

### 3.1. Quản lý Môi trường ảo & Dependencies
```powershell
# Kích hoạt virtual environment
.venv\Scripts\Activate.ps1

# Cài đặt / cập nhật dependencies
pip install -r requirements.txt

# Cài đặt package ở chế độ editable (nếu dùng pyproject.toml)
pip install -e .
```

### 3.2. Chạy Ứng dụng Backend & Frontend
```powershell
# Khởi chạy FastAPI Backend (Dev server)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Khởi chạy Frontend (Next.js)
npm --prefix src/frontend run dev
```

### 3.3. Kiểm tra Chất lượng Code & Định dạng (Lint & Format)
```powershell
# Kiểm tra lint bằng Ruff
ruff check .

# Tự động sửa lỗi lint có thể fix
ruff check --fix .

# Format code bằng Ruff
ruff format .
```

### 3.4. Kiểm thử (Testing) & Đánh giá (Eval)
```powershell
# Chạy toàn bộ unit test
pytest tests/ -v

# Chạy test có đo độ phủ code (coverage)
pytest tests/ --cov=src --cov-report=term-missing

# Chạy bộ benchmark đánh giá độ chính xác SQL (Spider-like benchmark)
python -m evals.benchmark_runner --dataset evals/datasets/benchmark_vi.json
```

---

## 4. CẤU TRÚC THƯ MỤC DỰ ÁN (PROJECT LAYOUT)

```
text2sql-agent/
├── AGENTS.md                  # Hướng dẫn kỹ thuật cố định cho AI Agent (Tệp này)
├── DETAI.md                   # Đề tài và tiêu chí chấm điểm đồ án
├── README.md                  # Giới thiệu dự án dành cho con người
├── requirements.txt           # Danh sách thư viện Python
├── pyproject.toml             # Cấu hình build & packaging
├── ruff.toml                  # Cấu hình linter & formatter
├── .env.example               # Mẫu biến môi trường
├── docs/                      # Tài liệu thiết kế kỹ thuật
│   ├── agent-architecture-v2.md # Kiến trúc chi tiết hệ thống v2.0
│   └── data-01-agent-architecture.md
├── evals/                     # Bộ benchmark & kịch bản kiểm thử Execution Accuracy
│   ├── datasets/              # 50 câu hỏi mẫu tiếng Việt kèm ground-truth SQL
│   └── benchmark_runner.py    # Runner đo VSR, EX, Self-correction rate
├── src/                       # Mã nguồn ứng dụng
│   ├── config.py              # Pydantic Settings đọc cấu hình .env
│   ├── agents/                # Tầng điều phối & reasoning (DeepAgents / LangGraph)
│   │   ├── supervisor.py      # Deep Agent Supervisor & Todo planning
│   │   ├── clarification.py   # Intent & Ambiguity check loop
│   │   ├── schema_retriever.py# Vector search DDL + Categorical value indexing
│   │   ├── sql_generator.py   # SQL authoring with error-context injection
│   │   ├── control_pipeline.py# LangGraph Deterministic Control Subgraph
│   │   └── synthesizer.py     # Data table, Recharts schema, insight explanation
│   ├── api/                   # FastAPI backend endpoints
│   │   ├── main.py            # Khởi tạo FastAPI app, middleware, routers
│   │   ├── routes/            # Endpoints: /ask, /approve, /history, /metrics
│   │   └── dependencies.py    # Auth, DB sessions, state checkpointers
│   ├── models/                # Pydantic schemas & Database ORM / State models
│   ├── utils/                 # Helpers: AST parser, DB clients, token counter
│   └── frontend/              # Web UI Next.js + Recharts (nếu có trong repo)
└── tests/                     # Unit tests & integration tests
    ├── test_agents/           # Test từng agent và node LangGraph
    ├── test_ast_security.py   # Test chặn SQL injection và DDL/DML
    └── test_api.py            # Test API endpoints và HITL interrupt flow
```

---

## 5. QUY CHUẨN LẬP TRÌNH (CODING CONVENTIONS)

1. **Phiên bản Python & Type Hints**:
   - Sử dụng **Python 3.11+**.
   - Mọi hàm và phương thức bắt buộc có đầy đủ type annotations (VD: `def generate_sql(prompt: str, context: SchemaContext) -> GeneratedSQLResult:`).
2. **Quản lý Cấu hình & Schema**:
   - Sử dụng **Pydantic v2** cho validation dữ liệu đầu vào/ra của API và state.
   - Biến môi trường quản lý tập trung trong `src/config.py` thông qua `BaseSettings`.
3. **Bất đồng bộ (Async First)**:
   - Toàn bộ route FastAPI, hàm gọi LLM (LangChain/DeepAgents), và truy vấn Warehouse/Vector DB phải viết theo dạng `async / await`.
4. **Xử lý Lỗi & Exception Handling**:
   - Bắt lỗi cụ thể (specific exceptions: `sqlglot.errors.ParseError`, `duckdb.DatabaseError`, `google.api_core.exceptions.GoogleAPICallError`).
   - Không dùng bare `except: pass`. Mọi lỗi từ control pipeline đều phải chuẩn hóa thành cấu trúc error dictionary gửi về node `ERR`.
5. **Ghi Log (Logging)**:
   - Dùng thư viện `loguru` hoặc `logging` chuẩn Python.
   - Luôn log có cấu trúc (structured JSON log) kèm `trace_id` và `thread_id` để tiện debug.

---

## 6. QUY TRÌNH KHI AI AGENT THỰC HIỆN TÁC VỤ (EXECUTION WORKFLOW)

Khi nhận một task từ người dùng, Agent thực hiện tuần tự:

1. **Hiểu rõ yêu cầu**: Đọc kỹ bối cảnh, đối chiếu với `docs/agent-architecture-v2.md` và `DETAI.md`.
2. **Kiểm tra hiện trạng code**: Sử dụng các công cụ tìm kiếm và đọc file (`grep_search`, `view_file`) để nắm rõ các hàm và module đã có sẵn trước khi viết mới.
3. **Viết code tập trung & tối giản**: Không thêm phụ thuộc thư viện không cần thiết; tuân thủ cấu trúc thư mục tại Mục 4.
4. **Tự kiểm thử & Xác minh (Verification Step)**:
   - Chạy `ruff check .` để đảm bảo code không có lỗi cú pháp hoặc vi phạm linting.
   - Chạy `pytest tests/` (hoặc test liên quan trực tiếp đến module vừa sửa) để bảo đảm tính đúng đắn.
5. **Báo cáo kết quả ngắn gọn**: Trình bày rõ các file đã tạo/sửa, lý do thay đổi và kết quả test đã chạy.
