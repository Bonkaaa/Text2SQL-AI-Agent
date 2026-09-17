# Kế Hoạch Chia Nhỏ Các Thành Phần Code Cho Frontend Text2SQL (v1.0)

> **Tài liệu tham chiếu**:
> - Thiết kế kiến trúc & UI/UX Frontend: [`docs/frontend/FRONTEND_DESIGN.md`](file:///d:/Text2SQL-AI-Agent/docs/frontend/FRONTEND_DESIGN.md)
> - Đề tài & Yêu cầu chấm điểm: [`docs/DETAI.md`](file:///d:/Text2SQL-AI-Agent/docs/DETAI.md)
> - Đặc tả yêu cầu sản phẩm: [`docs/PRD.md`](file:///d:/Text2SQL-AI-Agent/docs/PRD.md)
> - Đặc tả Gateway API: [`docs/agent/component-5.1-fastapi-specification.md`](file:///d:/Text2SQL-AI-Agent/docs/agent/component-5.1-fastapi-specification.md)
> - Mẫu phân rã Agent tham khảo: [`docs/agent/agent-components-breakdown.md`](file:///d:/Text2SQL-AI-Agent/docs/agent/agent-components-breakdown.md)
> - Quy ước kỹ thuật: [`AGENTS.md`](file:///d:/Text2SQL-AI-Agent/AGENTS.md)
>
> **Mục tiêu**: Phân rã toàn bộ hệ thống giao diện Frontend thành các **thành phần nhỏ (Atomic & Modular Components)**, sắp xếp theo trình tự phát triển từ dưới lên (**Bottom-Up**). Mỗi component có định nghĩa rõ ràng về **Input Props, Output Events, Logic giao diện, Phụ thuộc** và **Tiêu chí kiểm thử độc lập (DoD)** trước khi chuyển sang thành phần kế tiếp.

---

## 1. CHIẾN LƯỢC TRIỂN KHAI TUẦN TỰ (PHASED BOTTOM-UP STRATEGY)

Để đảm bảo chất lượng code cao nhất, tránh viết một khối khổng lồ gây lỗi khó rà soát, và giúp người dùng dễ dàng review từng bước, Frontend được chia thành **6 Giai đoạn (Phases)** với **19 Components độc lập**:

```
+-----------------------------------------------------------------------------------------+
| Phase 0: Nền Tảng, Môi Trường, Types & Tiện Ích Mạng (Foundation & Infrastructure)      |
| (0.1 Setup Next.js -> 0.2 Design Tokens & Tailwind -> 0.3 Types -> 0.4 API Client -> 0.5 CSV)
+-------------------------------------------+---------------------------------------------+
                                            |
+-------------------------------------------v---------------------------------------------+
| Phase 1: Khung Bố Cục & Điều Hướng Toàn Cục (Layout & Shell Components)                 |
| (1.1 Root Layout -> 1.2 Header & Status -> 1.3 Role Switcher -> 1.4 Sidebar -> 1.5 Schema)
+-------------------------------------------+---------------------------------------------+
                                            |
+-------------------------------------------v---------------------------------------------+
| Phase 2: Khung Nhập Liệu & Dòng Hội Thoại (Chat Input & Feed Components)                |
| (2.1 Chat Input -> 2.2 Prompt Presets -> 2.3 Message List -> 2.4 Reasoning Timeline)   |
+-------------------------------------------+---------------------------------------------+
                                            |
+-------------------------------------------v---------------------------------------------+
| Phase 3: Thẻ Trạng Thái Đặc Thù Của AI Agent (Agent Interactive Cards)                  |
| (3.1 Clarification Card A/B/C -> 3.2 HITL Approval Modal -> 3.3 Error & Retry Feedback)|
+-------------------------------------------+---------------------------------------------+
                                            |
+-------------------------------------------v---------------------------------------------+
| Phase 4: Trực Quan Hóa & Trình Diễn Dữ Liệu (Analytics Canvas & Data Presenters)        |
| (4.1 Business Insight -> 4.2 Recharts Dynamic Chart -> 4.3 Data Table -> 4.4 SQL Viewer)
+-------------------------------------------+---------------------------------------------+
                                            |
+-------------------------------------------v---------------------------------------------+
| Phase 5: Tích Hợp Toàn Trình & Màn Hình Admin Audit (Integration & Admin Dashboard)     |
| (5.1 Message Item Composer -> 5.2 Main Page -> 5.3 Admin Audit Page -> 5.4 E2E Polish)  |
+-----------------------------------------------------------------------------------------+
```

### Nguyên tắc Thực hiện Từng bước (Step-by-Step Rule):
1. **Làm một việc tại một thời điểm (One thing at a time)**: Chỉ code và kiểm thử 1 component trước khi chuyển sang component tiếp theo.
2. **Review trước khi đi tiếp**: Sau mỗi component hoặc nhóm phụ thuộc nhỏ, dừng lại để người dùng review và kiểm tra.
3. **Type-Safe 100%**: Mọi data models trên giao diện phải khớp chuẩn với Pydantic Schemas của backend FastAPI.
4. **Không Hardcode Mockup**: Các component phải được thiết kế để nhận dữ liệu thật từ API, có trạng thái Loading, Empty và Error riêng biệt.

---

## 2. CHI TIẾT TỪNG COMPONENT TRIỂN KHAI

---

### PHASE 0: NỀN TẢNG, MÔI TRƯỜNG & THƯ VIỆN TIỆN ÍCH (FOUNDATION)

#### Component 0.1: Khởi Tạo Dự Án Next.js 14 App Router
- **Thư mục/File**: `src/frontend/package.json`, `src/frontend/tsconfig.json`, `src/frontend/next.config.mjs`
- **Nhiệm vụ**: Khởi tạo khung ứng dụng Next.js 14 sử dụng App Router, TypeScript và cấu hình alias `@/*` trỏ vào `src/frontend/*`.
- **Dependencies**: `next@14.x`, `react@18.x`, `react-dom@18.x`, `typescript`, `@types/react`, `@types/node`.
- **Tiêu chí kiểm thử (DoD)**:
  - Lệnh `npm --prefix src/frontend run build` hoặc khởi chạy `npm --prefix src/frontend run dev` không bị lỗi build.

---

#### Component 0.2: Cấu Hình Design System & Tailwind CSS (Dark Mode Tokens)
- **Thư mục/File**: `src/frontend/tailwind.config.ts`, `src/frontend/postcss.config.mjs`, `src/frontend/app/globals.css`
- **Nhiệm vụ**:
  - Thiết lập bảng màu chuẩn Enterprise Dark Mode (nền Slate-950 / Zinc-900, viền Slate-800, điểm nhấn Indigo-500 và Emerald-500).
  - Tích hợp font chữ hiện đại **Inter**, bo góc thẻ `rounded-xl`, thanh cuộn tùy chỉnh `custom-scrollbar`.
  - Khai báo các tiện ích hiệu ứng kính mờ `glassmorphism`, pulsing loading indicator.
- **Dependencies**: `tailwindcss@^3.4`, `postcss`, `autoprefixer`, `lucide-react` (bộ icon).
- **Tiêu chí kiểm thử (DoD)**:
  - File `globals.css` nạp thành công các class tiện ích; Tailwind build không có cảnh báo cú pháp.

---

#### Component 0.3: Khai Báo TypeScript Interfaces & Hợp Đồng Dữ Liệu
- **File**: `src/frontend/types/api.d.ts`
- **Nhiệm vụ**: Định nghĩa toàn bộ kiểu dữ liệu TypeScript khớp chuẩn 100% với Pydantic Schemas trong [`src/models/api_schemas.py`](file:///d:/Text2SQL-AI-Agent/src/models/api_schemas.py).
- **Nội dung code**:
  ```typescript
  export type UserRole = "Analyst" | "Admin";

  export type QueryStatus = "COMPLETED" | "CLARIFICATION_REQUIRED" | "PENDING_APPROVAL" | "ERROR" | "EXECUTION_FAILED";

  export interface AskQueryRequest {
    question: str;
    session_id?: string;
    user_id?: string;
    role: UserRole;
  }

  export interface RechartsConfig {
    chart_type: "bar" | "line" | "area" | "pie" | "table";
    title?: string;
    x_key?: string;
    y_keys?: string[];
    series_labels?: Record<string, string>;
    description?: string;
  }

  export interface QueryResponse {
    session_id: string;
    status: QueryStatus;
    question: string;
    is_ambiguous: boolean;
    clarification_question?: string | null;
    suggested_options: string[];
    final_answer?: string | null;
    sql?: string | null;
    data?: Record<string, any>[] | null;
    columns?: string[] | null;
    recharts_config?: RechartsConfig | null;
    requires_hitl: boolean;
    estimated_cost_bytes?: number | null;
    execution_time_ms: number;
    error?: string | null;
  }

  export interface ApprovalRequest {
    session_id: string;
    approved: boolean;
    rejection_reason?: string | null;
  }

  export interface ApprovalResponse {
    session_id: string;
    approved: boolean;
    status: string;
    message: string;
    data?: Record<string, any>[] | null;
    columns?: string[] | null;
  }

  export interface AuditLogItem {
    timestamp: string;
    user_id: string;
    role: string;
    session_id: string;
    question?: string;
    sql?: string;
    status: string;
    execution_time_ms: number;
    bytes_scanned?: number;
    error_type?: string;
  }

  export interface AuditLogsResponse {
    total: number;
    limit: number;
    offset: number;
    logs: AuditLogItem[];
  }
  ```
- **Dependencies**: Không (Pure TypeScript).
- **Tiêu chí kiểm thử (DoD)**: Chạy `tsc --noEmit` không có lỗi cú pháp type.

---

#### Component 0.4: API Client & Network Service Layer
- **File**: `src/frontend/services/api.ts`
- **Nhiệm vụ**: Đóng gói các hàm gọi HTTP sang FastAPI Gateway (`http://localhost:8000` hoặc biến môi trường `NEXT_PUBLIC_API_URL`).
- **Các hàm chính**:
  - `askQuery(payload: AskQueryRequest): Promise<QueryResponse>`
  - `approveQuery(payload: ApprovalRequest): Promise<ApprovalResponse>`
  - `getQueryHistory(sessionId: string): Promise<QueryHistoryResponse>`
  - `getAuditLogs(limit?: number, offset?: number, role?: UserRole): Promise<AuditLogsResponse>`
  - `checkBackendHealth(): Promise<{ status: string; database: string; version: string }>`
- **Xử lý ngoại lệ**: Bắt lỗi kết nối mạng (Network Error / Offline), chuẩn hóa thông báo lỗi thân thiện bằng tiếng Việt.
- **Tiêu chí kiểm thử (DoD)**: Viết script test nhỏ hoặc gọi mock test kiểm tra parse response đúng type.

---

#### Component 0.5: Tiện Ích Xuất Dữ Liệu Bảng Ra CSV (CSV Exporter)
- **File**: `src/frontend/services/exportCsv.ts`
- **Nhiệm vụ**: Nhận vào danh sách cột và các dòng dữ liệu, chuyển thành chuỗi CSV chuẩn UTF-8 (có BOM `\uFEFF` để Excel hiển thị đúng tiếng Việt có dấu) và kích hoạt tải về trên trình duyệt.
- **Hàm chính**: `exportToCsv(filename: string, columns: string[], rows: Record<string, any>[]): void`
- **Tiêu chí kiểm thử (DoD)**: Test export với dữ liệu mẫu có ký tự tiếng Việt (ví dụ: *"Tổng doanh thu"*), mở file không bị vỡ font.

---

### PHASE 1: KHUNG BỐ CỤC & ĐIỀU HƯỚNG TOÀN CỤC (LAYOUT & SHELL)

#### Component 1.1: Root Layout & Global Shell
- **File**: `src/frontend/app/layout.tsx`
- **Nhiệm vụ**: Thiết lập khung layout gốc của ứng dụng web, đặt title, favicon, import `globals.css`, áp dụng theme tối ưu trên thẻ `<body>`.
- **Props/State**: `{ children: React.ReactNode }`
- **Tiêu chí kiểm thử (DoD)**: Trang hiển thị nền dark mode chuẩn, không bị nhấp nháy giao diện khi tải lại trang.

---

#### Component 1.2: Header & Trạng Thái Warehouse (Top Navigation)
- **File**: `src/frontend/components/layout/Header.tsx`
- **Nhiệm vụ**:
  - Hiển thị logo nhận diện thương hiệu `Text2SQL Enterprise AI`.
  - Hiển thị widget sức khỏe kết nối DuckDB Warehouse (`Connected`, `Checking...`, hoặc `Disconnected`) thông qua việc gọi `checkBackendHealth()`.
  - Tích hợp nút kích hoạt mở/đóng ngăn **Schema Drawer** bên phải.
- **Input Props**: `onToggleSchemaDrawer: () => void; isSchemaOpen: boolean;`
- **Tiêu chí kiểm thử (DoD)**: Header cố định trên đầu trang (sticky), hiển thị đúng trạng thái kết nối với backend.

---

#### Component 1.3: Bộ Chuyển Đổi Vai Trò Người Dùng (Role Switcher)
- **File**: `src/frontend/components/layout/RoleSwitcher.tsx`
- **Nhiệm vụ**:
  - Dropdown chọn vai trò giữa **`Analyst` (Nguyễn Văn An - Quyền đọc bị che PII)** và **`Admin` (Trần Thị Bình - Toàn quyền & Xem Audit)**.
  - Lưu trạng thái vai trò vào Context / State toàn cục để mọi request gửi đi đều kèm role tương ứng.
  - Hiển thị huy hiệu vai trò trực quan (màu xanh Indigo cho Analyst, màu tím/vàng Amber cho Admin).
- **Input Props**: `currentRole: UserRole; onRoleChange: (newRole: UserRole) => void;`
- **Tiêu chí kiểm thử (DoD)**: Chuyển đổi role cập nhật ngay lập tức giao diện và mở khóa các tính năng của Admin.

---

#### Component 1.4: Thanh Điều Hướng Bên Trái (Left Sidebar & Session Manager)
- **File**: `src/frontend/components/layout/Sidebar.tsx`
- **Nhiệm vụ**:
  - Nút **[+ Cuộc hội thoại mới]** để reset session_id.
  - Danh sách lịch sử các phiên làm việc đã lưu trong `localStorage`.
  - Danh sách các câu hỏi mẫu gợi ý 1-click (nhấn vào là tự điền/gửi câu hỏi).
  - Nút chuyển sang trang Quản trị **[🛡️ Nhật ký Audit]** (chỉ hiển thị khi `role === "Admin"`).
- **Input Props**: `currentSessionId: string; onSelectSession: (id: string) => void; onNewSession: () => void; onSelectPreset: (q: string) => void; role: UserRole;`
- **Tiêu chí kiểm thử (DoD)**: Tạo mới session sinh mã UUID mới; bấm vào preset gọi đúng hàm callback.

---

#### Component 1.5: Ngăn Tra Cứu Lược Đồ Dữ Liệu TPC-H (Schema Drawer)
- **File**: `src/frontend/components/layout/SchemaDrawer.tsx`
- **Nhiệm vụ**:
  - Ngăn trượt mở ra từ mép phải màn hình.
  - Liệt kê cấu trúc 8 bảng TPC-H (`region`, `nation`, `supplier`, `customer`, `part`, `partsupp`, `orders`, `lineitem`).
  - Ghi chú rõ các trường cấm (PII) đối với Analyst: `c_phone`, `c_acctbal`, `s_phone`, `s_acctbal`.
  - Liệt kê các công thức tính toán chỉ số chuẩn dbt metrics (Doanh thu thuần, Tỷ lệ trễ hạn).
- **Input Props**: `isOpen: boolean; onClose: () => void;`
- **Tiêu chí kiểm thử (DoD)**: Đóng/mở mượt mà với animation trượt ngang; hiển thị rõ ràng thông tin tra cứu.

---

### PHASE 2: KHUNG NHẬP LIỆU & DÒNG HỘI THOẠI (CHAT & INPUT ENGINE)

#### Component 2.1: Khung Nhập Câu Hỏi & Phím Tắt (Chat Input Bar)
- **File**: `src/frontend/components/chat/ChatInput.tsx`
- **Nhiệm vụ**:
  - Ô nhập textarea tự động dãn chiều cao theo nội dung.
  - Hỗ trợ phím tắt: `Enter` để gửi câu hỏi, `Shift + Enter` để xuống dòng mới.
  - Nút [Gửi] với icon mũi tên hoặc spinner loading khi hệ thống đang xử lý câu hỏi trước đó.
  - Tự động focus vào ô nhập khi tải trang.
- **Input Props**: `onSendMessage: (text: string) => void; isLoading: boolean; placeholder?: string;`
- **Tiêu chí kiểm thử (DoD)**: Bấm Enter khi có nội dung sẽ gọi `onSendMessage`, tự xóa trắng ô nhập sau khi gửi, không cho gửi khi input rỗng hoặc đang loading.

---

#### Component 2.2: Thư Viện Câu Hỏi Mẫu Nổi Bật (Prompt Presets Bar)
- **File**: `src/frontend/components/chat/PromptPresets.tsx`
- **Nhiệm vụ**:
  - Hiển thị danh sách các thẻ câu hỏi gợi ý nhanh khi màn hình bắt đầu chưa có tin nhắn nào.
  - Phân loại theo chủ đề: Doanh thu theo khu vực, Top khách hàng, Giao hàng trễ, Phân tích tồn kho.
- **Input Props**: `onSelectPrompt: (promptText: string) => void;`
- **Tiêu chí kiểm thử (DoD)**: Bấm vào thẻ gợi ý tự động kích hoạt tiến trình gửi câu hỏi.

---

#### Component 2.3: Danh Sách Hội Thoại & Tự Động Cuộn (Message Feed)
- **File**: `src/frontend/components/chat/MessageList.tsx`
- **Nhiệm vụ**:
  - Cuộn dọc danh sách các lượt trao đổi (User Message và Agent Response).
  - Tự động cuộn xuống cuối (Auto-scroll to bottom) khi có tin nhắn mới hoặc khi kết quả phân tích xuất hiện.
  - Trình bày tin nhắn của Người dùng ở dạng bubble bên phải, phản hồi của Agent bên trái.
- **Input Props**: `messages: ChatMessageItem[]; onOptionSelect: (option: string) => void; onHITLDecision: (approved: boolean, reason?: string) => void;`
- **Tiêu chí kiểm thử (DoD)**: Cuộn mượt mà; hiển thị đúng thứ tự thời gian.

---

#### Component 2.4: Tiến Trình Suy Luận Của Agent (Reasoning Timeline)
- **File**: `src/frontend/components/chat/ReasoningTimeline.tsx`
- **Nhiệm vụ**:
  - Trực quan hóa 4 bước suy luận của Agent khi trạng thái là `isLoading`:
    1. *Tra cứu lược đồ & giá trị danh mục (`schema-retriever`)*
    2. *Soạn thảo câu lệnh SQL (`sql-generator`)*
    3. *Kiểm duyệt an toàn AST, RBAC & Chi phí (`control-pipeline`)*
    4. *Dựng biểu đồ Recharts & Trích xuất Insight (`response-synthesizer`)*
  - Hiệu ứng pulsing light tạo cảm giác hệ thống đang tính toán thực sự.
- **Input Props**: `isActive: boolean; currentStep?: number;`
- **Tiêu chí kiểm thử (DoD)**: Hiển thị thanh tiến trình trực quan khi gửi câu hỏi và biến mất khi có kết quả trả về.

---

### PHASE 3: THẺ TRẠNG THÁI ĐẶC THÙ CỦA AI AGENT (AGENT STATE CARDS)

#### Component 3.1: Thẻ Làm Rõ Câu Hỏi (Clarification Card with Clickable Chips)
- **File**: `src/frontend/components/chat/ClarificationCard.tsx`
- **Nhiệm vụ**:
  - Hiển thị khi backend trả về `status: "CLARIFICATION_REQUIRED"`.
  - Hiển thị câu hỏi làm rõ từ Agent: *"Câu hỏi của bạn chưa đủ điều kiện lọc..."*.
  - Hiển thị danh sách các tùy chọn gợi ý `suggested_options` (ví dụ: `[A] Theo từng năm`, `[B] Theo 5 khu vực`, `[C] Theo phân khúc`).
  - Mỗi tùy chọn là một nút bấm tương tác (Clickable Chip). Bấm vào là lập tức gửi lựa chọn đó về backend.
- **Input Props**: `question: string; options: string[]; onSelectOption: (option: string) => void;`
- **Tiêu chí kiểm thử (DoD)**: Click vào chip kích hoạt `onSelectOption` với chuỗi tương ứng, hiển thị giao diện màu Amber cảnh báo nhẹ nhàng.

---

#### Component 3.2: Thẻ/Modal Phê Duyệt Con Người (HITL Approval Card)
- **File**: `src/frontend/components/chat/HITLApprovalCard.tsx`
- **Nhiệm vụ**:
  - Hiển thị khi câu lệnh truy vấn bảng lớn (`lineitem`) kích hoạt chốt chặn HITL (`status: "PENDING_APPROVAL"` hoặc `requires_hitl: true`).
  - Hiển thị câu lệnh SQL dự kiến (có format code).
  - Hiển thị dung lượng quét dự kiến (`estimated_cost_bytes` quy đổi sang MB).
  - Hai nút hành động:
    - **[✓ Phê Duyệt & Thực Thi]**: Màu xanh Emerald.
    - **[✕ Từ Chối]**: Màu đỏ Rose kèm ô nhập lý do tùy chọn.
- **Input Props**: `sql: string; estimatedBytes?: number; onApprove: () => void; onReject: (reason?: string) => void; isSubmitting: boolean;`
- **Tiêu chí kiểm thử (DoD)**: Bấm phê duyệt gửi tín hiệu `approve=True`, bấm từ chối gửi `approve=False`, có disabled state khi đang gửi request.

---

#### Component 3.3: Thẻ Thông Báo Lỗi & Vòng Lặp Tự Sửa Lỗi (Error & Retry Feedback Card)
- **File**: `src/frontend/components/chat/ErrorFeedbackCard.tsx`
- **Nhiệm vụ**:
  - Hiển thị khi truy vấn thất bại (`status: "ERROR"` hoặc `"EXECUTION_FAILED"`).
  - Giải thích nguyên nhân rõ ràng bằng tiếng Việt (ví dụ: vi phạm chính sách bảo mật RBAC đối với cột `c_phone`).
  - Hiển thị huy hiệu số lần đã thử tự sửa lỗi (ví dụ: *"Đã tự sửa lỗi 3/3 lần không thành công"*).
  - Nút gợi ý: *"Thử lại"* hoặc *"Sửa lại câu hỏi"*.
- **Input Props**: `errorMessage: string; errorType?: string; retryCount?: number;`
- **Tiêu chí kiểm thử (DoD)**: Hiển thị rõ nguyên nhân lỗi thân thiện, không làm sập giao diện khi gặp lỗi 500 từ server.

---

### PHASE 4: TRỰC QUAN HÓA & TRÌNH DIỄN DỮ LIỆU (ANALYTICS CANVAS)

#### Component 4.1: Thẻ Tóm Tắt Insight Kinh Doanh (Business Insight Card)
- **File**: `src/frontend/components/analytics/InsightCard.tsx`
- **Nhiệm vụ**:
  - Hiển thị đoạn văn tóm tắt nhận định phân tích kinh doanh do `response-synthesizer` sinh ra.
  - Nổi bật các con số chủ chốt, tỷ lệ tăng trưởng và xu hướng đáng chú ý.
  - Biểu tượng bóng đèn sáng `💡 Business Insight` tạo điểm nhấn trực quan.
- **Input Props**: `insightText: string; executionTimeMs?: number;`
- **Tiêu chí kiểm thử (DoD)**: Hiển thị văn bản mượt mà, hỗ trợ định dạng in đậm Markdown đơn giản.

---

#### Component 4.2: Biểu Đồ Động Đa Hình Thái Recharts (Dynamic Chart Visualizer)
- **File**: `src/frontend/components/analytics/DynamicChart.tsx`
- **Nhiệm vụ**:
  - Nhận `recharts_config` từ API và mảng `data` để tự động render biểu đồ tương ứng:
    - `bar`: BarChart (Doanh thu theo khu vực, Top sản phẩm).
    - `line`: LineChart (Xu hướng doanh số theo thời gian).
    - `area`: AreaChart (Biến động tích lũy).
    - `pie`: PieChart (Tỷ trọng phân khúc khách hàng).
  - Tích hợp `ResponsiveContainer`, Custom Tooltip định dạng tiền tệ đẹp mắt, Legend rõ ràng.
  - Có thanh công cụ nhỏ: Nút đổi nhanh loại biểu đồ (Bar $\leftrightarrow$ Line) và nút [Tải ảnh biểu đồ].
- **Input Props**: `data: Record<string, any>[]; config: RechartsConfig;`
- **Dependencies**: `recharts`.
- **Tiêu chí kiểm thử (DoD)**: Render đúng mọi loại biểu đồ theo JSON config; resize màn hình không bị vỡ layout chart.

---

#### Component 4.3: Bảng Số Liệu Chi Tiết Tương Tác (Interactive Data Table)
- **File**: `src/frontend/components/analytics/DataTable.tsx`
- **Nhiệm vụ**:
  - Hiển thị dữ liệu dạng bảng với danh sách cột `columns` và các dòng `data`.
  - Tự động căn lề: Cột chữ căn trái, cột số/tiền tệ căn phải và định dạng dấu phẩy phân cách hàng nghìn.
  - Hỗ trợ phân trang (Pagination: 10 dòng/trang) và sắp xếp cột (Sorting asc/desc).
  - Nút **[📥 Xuất file CSV]** gọi tiện ích `exportToCsv`.
- **Input Props**: `columns: string[]; data: Record<string, any>[]; title?: string;`
- **Tiêu chí kiểm thử (DoD)**: Phân trang mượt; bấm sắp xếp cột hoạt động chuẩn xác; bấm tải CSV xuất file đúng số dòng.

---

#### Component 4.4: Hộp Soát Xét SQL & Huy Hiệu Kiểm Duyệt (SQL & Governance Viewer)
- **File**: `src/frontend/components/analytics/SQLViewer.tsx`
- **Nhiệm vụ**:
  - Accordion có thể thu gọn / mở rộng với tiêu đề: *"Xem câu lệnh SQL & Kiểm duyệt an toàn"*.
  - Khối code SQL được tô màu cú pháp (Syntax Highlight) đẹp mắt.
  - Nút **[Copy SQL]** 1-click có tooltip *"Đã sao chép"*.
  - Các huy hiệu kiểm định an toàn: `AST Passed (SELECT Only)`, `RBAC Verified`, `Default Limit 1000`, `DuckDB Native`.
- **Input Props**: `sql: string; executionTimeMs: number; bytesScanned?: number;`
- **Tiêu chí kiểm thử (DoD)**: Bấm mở rộng xem được SQL; bấm copy sao chép chính xác câu lệnh vào clipboard.

---

### PHASE 5: TÍCH HỢP TOÀN TRÌNH & MÀN HÌNH ADMIN AUDIT (INTEGRATION & ADMIN)

#### Component 5.1: Bộ Kết Hợp Phản Hồi Hoàn Chỉnh (Message Item Composer)
- **File**: `src/frontend/components/chat/MessageItem.tsx`
- **Nhiệm vụ**:
  - Đóng gói toàn bộ các khối thành phần trên theo trạng thái phản hồi của Agent:
    - Nếu `CLARIFICATION_REQUIRED`: Render `ClarificationCard`.
    - Nếu `PENDING_APPROVAL`: Render `HITLApprovalCard`.
    - If `ERROR`: Render `ErrorFeedbackCard`.
    - Nếu `COMPLETED`: Render lần lượt `InsightCard` $\rightarrow$ `DynamicChart` $\rightarrow$ `DataTable` $\rightarrow$ `SQLViewer`.
- **Input Props**: `message: ChatMessage; onOptionClick: (opt: string) => void; onHITLSubmit: (approved: boolean) => void;`
- **Tiêu chí kiểm thử (DoD)**: Chuyển đổi mượt mà giữa các trạng thái dựa trên dữ liệu phản hồi từ backend.

---

#### Component 5.2: Trang Phân Tích Chính (Main Analytics Page)
- **File**: `src/frontend/app/page.tsx`
- **Nhiệm vụ**:
  - Trang chủ của ứng dụng: Kết nối `Header`, `Sidebar`, `MessageList`, `ChatInput`, `SchemaDrawer`.
  - Quản lý State chính: danh sách tin nhắn `messages`, trạng thái `isLoading`, `currentSessionId`, `userRole`.
  - Xử lý luồng gửi câu hỏi `askQuery` và tiếp nhận phê duyệt `approveQuery`.
- **Tiêu chí kiểm thử (DoD)**: Toàn bộ luồng hỏi - đáp - vẽ biểu đồ - xuất CSV hoạt động trơn tru từ đầu đến cuối trên trình duyệt.

---

#### Component 5.3: Bảng Nhật Ký Kiểm Toán Dành Cho Admin (Admin Audit Table & Page)
- **File**: `src/frontend/app/audit/page.tsx` & `src/frontend/components/admin/AuditTable.tsx`
- **Nhiệm vụ**:
  - Màn hình chuyên biệt dành riêng cho vai trò `Admin` để giám sát kiểm toán dữ liệu.
  - Bảng danh sách nhật ký Audit Logs lấy từ `GET /api/v1/audit/logs`.
  - Các cột: Thời gian, Người dùng, Vai trò, Câu hỏi, SQL, Trạng thái (`SUCCESS`, `BLOCKED_RBAC`, `BLOCKED_AST`, `BLOCKED_COST`), Thời gian (ms), Dung lượng quét.
  - Bộ lọc nhanh theo trạng thái và thanh tìm kiếm từ khóa câu hỏi.
  - Nếu người dùng chuyển sang vai trò `Analyst`: Tự động cảnh báo hoặc chuyển hướng về trang chủ để thể hiện đúng tính năng phân quyền.
- **Tiêu chí kiểm thử (DoD)**: Admin xem được toàn bộ lịch sử truy vấn; lọc được các lệnh bị chặn do vi phạm RBAC.

---

#### Component 5.4: Kiểm Thử Tích Hợp & Đóng Gói (E2E Sanity & Build Verification)
- **Nhiệm vụ**:
  - Chạy kiểm tra linting: `npm --prefix src/frontend run lint`.
  - Chạy build sản phẩm: `npm --prefix src/frontend run build`.
  - Kiểm thử liên thông thực tế giữa Frontend Next.js (`http://localhost:3000`) và Backend FastAPI (`http://localhost:8000`).
  - Viết tài liệu hướng dẫn khởi chạy trong `src/frontend/README.md`.
- **Tiêu chí kiểm thử (DoD)**: Lệnh build thành công không có warning; trang tải trong < 2 giây.

---

## 3. MA TRẬN PHỤ THUỘC & THỨ TỰ THỰC HIỆN CHI TIẾT

Bảng dưới đây là kim chỉ nam cho tiến độ triển khai từng component theo đúng thứ tự phụ thuộc:

| STT | Component ID | Tên Component | Tệp tin chính | Phụ thuộc trước | Kết quả kiểm thử cần đạt (DoD) |
|---|---|---|---|---|---|
| **#1** | **0.1** | **Next.js Project Scaffolding** | `src/frontend/package.json` | Không | Cài đặt package thành công, build sạch sẽ |
| **#2** | **0.2** | **Design System & Tailwind CSS** | `globals.css`, `tailwind.config.ts` | #1 | Dark theme tokens, font Inter hoạt động |
| **#3** | **0.3** | **TypeScript Interfaces** | `types/api.d.ts` | Không | Khớp 100% Pydantic Schemas của FastAPI |
| **#4** | **0.4** | **API Client Service** | `services/api.ts` | #3 | Hàm gọi API có typesafe và bắt lỗi mạng |
| **#5** | **0.5** | **CSV Exporter Utility** | `services/exportCsv.ts` | Không | Xuất file CSV UTF-8 đúng font tiếng Việt |
| **#6** | **1.1** | **Root Layout Shell** | `app/layout.tsx` | #2 | Áp dụng theme và khung sườn ứng dụng |
| **#7** | **1.2** | **Header & Warehouse Status** | `components/layout/Header.tsx` | #2, #4 | Hiển thị trạng thái kết nối DuckDB live |
| **#8** | **1.3** | **Role Switcher Component** | `components/layout/RoleSwitcher.tsx`| #3 | Chuyển đổi giữa Analyst và Admin |
| **#9** | **1.4** | **Sidebar & Session Manager** | `components/layout/Sidebar.tsx` | #2, #8 | Tạo phiên mới, danh sách lịch sử phiên |
| **#10**| **1.5** | **TPC-H Schema Drawer** | `components/layout/SchemaDrawer.tsx`| #2 | Ngăn tra cứu 8 bảng và cột cấm PII |
| **#11**| **2.1** | **Chat Input Bar** | `components/chat/ChatInput.tsx` | #2 | Phím tắt Enter/Shift+Enter, auto-resize |
| **#12**| **2.2** | **Prompt Presets Bar** | `components/chat/PromptPresets.tsx` | #2 | Thẻ câu hỏi mẫu kích hoạt gửi nhanh |
| **#13**| **2.4** | **Reasoning Timeline** | `components/chat/ReasoningTimeline.tsx`| #2 | Thanh tiến trình 4 bước suy luận mượt mà |
| **#14**| **3.1** | **Clarification Card (A/B/C)** | `components/chat/ClarificationCard.tsx`| #2, #3 | Clickable chips gửi ngay lựa chọn |
| **#15**| **3.2** | **HITL Approval Card** | `components/chat/HITLApprovalCard.tsx`| #2, #3 | Xem trước SQL, bấm Duyệt/Từ chối chuẩn |
| **#16**| **3.3** | **Error Feedback Card** | `components/chat/ErrorFeedbackCard.tsx`| #2 | Giải thích lỗi tiếng Việt, số lần retry |
| **#17**| **4.1** | **Business Insight Card** | `components/analytics/InsightCard.tsx`| #2 | Card làm nổi bật số liệu và nhận định |
| **#18**| **4.2** | **Dynamic Recharts Chart** | `components/analytics/DynamicChart.tsx`| #2, #3 | Render Bar, Line, Area, Pie theo JSON |
| **#19**| **4.3** | **Interactive Data Table** | `components/analytics/DataTable.tsx` | #2, #5 | Bảng phân trang, định dạng số, xuất CSV |
| **#20**| **4.4** | **SQL & Governance Viewer** | `components/analytics/SQLViewer.tsx` | #2 | Accordion tô màu SQL và nút sao chép |
| **#21**| **5.1** | **Message Item Composer** | `components/chat/MessageItem.tsx` | #14->#20 | Ghép nối linh hoạt theo trạng thái Agent |
| **#22**| **2.3** | **Message List Feed** | `components/chat/MessageList.tsx` | #21 | Cuộn mượt danh sách các lượt trao đổi |
| **#23**| **5.2** | **Main Analytics Page** | `app/page.tsx` | #7, #9, #11, #22 | Hoàn thiện trang tương tác phân tích chính |
| **#24**| **5.3** | **Admin Audit Dashboard** | `app/audit/page.tsx` | #4, #8 | Màn hình tra cứu và lọc Audit Log |
| **#25**| **5.4** | **E2E Polish & Verification** | Toàn bộ dự án | Tất cả | Build production pass, test liên thông tốt |

---

## 4. QUY TRÌNH REVIEW & KIỂM THỬ TỪNG COMPONENT CỦA AGENT

Để đảm bảo người dùng có thể theo dõi và review tiến độ một cách thoải mái và an tâm:

1. **Thông báo trước khi bắt đầu Component**: Nêu rõ Component đang chuẩn bị làm (ví dụ: *"Bắt đầu triển khai Component 0.3: Khai báo TypeScript Interfaces"*).
2. **Triển khai code ngắn gọn, chính xác**: Tạo đúng file quy định, không viết thừa dependencies.
3. **Tự xác minh (Self-Verification)**:
   - Chạy lệnh kiểm tra cú pháp TypeScript (`tsc --noEmit`) hoặc linter.
   - Kiểm tra logic không bị thiếu sót trường nào so với Pydantic backend.
4. **Báo cáo kết quả cụ thể**: Trình bày tóm tắt các file vừa tạo, giải thích logic và mời người dùng review trước khi bước sang component kế tiếp.
