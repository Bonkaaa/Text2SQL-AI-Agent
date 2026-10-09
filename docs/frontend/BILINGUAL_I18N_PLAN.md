# KẾ HOẠCH TRIỂN KHAI HỖ TRỢ SONG NGỮ (I18N: TIẾNG VIỆT & ENGLISH)
## Frontend Text2SQL AI Data Workspace

> **Mã tài liệu**: `docs/frontend/BILINGUAL_I18N_PLAN.md`  
> **Ngày lập**: 09/10/2026  
> **Trạng thái**: Bản kế hoạch kỹ thuật chi tiết (Implementation-Ready Specification)  
> **Tham chiếu**: [`FRONTEND_IMPLEMENTATION_PLAN.md`](file:///d:/Text2SQL-AI-Agent/docs/frontend/FRONTEND_IMPLEMENTATION_PLAN.md), [`AGENTS.md`](file:///d:/Text2SQL-AI-Agent/AGENTS.md)  
> **Nguyên tắc thiết kế**: *YAGNI & Tinh gọn (Ponytail)* — Zero extra dependencies, Type-safe React Context, Instant 1-click Switch, LocalStorage Persistence.

---

## 1. MỤC TIÊU & ĐỊNH HƯỚNG SẢN PHẨM

### 1.1. Bối cảnh & Yêu cầu
Hiện tại toàn bộ giao diện Frontend của ứng dụng đang sử dụng nhãn hiển thị bằng tiếng Anh (English). Mục tiêu là bổ sung hỗ trợ **song ngữ toàn diện (Bilingual i18n: Tiếng Việt 🇻🇳 & English 🇬🇧)**:
1. **Chuyển đổi tức thì (Instant 1-Click Switch)**: Người dùng có thể chuyển đổi linh hoạt giữa Tiếng Việt và Tiếng Anh ngay trên thanh điều hướng đầu trang (`AppHeader`) và trong trang Cài đặt (`Settings`), không cần reload trang.
2. **Lưu trữ tùy chọn (Persistence)**: Lưu lựa chọn ngôn ngữ vào `localStorage` (`querypilot_locale`), tự động ghi nhớ cho các lần truy cập tiếp theo.
3. **Bản địa hóa chuẩn thuật ngữ Data & AI Enterprise**: 
   - Không dịch máy thô cứng. Sử dụng thuật ngữ phân tích dữ liệu chuyên nghiệp (Ví dụ: *Executive Summary* -> *Tóm tắt điều hành*, *Query Governance* -> *Quản trị & Kiểm soát truy vấn*, *Read-only Mode* -> *Chế độ chỉ đọc SELECT*, *AST Verified* -> *Đã kiểm duyệt cú pháp AST*).
4. **Không làm vỡ luồng hiện tại**: Giữ nguyên toàn bộ cấu trúc URL (không bắt buộc đổi route thành `/vi/...` hay `/en/...`), đảm bảo 100% tương thích ngược và bộ test hiện tại không bị ảnh hưởng.

---

## 2. KIẾN TRÚC KỸ THUẬT (TECHNICAL ARCHITECTURE)

### 2.1. Lựa chọn Giải pháp: Lightweight Type-safe React Context vs Thư viện Ngoài
| Tiêu chí | Dùng thư viện ngoài (`next-intl` / `react-i18next`) | Tự dựng Type-safe React Context (Khuyến nghị) |
|---|---|---|
| **Số lượng thư viện cài thêm** | 2-3 packages (`next-intl`, `@formatjs/...`) | **0 dependencies** (Thuần React + TypeScript) |
| **Ảnh hưởng Routing** | Yêu cầu Middleware đổi URL dạng `/[locale]/...` dễ lỗi SSR | **Giữ nguyên URL sạch** (`/workspace`, `/dashboard`...) |
| **Độ phức tạp build** | Cần cấu hình Next.js middleware, matcher phức tạp | **Đơn giản, build siêu tốc, không rủi ro hydration** |
| **Type Safety** | Cần plugin/schema generator | **100% Type-safe tự động qua TypeScript keyof dictionary** |
| **Tốc độ thực thi** | Parse json runtime, tốn memory | **Truy xuất trực tiếp qua object key O(1)** |

=> **Quyết định**: Triển khai giải pháp **Type-Safe React Context** tinh gọn theo đúng triết lý *Ponytail* của repository.

### 2.2. Sơ đồ Kiến trúc Luồng Dữ liệu i18n

```
                     ┌─────────────────────────────┐
                     │  localStorage               │
                     │  (querypilot_locale: vi/en) │
                     └──────────────┬──────────────┘
                                    │ (read/write)
                                    ▼
                     ┌─────────────────────────────┐
                     │   LanguageProvider          │
                     │   (context/LanguageContext) │
                     └──────────────┬──────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
┌────────────────────┐    ┌────────────────────┐   ┌────────────────────┐
│ TopBar Switcher    │    │ Settings Page      │   │ Tất cả 7 Trang &   │
│ (🇻🇳 VI / 🇬🇧 EN)     │    │ (Language Section) │   │ Components         │
│ Button toggle      │    │ Select dropdown    │   │ useLanguage().t    │
└────────────────────┘    └────────────────────┘   └────────────────────┘
```

---

## 3. CẤU TRÚC TỆP TIN & TỪ ĐIỂN DỊCH THUẬT

### 3.1. Các tệp sẽ tạo mới & cập nhật

```
src/frontend/
├── locales/
│   ├── index.ts                      # Xuất types Locale, Translations, getDictionary
│   ├── en.ts                         # Bản tiếng Anh (English master dictionary)
│   └── vi.ts                         # Bản tiếng Việt (Vietnamese dictionary)
├── context/
│   ├── LanguageContext.tsx           # Context quản lý state ngôn ngữ, localStorage & hàm t()
│   └── __tests__/
│       └── language.test.tsx         # Unit tests cho LanguageContext & hàm t()
├── components/
│   ├── layout/
│   │   ├── AppHeader.tsx             # Thêm nút chuyển nhanh ngôn ngữ (VI/EN pill)
│   │   ├── AppSidebar.tsx            # Áp dụng từ điển dịch cho navigation & database status
│   │   └── LanguageSwitcher.tsx      # Component nút chuyển đổi ngôn ngữ độc lập
│   ├── workspace/                    # Áp dụng song ngữ cho Composer, Canvas, 5 Tabs
│   ├── sources/                      # Áp dụng song ngữ cho Schema Explorer, Data Sources
│   └── dashboard/                    # Áp dụng song ngữ cho Dashboard KPIs & Activity Chart
└── app/
    ├── layout.tsx                    # Bọc LanguageProvider ngoài cùng RootLayout
    └── (app)/settings/page.tsx       # Bổ sung khu vực tùy chọn Ngôn ngữ (Language Selection)
```

### 3.2. Cấu trúc Khóa Từ điển Phân lớp (Hierarchical Dictionary Keys)

Từ điển sẽ được tổ chức theo module chức năng rõ ràng:
- `common`: Các từ dùng chung (`save`, `cancel`, `delete`, `search`, `export`, `copy`, `status`, `loading`, `error`, `rows`, `time`).
- `nav`: Điều hướng Sidebar & Topbar (`workspace`, `dashboard`, `savedQueries`, `history`, `dataSources`, `settings`, `help`, `notifications`).
- `workspace`:
  - `composer`: Gợi ý câu hỏi, placeholder, nút gửi, hướng dẫn phím tắt Enter.
  - `assistant`: Trạng thái xử lý (`schemaRetrieval`, `astValidation`, `queryExecution`).
  - `clarification`: Tiêu đề làm rõ câu hỏi, nhãn gợi ý.
  - `hitl`: Cảnh báo chi phí cao, nút phê duyệt / từ chối, lý do từ chối.
  - `views`:
    - `answer`: Tóm tắt điều hành, chỉ số chính, phân tích định lượng, phương pháp tính.
    - `table`: Tiêu đề bảng, phân trang, sao chép bảng, xuất CSV.
    - `chart`: Điều khiển loại biểu đồ (Bar, Line), trục X, trục Y, chú giải.
    - `sql`: Kiểm duyệt AST an toàn, chỉ đọc, sao chép SQL, chạy lại.
    - `trace`: Cây tiến trình, chi phí quét, thời gian từng chặng.
- `sources`:
  - `header`: Tiêu đề trang, trạng thái kết nối DuckDB, số bảng TPC-DS đã lập chỉ mục.
  - `explorer`: Tìm kiếm bảng, các tab phân hệ (Tất cả, Bán hàng, Trả hàng, Kho, Kích thước).
  - `detail`: Cột, Kiểu dữ liệu, Khóa chính, Khóa ngoại, Mô tả nghiệp vụ, nút "Hỏi về bảng này".
- `history`: Bộ lọc trạng thái (Tất cả, Thành công, Thất bại), Tìm kiếm, Chạy lại câu hỏi.
- `saved`: Quản lý câu hỏi đã lưu, Loại kết quả, Mở trong Workspace, Xác nhận xóa.
- `dashboard`: 4 thẻ KPI tổng hợp, biểu đồ thể tích truy vấn 7 ngày, danh sách câu hỏi phổ biến.
- `settings`: Hồ sơ phân tích, Quản trị truy vấn (Chế độ chỉ đọc, Giới hạn dòng), Chế độ phát triển, Xóa bộ nhớ cache, **Lựa chọn ngôn ngữ**.
- `auth`: Màn hình đăng nhập, Chọn tài khoản mẫu (Chuyên viên / Quản trị viên), Đăng nhập.

---

## 4. CHI TIẾT CÁC BƯỚC THỰC HIỆN (PHASED EXECUTION STEPS)

### Bước 1: Xây dựng Từ điển Song ngữ & Type Definitions
- Tạo `src/frontend/locales/en.ts` với đầy đủ bộ khóa từ điển tiếng Anh làm mẫu chuẩn.
- Tạo `src/frontend/locales/vi.ts` chuyển ngữ tiếng Việt chuyên nghiệp, tự nhiên, đúng thuật ngữ dữ liệu.
- Tạo `src/frontend/locales/index.ts` định nghĩa kiểu dữ liệu `Locale = 'vi' | 'en'` và kiểm tra type consistency giữa `en` và `vi` (bảo đảm mọi khóa trong `en` đều có đối ứng chính xác trong `vi`).

### Bước 2: Tạo LanguageContext & Hook `useLanguage()`
- Tạo `src/frontend/context/LanguageContext.tsx`:
  - State: `locale: Locale`, `setLocale: (locale: Locale) => void`.
  - Hàm `t(path: string): string` hỗ trợ truy xuất dot-notation an toàn (ví dụ: `t('nav.workspace')`, `t('workspace.composer.placeholder')`).
  - Khởi tạo: Đọc từ `localStorage.getItem('querypilot_locale')`, mặc định ưu tiên `'vi'` (hoặc giữ `'en'` nếu người dùng đã chọn trước đó).
- Tích hợp `LanguageProvider` vào `src/frontend/app/layout.tsx`.

### Bước 3: Thêm UI Chuyển đổi Ngôn ngữ (Language Switchers)
- **Trên TopBar (`AppHeader.tsx`)**:
  - Thêm component chuyển đổi ngôn ngữ dạng Pill button sang trọng:
    - Khi đang là Tiếng Việt: Hiển thị icon cờ 🇻🇳 kèm nhãn `VI`, bấm chuyển sang 🇬🇧 `EN`.
    - Thiết kế tối giản, đồng bộ với dark/light mode và các nút khác trên header.
- **Trong Trang Cài đặt (`settings/page.tsx`)**:
  - Bổ sung section **"Ngôn ngữ & Bản địa hóa" (Language & Localization)**:
    - Radio card hoặc dropdown cho phép chọn giữa **Tiếng Việt (Vietnamese)** và **English (Tiếng Anh)**.
    - Cập nhật state ngay lập tức khi người dùng chọn.

### Bước 4: Chuyển đổi các Component sang sử dụng `useLanguage`
1. **Khung giao diện chung (Layout)**:
   - `AppSidebar.tsx`: Chuyển đổi nhãn 6 trang menu, widget trạng thái DuckDB, Help card.
   - `AppHeader.tsx`: Breadcrumb, search placeholder, tooltip thông báo/trợ giúp.
2. **Trang Workspace & Các View**:
   - `QueryComposer.tsx`: Placeholder, gợi ý mẫu, phím tắt.
   - `ClarificationChips.tsx` & `HITLApprovalBanner.tsx`: Thông báo duyệt, nút hành động.
   - `ResultCanvas.tsx` & 5 Tabs (`AnswerView`, `DataTableView`, `ChartView`, `SQLViewer`, `TraceView`).
3. **Trang Data Sources**:
   - `DataSourceCard.tsx`, `SchemaExplorer.tsx`, `TableDetailView.tsx`.
4. **Trang History & Saved Queries**:
   - Tiêu đề cột, bộ lọc trạng thái, nút hành động Rerun / Open, Modal xóa.
5. **Trang Dashboard & Settings**:
   - Thẻ chỉ số KPIs, danh sách câu hỏi đề xuất, biểu đồ.
   - Form cài đặt và nút reset cache.
6. **Trang Đăng nhập (Login)**:
   - Form đăng nhập, vai trò người dùng mẫu.

### Bước 5: Kiểm thử Toàn diện & Xác thực (Verification)
- Viết unit tests cho `LanguageContext` (`language.test.tsx`): Kiểm tra giá trị mặc định, chuyển đổi locale, lưu vào localStorage, fallback key.
- Chạy toàn bộ test suite hiện có: `npm test` bảo đảm 72 tests cũ vẫn pass 100%.
- Kiểm tra linter: `npm run lint` đạt 0 lỗi.
- Kiểm tra build production: `npm run build` thành công hoàn toàn.

---

## 5. THIẾT KẾ GIAO DIỆN NÚT CHUYỂN ĐỔI NGÔN NGỮ (UI DESIGN)

### 5.1. Nút Language Switcher trên TopBar (`AppHeader.tsx`)
```tsx
<button
  type="button"
  onClick={() => setLocale(locale === "vi" ? "en" : "vi")}
  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-line bg-surface-2 hover:bg-surface text-xs font-semibold text-foreground transition-colors shadow-xs"
  title={locale === "vi" ? "Chuyển sang English" : "Switch to Tiếng Việt"}
>
  <span className="text-sm">{locale === "vi" ? "🇻🇳" : "🇬🇧"}</span>
  <span className="text-[11px] font-bold">{locale === "vi" ? "VI" : "EN"}</span>
</button>
```

### 5.2. Mục Tùy chọn Ngôn ngữ trong Trang Settings (`/settings`)
```tsx
<section className="bg-surface border border-line rounded-xl p-4 md:p-5 shadow-panel space-y-4">
  <div className="flex items-center gap-2 text-foreground font-bold text-sm">
    <Globe className="w-4 h-4 text-primary" />
    <h3>{t("settings.languageSectionTitle")}</h3>
  </div>
  <p className="text-muted text-xs leading-relaxed">
    {t("settings.languageSectionDescription")}
  </p>
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
    {/* Option Tiếng Việt */}
    {/* Option English */}
  </div>
</section>
```

---

## 6. DANH MỤC THUẬT NGỮ CHUYỂN ĐỔI CHUẨN (TERMINOLOGY MAPPING)

| Thuật ngữ Gốc (English) | Chuyển ngữ Chuẩn Tiếng Việt | Ngữ cảnh Sử dụng |
|---|---|---|
| **Workspace** | **Không gian làm việc** | Điều hướng chính, tiêu đề trang |
| **Data sources** | **Nguồn dữ liệu** | Menu, quản lý kho TPC-DS |
| **Query history** | **Lịch sử truy vấn** | Menu, lịch sử chạy truy vấn |
| **Saved queries** | **Truy vấn đã lưu** | Menu, danh sách câu hỏi lưu |
| **Dashboard** | **Bảng điều khiển** | Menu, trang tổng quan chỉ số |
| **Settings** | **Cài đặt** | Menu, trang cấu hình người dùng |
| **Ask anything about your data...** | **Hỏi bất kỳ điều gì về dữ liệu của bạn...** | Khung nhập câu hỏi (Query Composer) |
| **Run query** | **Chạy truy vấn** | Nút gửi câu hỏi / Chạy lại SQL |
| **Executive Summary** | **Tóm tắt điều hành** | Tab Answer View |
| **Key Metrics** | **Chỉ số quan trọng** | Tab Answer View (KPI cards) |
| **Quantitative Insights** | **Phân tích định lượng** | Tab Answer View |
| **Calculation Methodology** | **Phương pháp tính toán** | Tab Answer View |
| **AST Verified** | **Đã kiểm duyệt cú pháp AST** | Tab SQL View badge an toàn |
| **Execution Trace** | **Tiến trình thực thi** | Tab Trace View |
| **Clarification Required** | **Cần làm rõ câu hỏi** | Banner hội thoại khi câu hỏi mơ hồ |
| **Pending Approval (HITL)** | **Chờ phê duyệt an toàn (HITL)** | Banner duyệt khi chi phí lớn |
| **Approve / Reject** | **Phê duyệt / Từ chối** | Nút hành động HITL |
| **Strict Read-Only Mode** | **Chế độ chỉ đọc SELECT nghiêm ngặt** | Cài đặt bảo mật an toàn dữ liệu |
| **Ask about this table** | **Hỏi về bảng này** | Nút hành động tại Schema Explorer |

---

## 7. TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA)

1. **Khả năng chuyển đổi mượt mà**:
   - Bấm nút ngôn ngữ trên Header hoặc trong Settings chuyển đổi toàn bộ giao diện giữa Tiếng Việt và Tiếng Anh tức thì (<50ms).
   - Tùy chọn được lưu vào `localStorage`, khi mở tab mới hoặc F5 tải lại trang vẫn giữ nguyên ngôn ngữ đã chọn.
2. **Độ phủ ngôn ngữ (100% Core UI Coverage)**:
   - Cả 7 trang (`Workspace`, `Data Sources`, `Query History`, `Saved Queries`, `Dashboard`, `Settings`, `Login`) đều hiển thị tiếng Việt chuẩn xác và tự nhiên.
3. **Chất lượng code & Ổn định**:
   - TypeScript kiểm tra không có lỗi type mismatch.
   - Chạy `npm run lint` đạt 0 lỗi, 0 cảnh báo.
   - Bộ test suite hiện tại và các test mới của `LanguageContext` đều pass 100% (`npm test`).
   - Lệnh build `npm run build` chạy thành công.
