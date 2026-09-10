# Danh Sách Các Quyết Định Kiến Trúc (Architectural Decision Records - ADR)

Thư mục này lưu trữ toàn bộ các biên bản quyết định kiến trúc kỹ thuật quan trọng của dự án **AI Agent Text-to-SQL Self-Service Analytics**, được lập theo chuẩn ADR để theo dõi lịch sử tiến hóa của hệ thống.

---

## Chỉ mục các bản ghi ADR

| Mã bản ghi | Tiêu đề quyết định | Trạng thái | Ngày quyết định | Tài liệu liên quan |
| :--- | :--- | :---: | :---: | :--- |
| [ADR-0001](file:///c:/text2sql-agent/docs/decisions/0001-hybrid-agent-architecture.md) | Lựa chọn Mô hình Hybrid (DeepAgents + LangGraph) và Chuẩn hóa trên TPC-H Benchmark | `Accepted` | 2026-09-08 | [agent-architecture-v2.md](file:///c:/text2sql-agent/docs/agent/agent-architecture-v2.md) |
| [ADR-0002](file:///c:/text2sql-agent/docs/decisions/0002-error-diagnostic-agent-and-modular-control-pipeline.md) | Bổ sung Node Agentic "Error Diagnostic Agent" và Mô-đun Hóa Package Control Pipeline (Kiến trúc v3.0) | `Accepted` | 2026-09-11 | [agent-architecture-v3.md](file:///c:/text2sql-agent/docs/agent/agent-architecture-v3.md), [agent-components-breakdown.md](file:///c:/text2sql-agent/docs/agent/agent-components-breakdown.md) |

---

## Quy trình cập nhật ADR

1. Khi có sự thay đổi quan trọng về mặt kiến trúc, cấu trúc module, chiến lược an ninh bảo mật hoặc mô hình tích hợp, bắt buộc phải tạo một bản ghi ADR mới.
2. Mã bản ghi được đánh số tăng dần theo định dạng `000X-<ten-ngan-gon>.md`.
3. Cập nhật chỉ mục trong file `README.md` này sau khi tạo bản ghi mới.
