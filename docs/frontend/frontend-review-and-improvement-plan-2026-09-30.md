# Review Frontend và hướng cải thiện theo kiến trúc Agent mới

**Ngày rà soát:** 2026-09-30  
**Phạm vi:** `src/frontend/` và các hợp đồng API/đầu ra hiện có ở `src/models/api_schemas.py`, `src/models/artifacts.py`, `src/api/routes/query.py`; đối chiếu định hướng trong `docs/agent-architecture-v4.md`.  
**Đặc tả thiết kế UI/UX mới:** Xem chi tiết tại [`docs/frontend/UI_UX_REDESIGN_SPECIFICATION.md`](file:///d:/Text2SQL-AI-Agent/docs/frontend/UI_UX_REDESIGN_SPECIFICATION.md).  
**Cách thực hiện:** Chỉ đọc mã nguồn và tài liệu. Không chạy ứng dụng, build, lint hoặc test; vì vậy đây là review tĩnh, chưa xác minh hành vi giao diện khi chạy.

## Tóm tắt

Frontend đã có nền tảng sản phẩm tương đối đầy đủ: khung chat, nhập câu hỏi, trạng thái làm rõ, phê duyệt HITL, báo lỗi, trình bày SQL, bảng, biểu đồ, xuất CSV và trang audit. Cấu trúc component theo khu vực chức năng giúp có thể cải tiến từng phần mà không cần viết lại toàn bộ giao diện.

Khoảng cách lớn nhất với kiến trúc Agent hiện tại nằm ở hợp đồng và cách trình bày kết quả. Frontend chủ yếu hiểu phản hồi kiểu một câu trả lời + một SQL + một bảng dữ liệu + một cấu hình biểu đồ (`QueryResponse` cũ), trong khi backend đã có các trường `response_package` và `output_artifacts`, với đầu ra gồm nhiều artifact như KPI, chart, table, evidence, callout và file. Vì vậy frontend chưa khai thác được kết quả phân tích nhiều bước/nhiều truy vấn theo cách mà Agent mới tạo ra.

## Hiện trạng tốt nên giữ lại

- **Có phân lớp giao diện:** các phần chat, analytics, layout, admin và API service đã tách thành thư mục/component riêng.
- **Đã có các trạng thái tương tác quan trọng:** clarification, HITL approval, lỗi và loading đều có component chuyên biệt.
- **Đã có primitive phân tích dùng lại được:** `DynamicChart`, `DataTable`, `SQLViewer` và `InsightCard` là nền tảng phù hợp để gắn với artifact renderer mới.
- **Có xử lý trải nghiệm cơ bản:** thông báo lỗi kết nối, timeout, health status, copy SQL và xuất CSV.
- **Có type API trung tâm:** `src/frontend/types/api.ts` là điểm tốt để thay đổi hợp đồng có kiểm soát.
- **Có test component sẵn trong repo:** đây là tài sản hữu ích cho giai đoạn triển khai sau; lần review này không chạy chúng theo yêu cầu.

## Phát hiện và khoảng cách kiến trúc

### P0 — Frontend chưa render hợp đồng kết quả mới

`src/models/api_schemas.py` đã khai báo `response_package`, `output_artifacts`, `tasks`, `metadata` và nhiều trường kết quả khác. `src/models/artifacts.py` định nghĩa artifact có discriminator `type`: `kpi`, `chart`, `table`, `evidence`, `callout`, `file`. Tuy nhiên `src/frontend/types/api.ts` chưa mô tả các contract này, còn `ChatMessageItem.tsx` chỉ tìm `recharts_config`, `data`, `columns`, `sql` và `final_answer`.

Hệ quả: câu trả lời nhiều phần (ví dụ insight + KPI + hai biểu đồ + bảng + dẫn chứng từ nhiều task) sẽ bị bỏ qua hoặc ép vào mô hình hiển thị cũ. Đây là điểm cần giải quyết trước khi đánh bóng UI.

**Đề xuất:** thêm kiểu discriminated union khớp chính xác Pydantic; tạo `ArtifactRenderer`/registry ánh xạ từng `type` vào component; ưu tiên đọc `response_package`, sau đó `output_artifacts`, cuối cùng dùng các trường đơn lẻ hiện có như đường tương thích tạm thời. Không suy diễn lại artifact từ nội dung văn bản khi API đã gửi dữ liệu có cấu trúc.

### P0 — Trạng thái API phía frontend không khớp đầy đủ backend

`QueryStatus` trong `src/frontend/types/api.ts` hiện chỉ gồm `COMPLETED`, `CLARIFICATION_REQUIRED`, `PENDING_APPROVAL`, `ERROR`, `EXECUTION_FAILED`. Backend cho phép thêm `SUCCESS` và `SECURITY_BLOCKED` (cùng `SECURITY_BLOCKED` được xử lý trong route). Nếu backend trả các trạng thái đó, luồng hiển thị hiện tại có thể rơi vào trạng thái mặc định thành công hoặc không thể hiện đúng lý do từ chối.

Ngoài ra, request frontend chưa có `session_token`; approval request chưa có `task_id`/`approval_id`, dù backend đã hỗ trợ các trường này. Điều này đặc biệt đáng lưu ý khi phiên Agent có nhiều task/phê duyệt.

**Đề xuất:** đồng bộ type với `api_schemas.py`; có một bộ chuyển trạng thái API → trạng thái UI tường minh; lưu và gửi session token; gắn hành động duyệt/từ chối với đúng approval/task thay vì chỉ dùng session hiện tại.

### P0 — Nhãn bảo mật đang tạo cảm giác xác thực không có bằng chứng

`ChatMessageItem.tsx` luôn hiển thị `AST Verified`, còn `SQLViewer.tsx` cũng luôn gắn huy hiệu này khi có SQL. Frontend không kiểm tra metadata tương ứng từ kết quả API. Với ứng dụng Text-to-SQL có yêu cầu SELECT-only, RBAC và cost guard, nhãn cứng này có thể khiến người dùng hiểu rằng câu truy vấn đã qua kiểm duyệt trong mọi trường hợp.

**Đề xuất:** chỉ hiển thị kết quả kiểm tra nếu backend trả về trạng thái/metadata kiểm soát rõ ràng; dùng nhãn trung tính như “SQL được đề xuất” cho câu đang chờ duyệt; trình bày trạng thái chặn hoặc chờ approval khác biệt. Không coi role switch ở giao diện là bằng chứng xác thực hoặc cấp quyền.

### P1 — Timeline suy luận không phản ánh tiến trình thực tế

`ReasoningTimeline` hiện dùng danh sách bước cố định. `ChatMessageItem` hiển thị timeline khi tải nhưng không nhận event từ backend; trang chính truyền `currentStep={2}` cố định cho trạng thái loading. Sau khi có kết quả, timeline cũng có thể hiện các bước như đã hoàn tất chỉ vì `isLoading` là false. Tên bước trong nội dung mặc định còn nhắc đến 8 bảng TPC-H, trong khi repo/kiến trúc hiện hỗ trợ cả TPC-H và TPC-DS, và pipeline v4 có preflight, planning, nhiều task, phân tích bằng chứng, tổng hợp artifact.

**Đề xuất:** giai đoạn đầu hiển thị trạng thái trung thực, không giả lập từng bước; nếu backend hỗ trợ stream/event, thiết kế contract event có `phase`, `status`, `task_id`, timestamp và thông điệp an toàn để hiển thị. Không đưa chain-of-thought nội bộ lên giao diện; chỉ hiển thị tiến trình tác vụ hoặc mô tả trạng thái đã được chủ động thiết kế cho người dùng.

### P1 — Session và hội thoại chưa được khôi phục đồng bộ

`AppContext.tsx` lưu danh sách session và ID phiên trong `localStorage`, nhưng `HomePage` giữ `messages` trong React state. Khi tải lại trang hoặc chọn session khác, nội dung hội thoại không được nạp từ API lịch sử; `getQueryHistory()` đã có ở service nhưng chưa được gọi trong luồng chính. Việc tạo ID ở client cũng cần được kiểm tra với quy tắc session ownership/token của backend.

**Đề xuất:** chọn backend làm nguồn sự thật cho session và lịch sử; định nghĩa API lấy đủ nội dung cần render hoặc endpoint chi tiết từng interaction; hiển thị loading/empty/error khi khôi phục; giữ cache local chỉ như tối ưu, có namespace theo người dùng/session. Đồng bộ chuyển session với việc nạp message, không chỉ đổi ID.

### P1 — Luồng clarification và HITL cần gắn đúng tương tác backend

Clarification hiện tiếp tục bằng cách gửi option như một câu hỏi mới; điều này có thể dùng cùng session nhưng frontend không biểu diễn rõ lượt clarification đang được trả lời hay giữ quan hệ với yêu cầu ban đầu. Approval handler tìm assistant message gần nhất đang chờ duyệt và gửi `session_id`; cách này có thể không đủ khi phiên có nhiều task hoặc nhiều approval, trong khi model backend đã có `approval_id` và `task_id`.

**Đề xuất:** xem clarification/approval như action có định danh, giữ liên kết tới message/task gốc; disable đúng card trong lúc gửi; sau phản hồi cập nhật đúng item. Trình bày rõ SQL, ước lượng chi phí, phạm vi duyệt và trạng thái kết quả sau quyết định.

### P1 — Role switcher là mô phỏng giao diện, không phải cơ chế xác thực

Vai trò lưu trong `localStorage` và được gửi từ client; trang audit cũng cho phép chuyển sang Admin bằng một nút. Đây có thể phù hợp cho demo cục bộ, nhưng không phải kiểm soát truy cập thật. UI ẩn/hiện chức năng theo role chỉ là trải nghiệm; API phải xác thực danh tính và quyền độc lập.

**Đề xuất:** ghi rõ chế độ demo trong giao diện nếu chưa có đăng nhập; không diễn đạt role switch như việc cấp quyền bảo mật. Khi tích hợp auth, lấy user/role từ session xác thực phía server và bỏ khả năng tự nâng quyền bằng local storage/request body.

### P2 — Dữ liệu schema và ngôn ngữ UI chưa nhất quán

Có cả `tpcdsSchema.ts` và `tpchSchema.ts`, trong khi nhiều component/tài liệu UI vẫn mặc định nói “TPC-H”, ví dụ subtitle của `InsightCard`, aria label của `DataTable`, timeline và tiêu đề assistant. Nếu chọn schema theo cấu hình/runtime chưa rõ, giao diện có thể mô tả sai nguồn dữ liệu đang truy vấn. Trang chào chính cũng dùng tiếng Anh giữa một sản phẩm và prompt chủ yếu tiếng Việt.

**Đề xuất:** lấy warehouse/schema context từ backend hoặc cấu hình có kiểu; truyền tên dataset/schema vào component thay vì hardcode; thống nhất ngôn ngữ UI, mặc định tiếng Việt nếu đây là trải nghiệm chính.

### P2 — API service và kiểu dữ liệu cần chặt chẽ hơn

`api.ts` chuẩn hóa lỗi theo tiếng Việt và có timeout tập trung, nhưng dùng `any` cho lỗi/chi tiết, ép kiểu response mà không runtime-validate, và endpoint audit gửi role từ client. `apiFetch` hiện không nhận token/session metadata dùng chung. Đây là điểm dễ sinh lệch contract khi backend phát triển nhanh.

**Đề xuất:** gom header/session handling vào API client; phân biệt timeout, offline, HTTP error và lỗi parse; validate phản hồi ở biên (bằng schema runtime nếu dự án chấp nhận dependency, hoặc parser/guard có kiểu); sinh type từ OpenAPI nếu pipeline backend hỗ trợ để tránh duy trì hai bản contract thủ công.

## Hướng kiến trúc frontend mục tiêu

```text
API response
  └─ API types + boundary parsing
       └─ Query/session state (loading, clarification, approval, result, error)
            └─ ResponsePackage adapter
                 └─ Artifact registry: KPI | Chart | Table | Evidence | Callout | File
                      └─ Existing presentation primitives
```

Nguyên tắc đề xuất:

1. **Hợp đồng có cấu trúc là nguồn dữ liệu chính.** Markdown chỉ dành cho phần văn bản giải thích, không parse Markdown để tái tạo bảng/biểu đồ nếu backend đã trả artifact.
2. **Renderer theo discriminator.** Mỗi loại artifact có component riêng, có fallback rõ ràng cho loại chưa được frontend hỗ trợ.
3. **Kết quả nhiều task phải giữ nguồn gốc.** Dùng `task_id`, `supporting_sql`, `executed_queries` để người dùng có thể xem bằng chứng/SQL liên quan, theo quyền backend cho phép.
4. **Tách trạng thái giao diện khỏi payload backend.** Mapper duy nhất chuyển response và event thành state dễ render; component không tự suy luận status bằng nhiều điều kiện rải rác.
5. **Bảo mật hiển thị theo dữ liệu xác thực.** Không suy ra quyền từ local storage và không khẳng định SQL đã được kiểm tra nếu API không xác nhận.
6. **Phiên làm việc có chủ sở hữu và khả năng phục hồi.** Nạp/lưu lịch sử cùng session, đồng thời bảo vệ token và không trộn state giữa các session.

## Lộ trình cải thiện đề xuất

### Giai đoạn 1 — Chuẩn hóa hợp đồng và trạng thái

- Đối chiếu frontend types với toàn bộ Pydantic response/request hiện tại.
- Thêm type `ResponsePackage`, artifact union, task metadata, safety/status fields, session token và approval identifiers.
- Tạo adapter cho payload mới và fallback tương thích payload cũ.
- Bổ sung trạng thái UI rõ ràng cho `SUCCESS`, `SECURITY_BLOCKED`, `CLARIFICATION_REQUIRED`, `PENDING_APPROVAL`, `ERROR`.

### Giai đoạn 2 — Render artifact của kiến trúc mới

- Tạo registry theo `artifact.type`.
- Nối artifact `chart` và `table` vào component có sẵn; thêm KPI, Evidence, Callout và File renderer.
- Tôn trọng `layout` của response package (`focus`, `stacked`, `dashboard_grid`) và metadata định dạng cột.
- Chỉ giữ parser Markdown như fallback chuyển tiếp; loại bỏ khi backend contract ổn định.

### Giai đoạn 3 — Làm chắc session, clarification và HITL

- Nạp lịch sử khi mở/chuyển session; định nghĩa cách khôi phục message và artifact.
- Gửi/nhận session token tập trung trong API service.
- Gắn approval vào `approval_id`/`task_id`; cập nhật đúng card/message.
- Biểu diễn clarification như một lượt tiếp diễn có liên kết tới câu hỏi ban đầu.

### Giai đoạn 4 — Tiến trình, bảo mật và hoàn thiện trải nghiệm

- Thay timeline giả lập bằng trạng thái backend thực có thể hiển thị an toàn.
- Loại bỏ các huy hiệu AST xác nhận cứng; làm rõ chế độ demo và giới hạn role switch.
- Đồng bộ tên schema, ngôn ngữ, trạng thái rỗng/loading/error và khả năng truy cập.
- Sau khi triển khai, chạy các kiểm tra phù hợp cho từng thay đổi và xác minh toàn luồng với backend; việc này nằm ngoài phạm vi review tĩnh hiện tại.

## Ưu tiên thực hiện

| Ưu tiên | Việc cần làm | Lý do |
|---|---|---|
| P0 | Hỗ trợ `response_package`/`output_artifacts` và artifact registry | Nếu không, frontend bỏ lỡ đầu ra chính của Agent mới |
| P0 | Đồng bộ API status/request types và session/approval identifiers | Tránh phân loại sai kết quả và action không đúng phiên/task |
| P0 | Bỏ khẳng định AST Verified không có căn cứ từ API | Tránh gây hiểu nhầm trạng thái an toàn |
| P1 | Khôi phục hội thoại theo session từ backend | Đảm bảo phiên agent hữu ích qua tải lại/chuyển phiên |
| P1 | Làm rõ clarification/HITL theo action id | Hỗ trợ đúng vòng tương tác và multi-task |
| P1 | Thay reasoning timeline mô phỏng bằng trạng thái trung thực | Khớp kiến trúc mới và tránh mô tả tiến trình không xảy ra |
| P2 | Chuẩn hóa schema, ngôn ngữ và API boundary parsing | Giảm lệch dữ liệu và tăng tính nhất quán |

## Kết luận

Frontend hiện tại là một nền demo tốt với nhiều component có thể tái sử dụng, nhưng chưa theo kịp hình thức đầu ra có cấu trúc và đa artifact của Agent v4. Hướng phù hợp là giữ shell/chat và các presenter hiện có, trước tiên cập nhật contract cùng state flow, rồi thêm artifact registry và hoàn thiện session/HITL. Các thay đổi về nhãn an toàn và role demo nên được xử lý sớm vì chúng tác động trực tiếp đến mức độ tin cậy mà giao diện tạo ra.
