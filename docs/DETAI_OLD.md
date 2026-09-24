# Tên Đề Tài
AI Agent Text-to-SQL Self-Service Analytics cho dữ liệu doanh nghiệp (Chuẩn TPC-H Benchmark)

# Mô Tả Bài Toán
📍 **Thực trạng**: Nhân viên nghiệp vụ (Kinh doanh, Mua hàng, Kế hoạch chuỗi cung ứng, Quản lý kho) tại Doanh nghiệp phân phối & thương mại (chuẩn hóa trên bộ dữ liệu TPC-H Benchmark) cần số liệu bán hàng, tình trạng giao trễ, mức chiết khấu và tồn kho nhưng phải chờ đội Data viết SQL, thời gian phản hồi từ 2 đến 5 ngày.

🎯 **Vấn đề**: Xây dựng AI Agent nhận câu hỏi tiếng Việt tự nhiên, tự lập kế hoạch truy vấn, sinh SQL đúng schema (8 bảng TPC-H), chạy trên warehouse (DuckDB / BigQuery), trả về bảng + biểu đồ Recharts + diễn giải insight kinh doanh; biết hỏi lại khi câu hỏi mơ hồ (Clarification Loop) và ghi nhớ ngữ cảnh hội thoại đa lượt.

🔒 **Ràng buộc**:
- **HITL (Human-In-The-Loop)**: Người dùng xem SQL sinh ra, lời giải thích và ước tính chi phí để xác nhận trước khi chạy thật trên bảng lớn (`lineitem`).
- **Governance & RBAC**: Phân quyền theo vai trò (`Analyst` chỉ đọc các trường nghiệp vụ, cấm PII/tài chính nhạy cảm; `Admin` quản trị toàn quyền và xem audit log).
- **Cost Guard**: Giới hạn chi phí quét dữ liệu (bytes scanned) và cảnh báo/chặn khi vượt ngưỡng quota.
- **Độ chính xác đo lường được**: Đo Execution Accuracy (EX) trên tập benchmark câu hỏi mẫu.

# Tech stack gợi ý
- **LLM**: Claude 3.5 Sonnet / GPT-4o (SQL Generation) + Claude 3.5 Haiku / GPT-4o-mini (Reasoning & Synthesis)
- **Agent Framework**: DeepAgents điều phối (Planning, Virtual Filesystem, Subagent isolation) + LangGraph Control Pipeline (AST Sanitizer, RBAC, Cost Guard, HITL, Audit Log)
- **Vector DB**: Qdrant / pgvector lưu embedding schema, few-shot examples và categorical values
- **Warehouse**: DuckDB (môi trường dev/local với native extension TPC-H `dbgen`) & Google BigQuery Sandbox (demo dryRun bytes scanned)
- **Semantic Layer**: dbt semantic metrics model (công thức Doanh thu thuần, Tỷ lệ hoàn hàng, Giá trị tồn kho)
- **Backend**: FastAPI (Async, Server-Sent Events streaming)
- **Frontend**: Next.js 14 + Tailwind CSS + Recharts
- **Deploy**: Vercel (Frontend) + Render / Railway / Docker Compose (Backend)
- **Auth**: Supabase Auth (JWT role-based).

# Yêu cầu đầu ra (Cơ bản + Nâng cao)

### Cơ bản:
- Web deploy online, đăng nhập 2 vai trò (`Analyst` / `Admin`).
- Agent nhận câu hỏi tiếng Việt tự nhiên $\rightarrow$ lập kế hoạch $\rightarrow$ sinh SQL đúng schema 8 bảng TPC-H $\rightarrow$ chạy trên warehouse $\rightarrow$ trả về bảng dữ liệu + biểu đồ tương tác + giải thích insight.
- Cơ chế HITL duyệt câu lệnh SQL và xem trước chi phí quét trước khi thực thi.
- Lưu nhật ký truy vấn (Audit Log) đầy đủ.

### Nâng cao:
- Multi-agent phối hợp: Agent sửa lỗi SQL tự động retry khi query fail (có chặn ngưỡng $\le 3$ lần kèm error context).
- Clarification Loop: Chủ động hỏi lại người dùng khi câu hỏi thiếu thông tin lọc (khu vực, năm, mặt hàng).
- Bộ eval benchmark đo Execution Accuracy (EX) và Valid SQL Rate (VSR) trên tập 50 câu hỏi mẫu (dựa trên 22 mẫu TPC-H chuẩn Spider-like).
- Ước tính và giới hạn chi phí quét (bytes scanned trên bảng lớn `lineitem`) qua BigQuery dryRun và DuckDB explain.