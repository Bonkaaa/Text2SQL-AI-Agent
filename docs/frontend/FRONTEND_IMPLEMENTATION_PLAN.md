# KẾ HOẠCH TRIỂN KHAI TOÀN DIỆN FRONTEND TEXT2SQL SELF-SERVICE ANALYTICS
## (AI Data Workspace Implementation Plan)

> **Mã tài liệu**: `docs/frontend/FRONTEND_IMPLEMENTATION_PLAN.md`  
> **Ngày lập**: 09/10/2026  
> **Trạng thái**: Bản kế hoạch kỹ thuật chi tiết đã phê duyệt (Implementation-Ready Specification)  
> **Tài liệu tham chiếu chính**:
> - Prototype trực quan: [`text2sql_frontend_blueprint.html`](file:///d:/Text2SQL-AI-Agent/text2sql_frontend_blueprint.html)
> - Đặc tả thiết kế UI/UX: [`Text2SQL_Frontend_Design_Spec.docx`](file:///d:/Text2SQL-AI-Agent/Text2SQL_Frontend_Design_Spec.docx)
> - Quy chuẩn Agent: [`AGENTS.md`](file:///d:/Text2SQL-AI-Agent/AGENTS.md)
> - Kiến trúc Agent v4.0 & Schema 24 bảng: [`docs/agent-architecture-v2.md`](file:///d:/Text2SQL-AI-Agent/docs/agent-architecture-v2.md) và [`docs/DATABASE_SCHEMA.md`](file:///d:/Text2SQL-AI-Agent/docs/DATABASE_SCHEMA.md)
> - Skills áp dụng: `ui-ux-pro-max` (Enterprise Data-Dense & Accessibility), `frontend-design` (Anti-AI Clichés), `ui-styling` (Tailwind + Radix/shadcn token pattern), `ponytail` (YAGNI & tinh gọn tối đa).

---

## 1. TỔNG QUAN & ĐỊNH HƯỚNG SẢN PHẨM

### 1.1. Định vị Sản phẩm: "Enterprise AI Data Workspace"
Hệ thống **AI Agent Text-to-SQL Self-Service Analytics** phục vụ phân tích dữ liệu bán lẻ đa kênh chuẩn **TPC-DS Benchmark (24 bảng)** trên nền kho dữ liệu DuckDB.
Giao diện frontend được định vị là một **AI Data Workspace** chuyên nghiệp (tương tự trải nghiệm của *Snowflake Snowsight, Metabase, Supabase Studio và Linear*), chứ **không phải một khung chat tiêu dùng thông thường (Consumer Chatbot)**:
1. **Lấy Dữ liệu & Kết quả làm Trung tâm (Data-First)**: Khung chat chỉ là nơi nhập lệnh tự nhiên; giá trị cốt lõi nằm ở **khung kết quả đa chiều (Result Canvas)** với bảng số liệu tương tác, biểu đồ Recharts, câu lệnh SQL có kiểm duyệt an toàn và phân tích insight.
2. **Minh bạch & Kiểm chứng Tuyệt đối (Evidence over Polish)**: Mọi kết luận của Agent đều đi kèm bằng chứng cụ thể: số dòng trả về, thời gian thực thi (ms), câu SQL đã chạy, và nhật ký các bước xử lý (Trace).
3. **Thẩm mỹ Doanh nghiệp Tinh tế (Clean Minimalist Enterprise)**: Giao diện sáng sủa (Light Theme trang nhã), hỗ trợ Dark Mode cao cấp, độ tương phản cao, mật độ thông tin tối ưu (Data-dense), loại bỏ hoàn toàn các chi tiết rườm rà (không quả cầu 3D phát sáng, không viền neon loang lổ, không timeline suy luận giả định).

---

## A. ĐÁNH GIÁ HIỆN TRẠNG CODEBASE (CURRENT-STATE ASSESSMENT)

### 1. Năng lực Backend & Điểm Chạm API Sẵn Có

Backend FastAPI ([`src/api/main.py`](file:///d:/Text2SQL-AI-Agent/src/api/main.py)) đã sẵn sàng phục vụ cho ứng dụng với các endpoints chính:

| Endpoint | Giao thức / Định dạng | Chức năng thực tế trong Codebase |
|---|---|---|
| `POST /api/v1/query/ask` | JSON HTTP Request / Response | Tiếp nhận câu hỏi, điều phối DeepAgents Supervisor và LangGraph Control Pipeline, trả về [`QueryResponse`](file:///d:/Text2SQL-AI-Agent/src/models/api_schemas.py#L54-L195). |
| `POST /api/v1/query/approve` | JSON HTTP Request / Response | Nhận quyết định phê duyệt Human-in-the-loop (HITL) khi truy vấn bị chặn tại `interrupt()`. Yêu cầu quyền `Admin`. |
| `GET /api/v1/query/history` | Query param `session_id` | Đọc danh sách các tệp artifact và vết thực thi của một phiên làm việc cụ thể. |
| `GET /api/v1/audit/logs` | Query params `limit`, `offset` | Truy xuất toàn bộ nhật ký kiểm toán hệ thống từ `AuditLogger` (câu hỏi, SQL, thời gian chạy, lỗi). Yêu cầu quyền `Admin`. |
| `GET /health` & `/api/v1/health` | JSON | Kiểm tra kết nối DuckDB và tình trạng hoạt động của API Gateway. |

### 2. Cấu Trúc Hợp Đồng Dữ Liệu `QueryResponse` (Kiến trúc v4.0 Evolution)

Backend cung cấp dữ liệu định kiểu phân lớp rõ ràng ([`src/models/api_schemas.py`](file:///d:/Text2SQL-AI-Agent/src/models/api_schemas.py) và [`src/models/artifacts.py`](file:///d:/Text2SQL-AI-Agent/src/models/artifacts.py)):
- **Lifecycle Status (`status`)**:
  - `COMPLETED` / `SUCCESS`: Truy vấn hoàn tất thành công.
  - `CLARIFICATION_REQUIRED`: Câu hỏi bị mơ hồ, cần hỏi lại người dùng kèm danh sách `suggested_options` (Chips A, B, C).
  - `PENDING_APPROVAL`: Truy vấn bị dừng bởi chốt chặn an toàn HITL (chi phí cao hoặc truy vấn lớn), cần Admin duyệt.
  - `SECURITY_BLOCKED`: Câu hỏi vi phạm an toàn (Prompt Injection, Data Mutation hoặc Out-of-Domain), trả về `refusal_reason`.
  - `ERROR`: Lỗi thực thi SQL hoặc lỗi hệ thống, trả về `error`.
- **Gói hiển thị đa chiều (`response_package`)**:
  - `direct_answer`: Tóm tắt câu trả lời trực diện.
  - `detailed_insight`: Danh sách luận điểm phân tích định lượng.
  - `layout`: Bố cục đề xuất (`focus`, `stacked`, `dashboard_grid`).
  - `artifacts`: Danh sách các khối dữ liệu định kiểu (Discriminated Union):
    - `kpi`: Thẻ chỉ số (`title`, `value`, `unit`, `delta`, `delta_type`).
    - `chart`: Cấu hình Recharts (`chart_type`: bar/line/area/pie, `x_key`, `y_keys`, `series_labels`, `data`).
    - `table`: Bảng dữ liệu đã hydrate (`title`, `columns`, `column_formats`, `rows`, `total_row_count`).
    - `evidence`: Dẫn chứng luận điểm với câu SQL và mẫu số liệu.
    - `callout`: Thông báo, cảnh báo hoặc lưu ý nghiệp vụ (`variant`: info/warning/error/no_data).
- **Tầng dữ liệu phẳng trực tiếp (Legacy Compat)**: `sql`, `data`, `columns`, `recharts_config`, `insight`, `visualization`.
- **Tầng giám sát & thực thi (Trace & Telemetry)**: `tasks` (danh sách AnalysisTask), `artifacts` (danh sách QueryArtifacts với thời gian chạy và số dòng), `execution_time_ms`, `estimated_cost_bytes`.

### 3. Bảng Ma Trận Phân Tách Năng Lực (Capabilities Matrix)

| Năng lực cần cho Frontend | Trạng thái Backend | Hướng xử lý đề xuất |
|---|---|---|
| **Hỏi đáp tự nhiên, sinh SQL, render biểu đồ Recharts, bảng dữ liệu** | **ĐÃ CÓ ĐẦY ĐỦ** (`POST /api/v1/query/ask`) | Tích hợp trực tiếp với API hiện tại. |
| **Gợi ý làm rõ khi câu hỏi mơ hồ (Clarification Chips)** | **ĐÃ CÓ ĐẦY ĐỦ** (`CLARIFICATION_REQUIRED` + `suggested_options`) | Render chips A, B, C tương tác, click để gửi câu hỏi làm rõ. |
| **Phê duyệt con người HITL (Approval Gate)** | **ĐÃ CÓ ĐẦY ĐỦ** (`POST /api/v1/query/approve`) | Banner cảnh báo + nút Phê duyệt / Từ chối (gắn quyền Admin). |
| **Hiển thị Trace & Telemetry thực tế** | **ĐÃ CÓ ĐẦY ĐỦ** (`tasks`, `artifacts`, `execution_time_ms`) | Render cây thực thi thật từ metadata backend trong tab Trace. |
| **Xác thực người dùng (Auth)** | **Header-based RBAC** (`X-User-Id`, `X-User-Role`, `X-Admin-Token`) | Màn hình Login quản lý session ở Client State/Storage, inject header tự động. Không cần viết lại OAuth2/JWT ở backend trong giai đoạn này. |
| **Khám phá Schema 24 bảng TPC-DS** | **Có DDL trong code Python**, chưa có REST endpoint | **Thêm 1 endpoint nhẹ** `GET /api/v1/schema` ở backend (kèm fallback bundle tĩnh catalog phía frontend). |
| **Lịch sử truy vấn toàn cục (Query History)** | Có `GET /api/v1/audit/logs` (toàn cục) và `/history` (theo session) | Kết hợp local session history với `GET /api/v1/audit/logs` khi có quyền Admin. |
| **Lưu câu truy vấn (Saved Queries)** | **CHƯA CÓ** persistence API | Lưu trữ bền vững tại Client (`localStorage`) qua Repository Pattern, sẵn sàng gắn backend REST API sau này mà không sửa UI. |
| **Quản lý đa Database Connections** | DuckDB TPC-DS là nguồn duy nhất | Hiển thị thông tin kết nối hoạt động của DuckDB TPC-DS (24 bảng), chưa cần xây dựng CRUD kết nối database ảo. |

---

## B. CẤU TRÚC TRANG & KIẾN TRÚC THÔNG TIN (PAGE STRUCTURE & INFORMATION ARCHITECTURE)

Dựa trên nguyên mẫu HTML và áp dụng nguyên tắc **YAGNI (Ponytail)**: Giữ toàn bộ các góc nhìn `Answer`, `Table`, `Chart`, `SQL`, `Trace` nằm trong thanh Tab của trang **Workspace**, tránh tạo các trang độc lập gây phân tán ngữ cảnh.

### 1. Sơ Đồ Điều Hướng & Cấu Trúc Tuyến Đường (Route Map)

```
/ (Root) ─── Auto-redirect ───► /workspace
│
├── (auth)/
│   └── /login                    # Đăng nhập & Lựa chọn vai trò (Analyst / Admin)
│
└── (app)/                        # Layout chung có Sidebar cố định & Topbar
    ├── /workspace                [P0] # Trung tâm hỏi đáp dữ liệu & Canvas kết quả 5 góc nhìn
    ├── /data-sources             [P0] # Trạng thái DuckDB & Schema Explorer 24 bảng TPC-DS
    ├── /history                  [P1] # Lịch sử các lần thực thi truy vấn (lọc, tìm kiếm, rerun)
    ├── /saved-queries            [P1] # Quản lý câu hỏi & biểu đồ đã lưu (open, rerun, delete)
    ├── /dashboard                [P2] # Tổng quan chỉ số sử dụng (KPIs, xu hướng, insight ghim)
    └── /settings                 [P2] # Tùy chỉnh người dùng, query preferences & Developer mode
```

### 2. Đặc Tả Chi Tiết Từng Trang

#### Trang 1: Workspace (`/workspace`) — **Ưu tiên P0 (Cốt lõi)**
- **Mục đích**: Trang quan trọng nhất của hệ thống, nơi nhân viên phân tích đặt câu hỏi và tương tác với kết quả.
- **Bố cục 2 cột (Adaptive Split Layout ~45/55)**:
  - **Cột Trái (Conversation Panel)**:
    - *Header*: Tiêu đề phiên phân tích, chỉ báo nguồn dữ liệu đang kết nối (`AdventureWorks / DuckDB TPC-DS`), nút "New conversation".
    - *Message Thread*: Luồng hội thoại cuộn mượt mà:
      - Tin nhắn người dùng (User Bubble).
      - Tin nhắn phản hồi của Agent (Assistant Message): hiển thị direct answer, các thẻ chỉ số inline stats, danh sách các bước thực thi tóm tắt (`Schema retrieval 42ms`, `SQL validated 1.2s`, `Query executed 186ms`).
      - *Clarification Chips*: Khi câu hỏi mơ hồ, hiển thị câu hỏi làm rõ cùng các nút tùy chọn A, B, C để bấm chọn gửi lại.
      - *HITL Approval Banner*: Khi truy vấn rơi vào diện cần duyệt, hiển thị cảnh báo chi phí quét và nút **[Phê duyệt]** / **[Từ chối]**.
    - *Query Composer*: Khung nhập câu hỏi nhiều dòng, phím tắt `Enter` gửi, `Shift+Enter` xuống dòng, nút gửi có icon loading khi đang xử lý, gợi ý các câu hỏi mẫu nghiệp vụ.
  - **Cột Phải (Result Canvas Panel)**:
    - *Header*: Tên kết quả phân tích, badge trạng thái (`Completed`, `Pending Approval`, `Failed`), metadata thời gian xử lý và số dòng trả về, nút xuất dữ liệu (Export).
    - *Tab Bar chuyển đổi 5 góc nhìn*:
      - **Answer View**: Callout tóm tắt điều hành, các chỉ số KPI lớn (`delta_type`), danh sách các điểm rút ra (`detailed_insight`), cách thức tính toán số liệu.
      - **Table View**: Bảng số liệu chuẩn định dạng số (`tabular-nums`), phân trang, nút Copy bảng và nút xuất file CSV.
      - **Chart View**: Render biểu đồ Recharts tương tác mượt mà (Bar / Line / Area / Pie), thanh công cụ chọn loại biểu đồ và nút lưu biểu đồ.
      - **SQL View**: Khung codeblock màu tối hiển thị cú pháp SQL với syntax highlighting, badge kiểm duyệt an toàn AST, nút Sao chép SQL và nút Chạy lại (Run query).
      - **Trace View**: Cây tiến trình thực thi chi tiết từ backend (Intent classification -> Schema retrieval -> SQL generation -> Control Pipeline -> Execution), hiển thị thời gian từng chặng và chi phí quét bytes.

#### Trang 2: Data Sources & Schema Explorer (`/data-sources`) — **Ưu tiên P0 (Cốt lõi)**
- **Mục đích**: Tạo niềm tin cho người dùng về nguồn dữ liệu thực tế mà Agent đang sử dụng.
- **Bố cục**:
  - *Connections Card*: Hiển thị nguồn dữ liệu DuckDB TPC-DS đang hoạt động (`Connected`, 24 bảng đã lập chỉ mục, dialect DuckDB, thời điểm đồng bộ schema gần nhất).
  - *Schema Explorer*: Ô tìm kiếm bảng nhanh, danh sách 24 bảng chia theo phân hệ (Sales, Returns, Inventory, Dimensions), chi tiết cấu trúc bảng được chọn hiển thị: Tên cột, kiểu dữ liệu (`int`, `varchar`, `decimal`), đánh dấu Primary Key (PK) / Foreign Key (FK) và mô tả nghiệp vụ tiếng Việt.
  - *Hành động "Ask about this table"*: Bấm vào sẽ tự động chuyển hướng về Workspace và điền sẵn câu hỏi mẫu liên quan đến bảng đó.

#### Trang 3: Query History (`/history`) — **Ưu tiên P1**
- **Mục đích**: Xem lại các lần chạy trước, tra cứu câu SQL đã sinh và mở lại phân tích cũ.
- **Bố cục**: Bảng dữ liệu có ô tìm kiếm câu hỏi hoặc SQL, bộ lọc trạng thái (`All`, `Success`, `Failed`), khoảng thời gian. Cột bảng hiển thị: Câu hỏi, nguồn dữ liệu, trạng thái, số dòng kết quả, thời gian thực thi, thời điểm chạy, và nút hành động *"Rerun"* đưa câu hỏi vào Workspace để chạy lại.

#### Trang 4: Saved Queries (`/saved-queries`) — **Ưu tiên P1**
- **Mục đích**: Quản lý những câu hỏi và truy vấn đã lưu để tái sử dụng định kỳ.
- **Bố cục**: Bảng danh sách câu hỏi đã lưu, định dạng kết quả (Chart / Table / Text), data source, thời điểm lưu, chủ sở hữu, nút *"Open"* mở trong Workspace và nút xóa kèm hộp thoại xác nhận. Sử dụng `localStorage` lưu trữ bền vững ở client.

#### Trang 5: Login (`/login`) — **Ưu tiên P1**
- **Mục đích**: Màn hình đăng nhập phong cách SaaS chuẩn mực.
- **Bố cục Split-Screen**:
  - *Nửa Trái (Visual Art & Metrics)*: Gradient màu tối trang nhã, logo sản phẩm, giới thiệu ngắn về năng lực Text2SQL và thẻ xem trước tiến trình thực thi của Agent.
  - *Nửa Phải (Form)*: Nhập email/mật khẩu, tùy chọn chọn nhanh tài khoản demo (`Analyst - Alex` hoặc `Admin - Data Lead`), nút đăng nhập cập nhật thông tin vai trò vào Client Session.

#### Trang 6: Dashboard (`/dashboard`) — **Ưu tiên P2**
- **Mục đích**: Báo cáo tổng quan hoạt động phân tích.
- **Bố cục**: 4 thẻ KPI tổng hợp (Tổng số truy vấn đã chạy, Tỷ lệ thành công %, Thời gian thực thi trung bình, Số insight đã lưu), biểu đồ đường xu hướng hoạt động 7 ngày, danh sách câu hỏi phổ biến và danh sách biểu đồ đã ghim.

#### Trang 7: Settings (`/settings`) — **Ưu tiên P2**
- **Mục đích**: Quản lý tùy chọn cá nhân và chế độ phát triển (Developer Mode).
- **Bố cục**: Tabs điều hướng:
  - *Profile*: Tên hiển thị, email.
  - *Query Preferences*: Bật/tắt chế độ Read-only, chế độ yêu cầu xem trước SQL trước khi chạy, giới hạn số dòng mặc định (100 / 500 / 1000 dòng).
  - *Developer Mode*: Bật/tắt hiển thị tab Trace trong Workspace, bật/tắt hiển thị chi phí token và latency, hộp thoại xác nhận khi thực hiện thao tác xóa.

---

## C. THIẾT KẾ GIAO DIỆN & KIẾN TRÚC COMPONENT (UI & COMPONENT ARCHITECTURE)

### 1. Hệ Thống Design Tokens & Typography

Tuân thủ nguyên tắc từ `frontend-design` (tránh AI clichés: không dùng màu tím neon rực, không dùng orb 3D) và `ui-ux-pro-max` (chế độ Data-Dense, mật độ 8/10, chuyển động 3/10):

| Token | Giá trị Light Mode | Giá trị Dark Mode | Mục đích sử dụng |
|---|---|---|---|
| `--canvas` | `#F5F7FB` | `#10141C` | Nền tổng thể toàn ứng dụng |
| `--surface` | `#FFFFFF` | `#171D28` | Thẻ panel, nền Workspace, Result Canvas |
| `--surface-2` | `#F8FAFC` | `#1D2532` | Nền phụ, header bảng, thẻ stat inline |
| `--surface-3` | `#EEF2F7` | `#273142` | Khung tìm kiếm, viền hover |
| `--line` | `#E4E9F1` | `#2A3444` | Đường kẻ phân chia vùng, viền panel |
| `--line-strong`| `#D5DCE8` | `#3A4659` | Viền input, viền button |
| `--primary` | `#5B5BD6` | `#9292FF` | Màu nhấn thương hiệu, nút CTA chính, active state |
| `--primary-soft`| `#EEEEFF`| `#292A50` | Nền tin nhắn user, badge active |
| `--green` | `#17845D` | `#50D6A0` | Truy vấn thành công, AST verified |
| `--green-soft` | `#E8F8F0`| `#19392E` | Nền badge thành công |
| `--amber` | `#A86812` | `#FFCD73` | Cảnh báo duyệt HITL, thẻ PK/FK |
| `--amber-soft` | `#FFF4DF`| `#3D3020` | Nền badge cảnh báo |
| `--red` | `#BF4653` | `#FF8490` | Thông báo lỗi, từ chối an ninh |
| `--red-soft` | `#FFF0F1` | `#43232A` | Nền badge lỗi |

- **Typography**:
  - Giao diện chung: `Inter` hoặc `Plus Jakarta Sans` (11–13px cho body text, 14–24px cho tiêu đề).
  - Bảng số liệu & Mã lệnh: `JetBrains Mono` hoặc monospace chuẩn, bắt buộc cấu hình `font-variant-numeric: tabular-nums` để số liệu luôn thẳng hàng theo cột.

### 2. Cấu Trúc Thư Mục Frontend Chuẩn (`src/frontend/`)

```
src/frontend/
├── app/
│   ├── (auth)/
│   │   └── login/
│   │       └── page.tsx              # Trang đăng nhập split-layout
│   ├── (app)/
│   │   ├── layout.tsx                # AppShell chung (Sidebar + TopBar)
│   │   ├── workspace/
│   │   │   └── page.tsx              # Workspace phân tích dữ liệu (P0 Core)
│   │   ├── data-sources/
│   │   │   └── page.tsx              # Quản lý nguồn & Schema Explorer (P0)
│   │   ├── history/
│   │   │   └── page.tsx              # Lịch sử truy vấn (P1)
│   │   ├── saved-queries/
│   │   │   └── page.tsx              # Câu hỏi đã lưu (P1)
│   │   ├── dashboard/
│   │   │   └── page.tsx              # Dashboard tổng quan (P2)
│   │   └── settings/
│   │       └── page.tsx              # Cài đặt tùy chọn & Developer mode (P2)
│   ├── globals.css                   # Biến CSS Design Tokens & utilities
│   ├── layout.tsx                    # Root layout (Fonts, Providers, Toast)
│   └── page.tsx                      # Root redirect về /workspace
├── components/
│   ├── layout/
│   │   ├── AppSidebar.tsx            # Sidebar cố định (Brand, DB Switcher, Nav links, Profile)
│   │   ├── AppHeader.tsx             # Topbar (Breadcrumbs, Quick Search, User Menu)
│   │   └── DatabaseSwitcher.tsx      # Bộ hiển thị database đang kết nối
│   ├── workspace/
│   │   ├── WorkspaceLayout.tsx       # Bố cục 2 cột (Conversation & Result Canvas)
│   │   ├── ConversationPanel.tsx     # Khung trao đổi bên trái
│   │   ├── MessageItem.tsx           # Tin nhắn User & Assistant
│   │   ├── QueryComposer.tsx         # Khung nhập câu hỏi (Enter, multi-line)
│   │   ├── ClarificationChips.tsx    # Các thẻ lựa chọn gợi ý khi mơ hồ
│   │   ├── HITLApprovalBanner.tsx    # Khối phê duyệt HITL
│   │   ├── ResultCanvas.tsx          # Khung tab kết quả bên phải
│   │   └── views/
│   │       ├── AnswerView.tsx        # Callout tóm tắt & KPI cards
│   │       ├── DataTableView.tsx     # Bảng dữ liệu (Sort, Pagination, Export CSV)
│   │       ├── ChartView.tsx         # Recharts container (Bar, Line, Area, Pie)
│   │       ├── SQLViewer.tsx         # Cú pháp SQL kèm syntax highlight & copy
│   │       └── TraceView.tsx         # Cây tiến trình thực thi từ backend
│   ├── sources/
│   │   ├── DataSourceCard.tsx        # Thông tin kết nối DuckDB TPC-DS
│   │   ├── SchemaExplorer.tsx        # Khám phá 24 bảng TPC-DS
│   │   └── TableDetailView.tsx       # Chi tiết cột, kiểu dữ liệu, khóa PK/FK
│   ├── shared/
│   │   ├── ui/                       # UI Primitives: Button, Badge, Card, Tabs, Input, Modal
│   │   ├── StatusBadge.tsx           # Badge trạng thái
│   │   ├── EmptyState.tsx            # Trạng thái rỗng
│   │   ├── ErrorAlert.tsx            # Thông báo lỗi
│   │   └── Toast.tsx                 # Thông báo nổi phản hồi thao tác
├── lib/
│   ├── api-client.ts                 # Gọi API FastAPI & inject RBAC headers
│   ├── storage.ts                    # Lưu trữ localStorage (Saved queries, Settings)
│   └── formatters.ts                 # Định dạng số tiền, số lượng, phần trăm, thời gian (ms)
├── types/
│   ├── api.ts                        # TypeScript interfaces khớp Pydantic backend
│   └── schema.ts                     # Schema metadata 24 bảng TPC-DS
└── hooks/
    ├── useWorkspace.ts               # Hook quản lý hội thoại và kết quả
    ├── useSavedQueries.ts            # Hook quản lý câu hỏi đã lưu
    └── useSettings.ts                # Hook quản lý tùy chọn Developer mode
```

### 3. Chiến Lược Quản Lý Trạng Thái (State Management Strategy)
Theo tinh thần **Ponytail (không dùng thư viện phức tạp khi không cần)**:
- **Session & Auth State**: Lưu trữ qua `AuthContext` (lưu `userId`, `role`: Analyst/Admin, `sessionToken`, `adminToken`), tự động đồng bộ vào `localStorage`.
- **Workspace State**: Quản lý bằng React Custom Hook `useWorkspace` (danh sách tin nhắn trong phiên, tab kết quả đang chọn, dữ liệu response gần nhất, trạng thái loading).
- **Saved Queries & Preferences**: Quản lý qua `useSavedQueries` và `useSettings` đọc/ghi trực tiếp vào `localStorage`.

---

## D. TÍCH HỢP FRONTEND - BACKEND (FRONTEND-TO-BACKEND INTEGRATION)

### 1. Luồng Giao Tiếp Chi Tiết Cho Từng Tính Năng

#### A. Gửi Câu Hỏi: `POST /api/v1/query/ask`
- **Request Body**:
  ```json
  {
    "question": "Top 10 sản phẩm có doanh thu cao nhất năm 2003",
    "session_id": "sess_workspace_01",
    "user_id": "analyst_alex",
    "role": "Analyst"
  }
  ```
- **Headers tự động kèm theo**:
  - `X-User-Id`: ID người dùng hiện tại
  - `X-User-Role`: `Analyst` hoặc `Admin`
  - `X-Session-Id`: ID phiên hiện tại
  - `X-Session-Token`: Token bí mật chống giả mạo phiên (nhận từ response trước)
- **Xử lý Response**:
  - Cập nhật Assistant message với `final_answer`.
  - Nếu có `response_package.artifacts`: Tự động chọn tab phù hợp (ưu tiên Tab `Chart` nếu có biểu đồ, Tab `Table` nếu có bảng số liệu, hoặc Tab `Answer` nếu là chỉ số KPI đơn lẻ).
  - Nạp câu lệnh `sql` vào Tab `SQL`.
  - Nạp danh sách `tasks` và `artifacts` vào Tab `Trace`.

#### B. Phê Duyệt HITL: `POST /api/v1/query/approve`
- **Request Body**:
  ```json
  {
    "session_id": "sess_workspace_01",
    "approved": true,
    "rejection_reason": null
  }
  ```
- **Headers**: Yêu cầu `X-User-Role: Admin` (kèm `X-Admin-Token` nếu server yêu cầu).
- **Xử lý**: Nhận kết quả `ApprovalResponse`, giải phóng trạng thái chờ và hiển thị dữ liệu bảng trong Workspace.

#### C. Khám Phá Schema 24 Bảng TPC-DS
- **Giải pháp**:
  - *Backend (Khuyến nghị)*: Bổ sung 1 endpoint nhẹ `GET /api/v1/schema` trong FastAPI xuất dữ liệu từ `src/utils/schema_context.py`.
  - *Frontend Fallback*: Nhúng sẵn file metadata `src/frontend/data/tpcdsSchema.ts` chứa đầy đủ 24 bảng để UI hoạt động độc lập ngay cả khi chưa bổ sung endpoint backend.

#### D. Lịch Sử & Audit Logs: `GET /api/v1/audit/logs`
- **Request Query**: `?limit=50&offset=0`
- **Headers**: `X-User-Role: Admin`.
- **Hiển thị**: Trang `/history` nạp danh sách các sự kiện kiểm toán để người dùng tìm kiếm, lọc và bấm *"Rerun"*.

### 2. Danh Sách Công Việc Backend Cần Hỗ Trợ (Backend Work Items)
- [ ] **BE-1 (Khuyến nghị)**: Bổ sung route `GET /api/v1/schema` trả về danh sách 24 bảng TPC-DS kèm cột, kiểu dữ liệu, khóa PK/FK và mô tả nghiệp vụ tiếng Việt.
- [ ] **BE-2 (Tùy chọn)**: Hỗ trợ SSE (Server-Sent Events) tại `GET /api/v1/query/stream` nếu muốn hiển thị trạng thái từng bước theo thời gian thực (hiện tại `POST /ask` phản hồi đồng bộ hoàn tất trong 1–3s là hoàn toàn đủ tốt).

---

## E. KẾ HOẠCH TRIỂN KHAI THEO GIAI ĐOẠN (PHASED IMPLEMENTATION PLAN)

```
[Phase 1: Nền tảng & AppShell]
  │
  ▼
[Phase 2: Workspace Cốt Lõi (P0)]
  │
  ▼
[Phase 3: Data Sources, Schema Explorer & Login (P0/P1)]
  │
  ▼
[Phase 4: Query History & Saved Queries (P1)]
  │
  ▼
[Phase 5: Dashboard, Settings & Hoàn thiện Toàn diện (P2)]
```

---

### GIAI ĐOẠN 1: NỀN TẢNG KỸ THUẬT & APPSHELL DÙNG CHUNG
- **Mục tiêu**: Khởi tạo dự án Next.js 14 sạch sẽ, cấu hình hệ thống tokens Tailwind CSS theo nguyên mẫu HTML, dựng khung AppShell (Sidebar, TopBar) và các trang rỗng để điều hướng mượt mà.
- **Phạm vi & Công việc**:
  - Khởi tạo Next.js 14 App Router với TypeScript và Tailwind CSS tại `src/frontend/`.
  - Cấu hình file `globals.css` định nghĩa toàn bộ biến CSS Tokens (Canvas, Surface, Line, Primary, Success, Warning, Danger).
  - Dựng component `AppSidebar`: Logo QueryPilot, Database Switcher widget (`DuckDB TPC-DS Connected`), danh sách 6 mục điều hướng, Help card, Profile mini. Hỗ trợ responsive co gọn thành icon bar khi màn hình dưới 900px.
  - Dựng component `AppHeader`: Breadcrumb động theo route (`QueryPilot › Workspace`), khung tìm kiếm nhanh (`⌘ K`), User badge.
  - Dựng layout shell `app/(app)/layout.tsx` và các placeholder pages cho `/workspace`, `/data-sources`, `/history`, `/saved-queries`, `/dashboard`, `/settings`.
  - Cấu hình redirect `/` về `/workspace`.
- **Tiêu chí hoàn thành (Exit Criterion)**: Chạy `npm run dev` hiển thị giao diện mượt mà, chuyển đổi giữa 6 trang cập nhật đúng URL và breadcrumb, responsive hoạt động chính xác.

---

### GIAI ĐOẠN 2: WORKSPACE CỐT LÕI (CORE TEXT2SQL ENGINE)
- **Mục tiêu**: Hoàn thiện trọn vẹn trải nghiệm hỏi đáp dữ liệu: Nhập câu hỏi -> Gửi API backend -> Render bảng, biểu đồ, SQL và Trace thật.
- **Phạm vi & Công việc**:
  - `lib/api-client.ts`: Module gọi API FastAPI `/api/v1/query/ask` và `/api/v1/query/approve`, xử lý timeout và bắt lỗi mạng.
  - `QueryComposer.tsx`: Khung nhập liệu với phím tắt `Enter` gửi, icon chỉ báo nguồn dữ liệu đang kết nối, gợi ý câu hỏi mẫu.
  - `ConversationPanel.tsx` & `MessageItem.tsx`: Hiển thị tin nhắn người dùng và phản hồi của Agent kèm inline stats, timeline tóm tắt các bước thực thi.
  - `ClarificationChips.tsx`: Khối hiển thị các lựa chọn gợi ý khi `status === "CLARIFICATION_REQUIRED"`.
  - `HITLApprovalBanner.tsx`: Khối cảnh báo phê duyệt khi `status === "PENDING_APPROVAL"`, hỗ trợ gửi phê duyệt và nhận kết quả tức thì.
  - `ResultCanvas.tsx` & 5 Tabs hiển thị kết quả:
    - `AnswerView`: Hiển thị tóm tắt, KPI cards, insight rút ra.
    - `DataTableView`: Bảng dữ liệu hỗ trợ cuộn ngang/dọc, căn lề số dạng `tabular-nums`, nút Copy bảng và xuất file CSV.
    - `ChartView`: Render biểu đồ Recharts (Bar/Line) thích ứng với dữ liệu thật từ backend.
    - `SQLViewer`: Codeblock màu tối hiển thị cú pháp SQL rõ ràng kèm nút Copy SQL và badge kiểm duyệt an toàn.
    - `TraceView`: Cây tiến trình thực thi chi tiết từ danh sách `tasks` và `artifacts` của backend.
- **Tiêu chí hoàn thành (Exit Criterion)**: Gửi được câu hỏi thực tế (ví dụ: *"Top 10 sản phẩm có doanh thu cao nhất năm 2003"*), nhận dữ liệu thật từ DuckDB TPC-DS, cả 5 tab hiển thị chính xác, luồng duyệt HITL hoạt động trơn tru.

---

### GIAI ĐOẠN 3: DATA SOURCES, SCHEMA EXPLORER & MÀN HÌNH ĐĂNG NHẬP
- **Mục tiêu**: Người dùng hiểu rõ ngữ cảnh kho dữ liệu 24 bảng TPC-DS và có thể đăng nhập phân quyền vai trò.
- **Phạm vi & Công việc**:
  - Bổ sung endpoint backend `GET /api/v1/schema` (kèm fallback tĩnh tại `src/frontend/data/tpcdsSchema.ts`).
  - `SchemaExplorer.tsx`: Tìm kiếm bảng, lọc theo phân hệ (Sales, Returns, Inventory, Dimensions), xem danh sách cột, kiểu dữ liệu, đánh dấu PK/FK và giải thích ý nghĩa cột.
  - Nút *"Hỏi về bảng này"*: Chuyển về Workspace kèm câu hỏi gợi ý về bảng tương ứng.
  - `app/(auth)/login/page.tsx`: Màn hình đăng nhập split-screen, cho phép chọn nhanh tài khoản `Analyst` hoặc `Admin` để lưu vào session context.
- **Tiêu chí hoàn thành (Exit Criterion)**: Tìm kiếm và tra cứu được đầy đủ thông tin của cả 24 bảng TPC-DS; đăng nhập/chuyển đổi tài khoản Admin cập nhật đúng header `X-User-Role`.

---

### GIAI ĐOẠN 4: LỊCH SỬ TRUY VẤN (HISTORY) & CÂU HỎI ĐÃ LƯU (SAVED QUERIES)
- **Mục tiêu**: Cho phép tra cứu các lần chạy trước và lưu lại những phân tích hữu ích.
- **Phạm vi & Công việc**:
  - `app/(app)/saved-queries/page.tsx`: Bảng quản lý câu hỏi đã lưu, lưu vào `localStorage`, có ô tìm kiếm, bộ lọc data source, nút xóa có xác nhận và nút *"Open"* mở lại trong Workspace.
  - Tích hợp nút *"Save query"* trong Workspace để lưu kết quả đang xem vào danh sách Saved Queries.
  - `app/(app)/history/page.tsx`: Bảng hiển thị lịch sử các lần chạy trước (kết nối với audit logs hoặc local session runs), lọc theo trạng thái Success/Failed, nút *"Rerun"* đưa câu hỏi vào Workspace để chạy lại.
- **Tiêu chí hoàn thành (Exit Criterion)**: Lưu thành công câu hỏi từ Workspace sang Saved Queries; bấm Rerun trong History hoặc Open trong Saved Queries sẽ kích hoạt câu hỏi trong Workspace.

---

### GIAI ĐOẠN 5: TỔNG QUAN DASHBOARD, CÀI ĐẶT (SETTINGS) & HOÀN THIỆN TOÀN DIỆN
- **Mục tiêu**: Hoàn thiện Dashboard tổng hợp và Settings; rà soát khả năng tiếp cận (Accessibility), responsive và hiệu năng.
- **Phạm vi & Công việc**:
  - `app/(app)/dashboard/page.tsx`: 4 thẻ KPI tính toán từ dữ liệu chạy thực tế, biểu đồ hoạt động theo thời gian, danh sách câu hỏi phổ biến và danh sách biểu đồ đã ghim.
  - `app/(app)/settings/page.tsx`: Cấu hình profile, tùy chọn query (Read-only, default limit), tùy chọn Developer Mode (bật/tắt tab Trace, telemetry).
  - Tối ưu hóa Responsive: Kiểm tra bố cục trên Desktop (1440px), Laptop (1024px), Tablet (768px) và Mobile (375px).
  - Khả năng tiếp cận: Đảm bảo tỷ lệ tương phản đạt chuẩn WCAG AA, focus outline bàn phím rõ ràng, các icon có thuộc tính `aria-hidden` hoặc nhãn `aria-label` đầy đủ.
- **Tiêu chí hoàn thành (Exit Criterion)**: Toàn bộ 7 trang hoạt động nhất quán, không còn lỗi console, kiểm tra linting `npm run lint` đạt 100% pass, build production `npm run build` thành công.

---

## F. RỦI RO KỸ THUẬT & QUYẾT ĐỊNH THIẾT KẾ (RISKS & TECHNICAL DECISIONS)

| Rủi ro kỹ thuật | Giải pháp đề xuất |
|---|---|
| **SSR Hydration Mismatch với Recharts** | Toàn bộ các component biểu đồ (`ChartView`) khai báo `'use client'` và bọc trong component có kiểm tra `mounted` để tránh lỗi bất đồng bộ SSR của Next.js. |
| **Bảng dữ liệu lớn làm đơ trình duyệt** | Áp dụng phân trang tại client (10–25 dòng/trang) và giới hạn hiển thị tối đa 100 dòng kèm nút xuất CSV nếu dữ liệu lớn, tránh render DOM quá tải. |
| **Bảo vệ quyền Admin trên Client** | Header `X-Admin-Token` được lưu trữ an toàn trong Client Session và chỉ gửi kèm khi tài khoản đăng nhập là Admin. Nếu thiếu token, backend tự động từ chối với mã 403 Forbidden. |
| **Thiếu Persistence API cho Saved Queries** | Sử dụng `localStorage` thông qua tầng repository trừu tượng (`storage.ts`). Khi backend bổ sung REST API `/api/v1/saved-queries`, chỉ cần thay đổi 1 file service mà không ảnh hưởng tới UI. |
| **Trôi dạt sang "Chatbot đồ chơi"** | Nghiêm cấm đưa vào các hiệu ứng thừa thãi (như quả cầu 3D, chat pill di động, CoT ảo). Mọi chi tiết thiết kế bám chặt vào nguyên mẫu HTML: Bố cục 2 panel rõ ràng, màu sắc Slate/Indigo nhẹ nhàng, bảng biểu dữ liệu đặt lên hàng đầu. |

---

## G. TIÊU CHÍ NGHIỆM THU TỔNG THỂ (ACCEPTANCE CRITERIA)

1. **Khả Năng Vận Hành Cốt Lõi (Workspace)**:
   - Gửi được câu hỏi ngôn ngữ tự nhiên tiếng Việt, nhận kết quả thực tế từ DuckDB TPC-DS trong vòng dưới 5 giây.
   - Khi câu hỏi mơ hồ, hiển thị rõ ràng các thẻ gợi ý A/B/C và cho phép bấm chọn để gửi lại.
   - Khi câu lệnh cần phê duyệt HITL, hiển thị banner cảnh báo và cho phép người dùng có quyền Admin phê duyệt thành công.
   - Cả 5 góc nhìn (Answer, Table, Chart, SQL, Trace) hiển thị đúng định dạng khi có dữ liệu tương ứng, tự động thích ứng với cấu trúc `response_package` của backend.
2. **Khám Phá Dữ Liệu (Data Sources)**:
   - Hiển thị chính xác trạng thái kết nối của DuckDB TPC-DS.
   - Tìm kiếm và xem được danh sách cột, kiểu dữ liệu, khóa PK/FK của cả 24 bảng TPC-DS.
   - Nút *"Hỏi về bảng này"* hoạt động trơn tru, điền sẵn câu hỏi vào Workspace.
3. **Lịch Sử & Tái Sử Dụng (History & Saved Queries)**:
   - Lưu trữ và hiển thị được danh sách câu hỏi đã lưu, hỗ trợ tìm kiếm và xóa có xác nhận.
   - Cho phép mở lại câu hỏi đã lưu hoặc chạy lại câu hỏi từ History chỉ với 1 cú click.
4. **Trải Nghiệm & Thẩm Mỹ (UI/UX Quality)**:
   - Giao diện khớp với ngôn ngữ thiết kế của nguyên mẫu HTML: màu sắc trang nhã, typography sắc nét, font số `tabular-nums` thẳng hàng.
   - Không xuất hiện bất kỳ "AI Cliché" nào (không quả cầu neon 3D, không timeline giả định, không bong bóng chat ép hẹp).
   - Responsive hoàn chỉnh từ desktop (1440px) xuống laptop (1024px) và mobile (375px).
   - Đạt chuẩn kiểm tra code: `npm run lint` không có lỗi, `npm run build` thành công không cảnh báo type.

---

## H. PHẠM VI & CHECKLIST CHI TIẾT GIAI ĐOẠN 1 (PHASE 1 SCOPE & TASK BREAKDOWN)

- [ ] **Task 1.1: Khởi tạo Project & Cài đặt Thư viện**
  - Khởi tạo dự án Next.js 14 App Router với TypeScript và Tailwind CSS tại `src/frontend/`.
  - Cài đặt các dependencies cần thiết tối thiểu: `lucide-react`, `clsx`, `tailwind-merge`.
  - Cấu hình file `src/frontend/tsconfig.json` với path alias `@/*`.
- [ ] **Task 1.2: Thiết lập Design Tokens & Utility Styles**
  - Cấu hình `src/frontend/tailwind.config.ts` và `src/frontend/app/globals.css` định nghĩa toàn bộ bảng màu Semantic từ prototype:
    - Nền canvas `#f5f7fb` (Light) / `#10141c` (Dark), surface panel `#ffffff`, line `#e4e9f1`.
    - Màu chủ đạo Primary Indigo `#5b5bd6`, Success Green `#17845d`, Warning Amber `#a86812`, Error Red `#bf4653`.
  - Định nghĩa utility rules cho typography: font Sans cho văn bản và font Mono `tabular-nums` cho số liệu.
- [ ] **Task 1.3: Xây dựng Component AppSidebar**
  - Tạo `src/frontend/components/layout/AppSidebar.tsx`:
    - Brand Logo & Name: `QueryPilot` (AI data workspace).
    - Database Switcher Widget: Hiển thị `AdventureWorks / DuckDB TPC-DS (24 tables)` kèm chấm xanh Connected.
    - Danh sách 6 mục điều hướng: Workspace, Dashboard, Saved queries (kèm badge số đếm), Query history, Data sources, Settings.
    - Trạng thái Active highlight rõ ràng khi ở trang tương ứng.
    - Thẻ trợ giúp nhanh (Help card) và Profile người dùng ở đáy sidebar.
    - Hỗ trợ responsive: Tự động thu gọn thành thanh icon gọn gàng trên màn hình nhỏ (<900px).
- [ ] **Task 1.4: Xây dựng Component AppHeader (TopBar)**
  - Tạo `src/frontend/components/layout/AppHeader.tsx`:
    - Breadcrumb động phản ánh chính xác trang hiện tại (ví dụ: `QueryPilot › Workspace`).
    - Khung tìm kiếm nhanh (`Search queries, tables... ⌘ K`).
    - Nút Help, Notifications và User Avatar kèm badge vai trò (`Analyst` / `Admin`).
- [ ] **Task 1.5: Xây dựng Layout Chung & Cấu Trúc Tuyến Đường (Route Shells)**
  - Tạo `src/frontend/app/(app)/layout.tsx` kết hợp `AppSidebar` và `AppHeader` thành AppShell hoàn chỉnh.
  - Tạo các file trang đại diện (placeholder pages có sẵn PageHeading, Eyebrow, Title, Action Button) cho:
    - `src/frontend/app/(app)/workspace/page.tsx`
    - `src/frontend/app/(app)/data-sources/page.tsx`
    - `src/frontend/app/(app)/history/page.tsx`
    - `src/frontend/app/(app)/saved-queries/page.tsx`
    - `src/frontend/app/(app)/dashboard/page.tsx`
    - `src/frontend/app/(app)/settings/page.tsx`
  - Cấu hình `src/frontend/app/page.tsx` tự động redirect về `/workspace`.
- [ ] **Task 1.6: Kiểm thử & Nghiệm thu Giai đoạn 1**
  - Chạy `npm run dev` kiểm tra giao diện trên trình duyệt.
  - Xác minh điều hướng giữa 6 trang mượt mà, layout không vỡ.
  - Kiểm tra `npm run lint` và `npm run build` vượt qua mà không có lỗi cú pháp hoặc cảnh báo.
