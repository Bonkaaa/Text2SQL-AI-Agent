# Kế Hoạch & Tiến Độ Thực Hiện Frontend Text2SQL (Phase 2 & Next Steps)

> **Tài liệu tham chiếu gốc**:
> - Tài liệu phân rã thành phần gốc: [`docs/frontend/frontend-components-breakdown.md`](file:///d:/Text2SQL-AI-Agent/docs/frontend/frontend-components-breakdown.md)
> - Thiết kế UI/UX: [`docs/frontend/FRONTEND_DESIGN.md`](file:///d:/Text2SQL-AI-Agent/docs/frontend/FRONTEND_DESIGN.md)
> - Đặc tả API Gateway: [`docs/agent/component-5.1-fastapi-specification.md`](file:///d:/Text2SQL-AI-Agent/docs/agent/component-5.1-fastapi-specification.md)
> - Quy ước kỹ thuật: [`AGENTS.md`](file:///d:/Text2SQL-AI-Agent/AGENTS.md)
>
> **Mục đích tài liệu**: Đánh giá hiện trạng thực tế mã nguồn đã hoàn thành, cô lập trọng tâm **Phase 2 (Khung Nhập Liệu & Dòng Hội Thoại)** và cung cấp kế hoạch chi tiết từng bước để phát triển các component tiếp theo.

---

## 1. TỔNG QUAN TIẾN ĐỘ THỰC TẾ (REAL-TIME PROGRESS TRACKER)

Đối chiếu giữa kế hoạch 6 Phase trong tài liệu gốc và hiện trạng codebase tại `src/frontend`:

| Giai Đoạn (Phase) | Số Components | Trạng Thái Thực Tế | Tỷ Lệ Đạt | Đánh Giá Kỹ Thuật |
|---|:---:|:---:|:---:|---|
| **Phase 0: Nền Tảng & Hạ Tầng** | 5 | **ĐÃ HOÀN THÀNH** ✅ | **100%** (5/5) | Next.js 14 App Router, Dark Theme Tokens, TypeScript types ([`types/api.ts`](file:///d:/Text2SQL-AI-Agent/src/frontend/types/api.ts)), API Client ([`services/api.ts`](file:///d:/Text2SQL-AI-Agent/src/frontend/services/api.ts)), Mock Data generator. |
| **Phase 1: Bố Cục & Điều Hướng** | 5 | **ĐÃ HOÀN THÀNH** ✅ | **100%** (5/5) | Root Layout, Header (Health check DuckDB Live), RoleSwitcher (Analyst/Admin), Sidebar lịch sử, Schema Drawer 8 bảng TPC-H & cảnh báo PII. |
| **Phase 2: Nhập Liệu & Dòng Hội Thoại** | 4 | **ĐÃ HOÀN THÀNH** ✅ | **100%** (4/4) | Hoàn thành 100% bằng TDD: 2.1 (`QueryInputCard.tsx`), 2.2 (`PromptPresets.tsx`), 2.4 (`ReasoningTimeline.tsx`), 2.3 (`MessageList.tsx`) kèm 23 unit tests pass. |
| **Phase 3: Thẻ Trạng Thái Agent** | 3 | **ĐÃ HOÀN THÀNH** ✅ | **100%** (3/3) | Hoàn thành 100% bằng TDD: 3.1 (`ClarificationCard.tsx`), 3.2 (`HITLApprovalCard.tsx`), 3.3 (`ErrorFeedbackCard.tsx`) kèm 18 unit tests pass. |
| **Phase 4: Trực Quan Hóa Dữ Liệu** | 4 | **ĐÃ HOÀN THÀNH** ✅ | **100%** (4/4) | Hoàn thành 100% bằng TDD: 4.1 (`InsightCard.tsx`), 4.2 (`DynamicChart.tsx`), 4.3 (`DataTable.tsx`), 4.4 (`SQLViewer.tsx`) kèm 24 unit tests pass. |
| **Phase 5: Tích Hợp & Admin Audit** | 4 | **ĐÃ HOÀN THÀNH** ✅ | **100%** (4/4) | Hoàn thành 100% bằng TDD & CI: 5.1 (`AuditTable.tsx`), 5.2 (Trang Audit `app/audit/page.tsx`), 5.3 (`ChatMessageItem.tsx`), 5.4 (E2E Production Build & Sanity Check, 14 suites, 84/84 tests pass, Next.js 14 Build thành công). |
| **TỔNG CỘNG TOÀN BỘ FRONTEND** | **25** | **ĐÃ HOÀN THÀNH** ✅ | **100%** (25/25) | **Hệ thống Frontend đã sẵn sàng 100% cho Production (Enterprise-grade UI/UX)** |

---

## 2. RÀ SOÁT CHI TIẾT 4 COMPONENT CỦA PHASE 2 (ĐÃ HOÀN TẤT)

Phase 2 đã hoàn thành toàn bộ **trải nghiệm nhập liệu thông minh và luồng trao đổi hỏi - đáp** giữa người dùng và DeepAgents:

```
                  PHASE 2: CHAT INPUT & FEED COMPONENTS [HOÀN THÀNH 100% ✅]
 +-------------------------------------------------------------------------------+
 | [XONG ✅] Component 2.1: QueryInputCard.tsx (Pill Box, Model Switch, TDD: 8/8)  |
 +-------------------------------------------------------------------------------+
                                         |
                                         v
 +-------------------------------------------------------------------------------+
 | [XONG ✅] Component 2.2: PromptPresets.tsx (Gợi ý 4 nhóm TPC-H, TDD: 6/6)      |
 +-------------------------------------------------------------------------------+
                                         |
                                         v
 +-------------------------------------------------------------------------------+
 | [XONG ✅] Component 2.4: ReasoningTimeline.tsx (4 bước DeepAgents CoT, TDD: 6/6)|
 +-------------------------------------------------------------------------------+
                                         |
                                         v
 +-------------------------------------------------------------------------------+
 | [XONG ✅] Component 2.3: MessageList.tsx (Feed cuộn mượt mà tự động, TDD: 3/3) |
 +-------------------------------------------------------------------------------+
```

### Component 2.1: Khung Nhập Câu Hỏi & Phím Tắt (Chat Input Bar)
- **File**: [`src/frontend/components/chat/QueryInputCard.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/QueryInputCard.tsx)
- **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (8/8 tests pass)
- **Tính năng**: Pill chatbox, phím tắt `Enter` gửi, kiểm tra rỗng, `disabled` khi `isLoading`, spinner, Dropdown chọn mô hình TPC-H/Flash, Voice/Attachment icons, alias export `ChatInput`.

---

### Component 2.2: Thư Viện Câu Hỏi Mẫu Nổi Bật (Prompt Presets Bar)
- **File**: [`src/frontend/components/chat/PromptPresets.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/PromptPresets.tsx)
- **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 tests pass)
- **Tính năng**: 4 danh mục chuẩn TPC-H (Doanh thu vùng, Top khách hàng, Đơn giao trễ, Chiết khấu), bo góc `rounded-full`, dark mode pill hover effect, phím tắt Enter/Space, callback `onSelectPrompt`. Đã tích hợp vào `app/page.tsx`.

---

### Component 2.4: Tiến Trình Suy Luận Của Agent (Reasoning Timeline)
- **File**: [`src/frontend/components/chat/ReasoningTimeline.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/ReasoningTimeline.tsx)
- **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 tests pass)
- **Tính năng**: Trực quan hóa 4 bước DeepAgents CoT (Làm rõ ý định -> Schema Retriever -> SQL Generator -> Control Guard & Synthesizer), icon xoay khi loading, checkmark xanh khi hoàn tất, badge thời gian `executionTimeMs`, accordion đóng/mở. Đã tích hợp vào `ChatMessageItem.tsx`.

---

### Component 2.3: Danh Sách Hội Thoại & Tự Động Cuộn (Message Feed)
- **File**: [`src/frontend/components/chat/MessageList.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/MessageList.tsx)
- **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (3/3 tests pass)
- **Tính năng**: Quản lý feed hội thoại, tự động cuộn mượt mà `scrollIntoView` xuống cuối khi có tin nhắn mới hoặc bot đang phân tích, kết nối `ChatMessageItem` và `onApproveHitl`. Đã tích hợp vào `app/page.tsx`.

---

## 3. KẾ HOẠCH HÀNH ĐỘNG CHO PHASE 3 (AGENT INTERACTIVE CARDS)

Tiếp tục áp dụng quy trình **Test-Driven Development (TDD: Red -> Green -> Refactor)**:

1. **Component 3.1 — Thẻ Làm Rõ Câu Hỏi (Clarification Card with Clickable Chips)**:
   - File: [`src/frontend/components/chat/ClarificationCard.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/ClarificationCard.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Đã tích hợp vào `ChatMessageItem.tsx`, `MessageList.tsx`, và `app/page.tsx`.
2. **Component 3.2 — Thẻ Phê Duyệt Con Người (HITL Approval Card)**:
   - File: [`src/frontend/components/chat/HITLApprovalCard.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/HITLApprovalCard.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Hiển thị khi `status: "PENDING_APPROVAL"`, hiển thị dung lượng MB ước lượng (Cost Guard), xem trước câu lệnh SQL với cú pháp rõ ràng, nút [Phê duyệt] (Emerald) và [Từ chối] kèm modal/input lý do, hỗ trợ `isSubmitting` spinner loading. Đã tích hợp trọn vẹn vào `ChatMessageItem.tsx`, `MessageList.tsx`, và `app/page.tsx`.
3. **Component 3.3 — Thẻ Thông Báo Lỗi & Tự Sửa Lỗi (Error & Retry Feedback Card)**:
   - File: [`src/frontend/components/chat/ErrorFeedbackCard.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/ErrorFeedbackCard.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Phân loại lỗi thân thiện bằng tiếng Việt (`RBAC_VIOLATION`, `AST_BLOCKED`, `TIMEOUT`, `SYNTAX_ERROR`), hiển thị badge vòng lặp tự sửa lỗi (`Tự sửa lỗi: 3/3 lần thất bại`), accordion xem raw error details kèm nút [Sao chép mã lỗi], nút [Thử lại] (`onRetry`) gửi lại câu hỏi cuối. Đã tích hợp trọn vẹn vào `ChatMessageItem.tsx`, `MessageList.tsx`, và `app/page.tsx`.

---

## 4. KẾ HOẠCH HÀNH ĐỘNG CHO PHASE 4 (ANALYTICS CANVAS & DATA VISUALIZATION)

Sau khi hoàn thành 100% Phase 0, 1, 2 và 3, bước tiếp theo là nâng cấp các thành phần hiển thị kết quả phân tích dữ liệu:

1. **Component 4.1 — Thẻ Tóm Tắt Insight Kinh Doanh (Business Insight Card)**:
   - File: [`src/frontend/components/analytics/InsightCard.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/analytics/InsightCard.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Trình diễn nhận định kinh doanh sinh ra từ Synthesizer (`final_answer`), tự động định dạng markdown in đậm (`**KPI**`), hiển thị danh sách gạch đầu dòng bullet points (`- ` / `* `), badge thời gian xử lý `{executionTimeMs}ms`, nút [Sao chép nhận định] tiện lợi. Đã tích hợp thay thế text thô trong `ChatMessageItem.tsx`.
2. **Component 4.2 — Biểu Đồ Động Đa Hình Thái Recharts (Dynamic Chart Visualizer)**:
   - File: [`src/frontend/components/analytics/DynamicChart.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/analytics/DynamicChart.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Tự động vẽ `BarChart`, `LineChart`, `AreaChart`, `PieChart` dựa trên `recharts_config`. Tích hợp thanh công cụ chuyển đổi nhanh loại biểu đồ (Chart Type Switcher), bảng màu Enterprise (Indigo, Emerald, Amber, Cyan...), custom tooltip dark mode với định dạng số phân cách hàng nghìn, và fallback empty state khi không có dữ liệu. Đã tích hợp thêm tab **[📊 Biểu đồ]** trong `ChatMessageItem.tsx`.
3. **Component 4.3 — Bảng Dữ Liệu Chuyên Sâu TPC-H (Interactive Data Table)**:
   - File: [`src/frontend/components/analytics/DataTable.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/analytics/DataTable.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Tách rời bảng dữ liệu thành component độc lập với đầy đủ tính năng phân tích: sắp xếp cột (Column Sorting: asc/desc), tìm kiếm nhanh tức thì trên toàn bộ dữ liệu, phân trang linh hoạt (tùy chọn 5, 10, 20 dòng/trang), nút [Xuất CSV] tiếng Việt UTF-8 BOM chuẩn. Đã tích hợp thay thế bảng tĩnh trong `ChatMessageItem.tsx`.
4. **Component 4.4 — Hộp Xem & Sao Chép SQL Chuẩn Cú Pháp (SQL Viewer & Copy)**:
   - File: [`src/frontend/components/analytics/SQLViewer.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/analytics/SQLViewer.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Accordion đóng/mở linh hoạt ("Xem câu lệnh SQL & Kiểm duyệt an toàn"), tô màu cú pháp từ khóa SQL (`SELECT`, `FROM`, `WHERE`, `JOIN`, `GROUP BY`...), hệ thống huy hiệu kiểm định an toàn Enterprise (`AST Passed (SELECT Only)`, `RBAC Verified`, `Default Limit 1000`, `DuckDB Native`), badge thời gian thực thi `{executionTimeMs}ms` và dung lượng quét `{bytesScanned}`, nút [Sao chép SQL] 1-click mượt mà với clipboard API. Đã tích hợp thay thế khung SQL cũ trong `ChatMessageItem.tsx`.

---

## 5. KẾ HOẠCH HÀNH ĐỘNG CHO PHASE 5 (ENTERPRISE GOVERNANCE & ADMIN AUDIT VIEW)

Sau khi hoàn tất toàn bộ 4 Phase nền tảng và trực quan hóa, Phase 5 tập trung vào kiểm toán an ninh doanh nghiệp, phân quyền vai trò và hoàn thiện trải nghiệm người dùng:

1. **Component 5.1 — Bảng Nhật Ký Kiểm Toán Cho Quản Trị Viên (Admin Audit Table)**:
   - File: [`src/frontend/components/admin/AuditTable.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/admin/AuditTable.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Hiển thị bảng nhật ký truy vấn bảo mật: `timestamp` / `created_at`, `user_id`, `role`, `question`, `sql`, `status` (`SUCCESS`, `BLOCKED_RBAC`, `BLOCKED_AST`, `BLOCKED_COST`, `BLOCKED_HITL`, `TIMEOUT`, `DB_ERROR`), `execution_time_ms`, `bytes_scanned`.
   - Bộ lọc trạng thái đa năng (All, Thành công, Vi phạm RBAC, Chặn AST, Chặn chi phí, Lỗi khác) kèm bộ đếm số lượng bản ghi động.
   - Thanh tìm kiếm tức thì trên Client-side theo câu hỏi, câu SQL, mã người dùng, mã phiên.
   - Phân trang nâng cao (5, 10, 20, 50 dòng/trang).
   - Modal chi tiết truy vấn kiểm toán (Audit Detail Modal) hỗ trợ copy SQL, xem chi tiết lỗi kỹ thuật và thông tin phiên.
   - Xuất dữ liệu nhật ký ra tệp CSV UTF-8 BOM chuẩn tiếng Việt.
2. **Component 5.2 — Trang Quản Trị & Kiểm Toán Toàn Diện (Admin Audit Page)**:
   - File: [`src/frontend/app/audit/page.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/app/audit/page.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Cơ chế Role Gate bảo vệ phân quyền: khi người dùng là Analyst (`Nguyễn Văn An`), hiển thị màn hình từ chối quyền truy cập `403 Forbidden` kèm nút [Quay về trang phân tích] và [Chuyển sang vai trò Admin] để tiện kiểm thử phân quyền.
   - Khi là Admin (`Trần Thị Bình`): Tự động nạp dữ liệu từ API `GET /api/v1/audit/logs`, tính toán và hiển thị 4 thẻ KPI kiểm toán (Tổng số truy vấn, Tỷ lệ thành công, Vi phạm RBAC, Chặn AST & Chi phí).
   - Tích hợp bảng `AuditTable`, TopBar điều hướng quay về trang chủ và nút [Làm mới dữ liệu] tức thì.
3. **Component 5.3 — Chuẩn Hóa Bộ Kết Hợp Phản Hồi (MessageItem Composer Polish)**:
   - File: [`src/frontend/components/chat/ChatMessageItem.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/ChatMessageItem.tsx)
   - Unit test: [`src/frontend/components/chat/__tests__/ChatMessageItem.test.tsx`](file:///d:/Text2SQL-AI-Agent/src/frontend/components/chat/__tests__/ChatMessageItem.test.tsx)
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅ (6/6 unit tests pass).
   - Tối ưu hóa render logic điều phối chuẩn mực theo từng trạng thái Agent:
     - User Message: Bong bóng chat căn phải, timestamp và avatar `User`.
     - Bot Loading: Hiệu ứng `Sparkles` cùng `ReasoningTimeline` (bước 2 CoT đang chạy spinner).
     - `CLARIFICATION_REQUIRED`: Chỉ hiển thị `ClarificationCard` với danh sách chip tùy chọn.
     - `PENDING_APPROVAL`: Chỉ hiển thị `HITLApprovalCard` (không render bảng kết quả trước khi được duyệt).
     - `ERROR` / `EXECUTION_FAILED`: Chỉ hiển thị `ErrorFeedbackCard` kèm phân loại lỗi và nút [Thử lại].
     - `COMPLETED`: Hiển thị `InsightCard` cùng các tab chuyển đổi linh hoạt `DynamicChart` $\leftrightarrow$ `DataTable` $\leftrightarrow$ `SQLViewer`.
   - Export alias `export { ChatMessageItem as MessageItem }` chuẩn hóa.
4. **Component 5.4 — Kiểm Thử Liên Thông, Rà Soát Toàn Bộ & Build Production (E2E Sanity & Production Build Verification)**:
   - **Trạng thái**: **ĐÃ HOÀN THÀNH 100%** ✅.
   - **Kết quả nghiệm thu kỹ thuật**:
     - **ESLint 8 + Next.js 14**: `npm run lint` đạt `✔ No ESLint warnings or errors` (0 warnings, 0 errors, exit code 0). Cấu hình tương thích sạch `.eslintrc.json`.
     - **Vitest Suites**: 14 test suites, **84/84 tests PASS 100%** (thời gian chạy ~13s).
     - **TypeScript Typecheck**: `npx tsc --noEmit` đạt chuẩn nghiêm ngặt, **0 type errors**.
     - **Production Build**: `npm run build` thành công xuất sắc (exit code 0), tối ưu hóa bundle tĩnh cho cả 2 routes chính (`/` kích thước 151 kB / First Load 250 kB, `/audit` kích thước 10.2 kB / First Load 109 kB).
   - **Đóng gói toàn diện**: Toàn bộ 25 components thuộc 6 Phase từ Phase 0 đến Phase 5 đã hoàn thành đồng bộ, sẵn sàng kết nối liền mạch với FastAPI Backend.

---

## 6. BẢNG TỔNG KẾT NGHIỆM THU TOÀN DIỆN FRONTEND (PHASE 0 - PHASE 5)

| Phase | Thành Phần (Components) | Mã Nguồn Chính | Số Test | Kết Quả Test | Trạng Thái |
|:---:|---|---|:---:|:---:|:---:|
| **0** | Hạ tầng, Theme, Mock, API Client | `services/api.ts`, `types/api.ts`, `mock/` | CI | Type-safe | **Hoàn Thành** ✅ |
| **1** | Layout, Header, RoleSwitcher, Sidebar, SchemaDrawer | `Header.tsx`, `Sidebar.tsx`, `SchemaDrawer.tsx` | UI | Type-safe | **Hoàn Thành** ✅ |
| **2** | QueryInputCard, PromptPresets, ReasoningTimeline, MessageList | `components/chat/` | 23 | 23/23 PASS | **Hoàn Thành** ✅ |
| **3** | ClarificationCard, HITLApprovalCard, ErrorFeedbackCard | `components/chat/` | 18 | 18/18 PASS | **Hoàn Thành** ✅ |
| **4** | InsightCard, DynamicChart, DataTable, SQLViewer | `components/analytics/` | 24 | 24/24 PASS | **Hoàn Thành** ✅ |
| **5** | AuditTable, Admin Audit Page, ChatMessageItem, Build Sanity | `components/admin/`, `app/audit/`, `ChatMessageItem.tsx` | 19 | 19/19 PASS | **Hoàn Thành** ✅ |
| **TỔNG** | **25 Components / Modules** | **Toàn bộ `src/frontend`** | **84** | **84/84 PASS (100%)** | **PRODUCTION READY 🚀** |

