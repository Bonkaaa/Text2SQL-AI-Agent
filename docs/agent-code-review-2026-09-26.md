# Báo cáo review code Agent Architecture

**Ngày review:** 2026-09-26  
**Phạm vi:** luồng agent v4 (preflight/supervisor, planner/executor/evidence/presentation, control pipeline, AST/RBAC, API query và dependency liên quan). Đã rà soát tĩnh mã nguồn; không chỉnh sửa logic ứng dụng và không chạy test/lint trong lượt review này.  
**Chuẩn đối chiếu:** `docs/agent-architecture-v4.md`, `docs/agent/agent-architecture-v3.md`, và guardrails trong `AGENTS.md`.

## Lỗi cần ưu tiên sửa

### 1. [P0] Client có thể tự nâng quyền bằng dữ liệu request — `src/api/routes/query.py:54-58`

`ask_query` lấy `user_id` và `role` trực tiếp từ body nếu được truyền, ghi đè UserContext do dependency cung cấp. Client có thể gửi `role=ADMIN` (hoặc user ID khác) để chạy truy vấn bằng quyền ADMIN; có thể chọn session khác để nhắm checkpointer. Vai trò phải được xác lập từ danh tính đã xác thực phía server, không nhận từ body/header tự khai nếu header chưa được gateway tin cậy xác minh.

### 2. [P1] RBAC cột nhạy cảm bị vượt qua bởi `SELECT *` — `src/utils/ast_sanitizer.py:91-99`, `src/utils/rbac_enforcer.py:49-56`

Sanitizer bỏ qua `*` khi thu thập `columns_used`, rồi RBAC chỉ kiểm tra danh sách cột này. `SELECT * FROM customer` do đó không liệt kê `c_phone`/`c_acctbal` và không bị chặn dù role có denied columns. Cần mở rộng wildcard theo schema trước khi authorize, hoặc từ chối wildcard trên bảng có cột nhạy cảm.

### 3. [P1] HITL của analytics không thể được resume qua endpoint hiện tại — `src/agents/analytics/task_executor.py:110-115`, `src/agents/control_pipeline/builder.py:125-140`, `src/api/routes/query.py:298-330`

Task executor gọi `run_control_pipeline` đồng bộ mà không truyền graph/checkpointer; pipeline tự tạo graph mới và kết thúc ngay khi nhận interrupt, trả `BLOCKED_HITL`. API `/approve` lại resume checkpointer của supervisor bằng `thread_id=session_id`, không phải graph con đó. Vì vậy luồng HITL mô tả trong kiến trúc không tiếp tục thực thi query đã duyệt; retry sau đó có thể tạo lại query thay vì resume checkpoint. Cần thống nhất checkpoint/thread ID và đưa pipeline pause/resume vào cùng graph có checkpoint, hoặc thiết kế một approval flow riêng được lưu bền vững.

### 4. [P1] Endpoint phê duyệt không ràng buộc người duyệt/phiên với người dùng — `src/api/routes/query.py:276-303`

`/approve` nhận `session_id` và quyết định từ body, không có dependency xác thực hay kiểm tra quyền ADMIN/quyền sở hữu phiên. Bất kỳ caller nào biết hoặc đoán session ID có thể gửi phê duyệt/từ chối và tác động tới phiên. Cần xác thực người gọi, kiểm tra quyền phê duyệt và ràng buộc session với chủ sở hữu/tenant.

### 5. [P1] Lỗi `EXPLAIN` được coi là truy vấn nằm trong ngân sách — `src/utils/db_connector.py:147-156`

Khi `EXPLAIN` thất bại (không parse được hoặc không ước lượng được), connector trả `is_within_budget=True` cùng mức 1024 bytes. Control pipeline vì vậy tiếp tục đến execute thay vì đóng an toàn. Cost guard cần fail closed khi estimate không tin cậy; phân biệt lỗi cú pháp với lỗi estimate chỉ khi đã có kiểm tra AST thích hợp.

### 6. [P2] API khai async nhưng gọi LLM/control pipeline đồng bộ — `src/agents/analytics/task_executor.py:103-115`, `src/agents/control_pipeline/builder.py:139`, `src/agents/control_pipeline/diagnostic.py:177-189`

`aexecute_analysis_task` gọi `generate_sql` và `run_control_pipeline` đồng bộ; pipeline dùng `graph.invoke`, diagnostic dùng `llm.invoke`. Các thao tác I/O chặn event loop của FastAPI/LangGraph, làm giảm concurrency và có thể khiến request khác bị treo khi truy vấn/LLM chậm. Cần dùng API async end-to-end hoặc đẩy tác vụ sync sang worker thread.

### 7. [P2] Cấu hình retry cho phép vượt giới hạn tối đa 3 lần — `src/agents/analytics/task_executor.py:64-69,92`

Mặc định là 3 retry, nhưng `max_retries` là tham số công khai không bị clamp; giá trị lớn hơn 3 tạo nhiều hơn 3 lần retry, trái guardrail `MAX_RETRIES = 3`. Hãy clamp/reject giá trị ngoài `[0, 3]` và làm rõ `retry_count` đang tính lần thử ban đầu hay số lần retry.

### 8. [P2] Audit ghi câu SQL vào trường `question` — `src/agents/control_pipeline/nodes.py:286-295`

AuditEvent được tạo với `question=state.get("sql", "")`; trường câu hỏi của người dùng bị mất và SQL có thể bị hiển thị như câu hỏi trong UI/export. Truyền nguyên câu hỏi qua ControlState và ghi đúng giá trị; đồng thời xem xét nguy cơ lưu literal nhạy cảm trong SQL audit.

## Rủi ro/điểm cần xác nhận thêm

- `require_admin_role` trong `src/api/dependencies.py:80-108` xem header `X-User-Role: Admin` là bằng chứng quyền ADMIN và tạo user ADMIN mặc định nếu không có `user_context`. Nếu API có thể truy cập trực tiếp không qua gateway tin cậy, endpoint audit cũng có thể bị chiếm quyền bằng header giả. Cần xác nhận trust boundary triển khai; trong mọi trường hợp nên lấy danh tính/role từ cơ chế xác thực server-side.
- `docs/agent-architecture-v4.md` ghi giới hạn phân tích tối đa 3 task; planner có clamp số task trả về, nhưng nên xác thực `max_analysis_tasks` ở cấu hình để ngăn giá trị cấu hình bất thường.
- Một số fallback regex/response scraping vẫn còn ở `src/api/routes/query.py:119-200`, dù kiến trúc v4 ghi mục tiêu typed artifacts và 0 regex. Đây là nguy cơ tương thích, dễ trả dữ liệu sai khi định dạng lời nói đổi; cần bỏ sau khi API chỉ còn nhận typed response contract.

## Kết luận

Ưu tiên sửa theo thứ tự: (1) xác thực danh tính/role phía server, (2) wildcard trong RBAC, (3) thiết kế lại HITL resume và bảo vệ `/approve`, (4) fail-closed cho cost estimate. Sau đó xử lý async và giới hạn retry, rồi sửa audit contract và loại bỏ regex scraping.

Review này là rà soát tĩnh, chưa xác nhận các lỗi bằng test thực thi. Nên bổ sung regression tests cho từng mục P0/P1 trước khi sửa/merge.

---

## Re-review sau cập nhật code (2026-09-26)

Đã kiểm tra lại các thay đổi hiện tại trong các file liên quan. Trạng thái dưới đây dựa trên code review tĩnh, chưa chạy regression tests.

| Issue | Trạng thái | Nhận xét |
|---|---|---|
| 1. Role escalation từ body | **Còn hở** | `ask_query` đã chặn body role khác role dependency, nhưng dependency vẫn lấy role trực tiếp từ `X-User-Role`. Nếu header do client kiểm soát thì vẫn tự nhận ADMIN được. `request.user_id` còn được dùng khi dependency trả `anonymous_user`; `session_id` từ body cũng được dùng làm thread ID. Cần identity/role/session ownership từ auth server-side. |
| 2. `SELECT *` bypass RBAC | **Đã xử lý trong code, cần test** | AST đánh dấu `has_star`, mở rộng cột theo bảng TPC-H và truyền flag vào RBAC. Cần kiểm tra thêm wildcard qua CTE/subquery, nhiều bảng và schema không thuộc danh mục TPC-H; trường hợp không mở rộng được phải fail closed. |
| 3. HITL không resume | **Đã có luồng store nhưng chưa triệt để** | Executor lưu pending approval và API `/approve` yêu cầu `require_admin_role`, sau đó chạy SQL và resolve store. Tuy nhiên store là dict trong RAM (`pending_store.py`), mất khi restart và không chia sẻ giữa worker; khóa theo `session_id` làm nhiều task trong cùng phiên ghi đè nhau. Phê duyệt thực thi trực tiếp mà không truyền timeout; kết quả được trả ở response approve nhưng chưa thấy nối về task/analytics run đã chờ. Chưa thể coi đây là durable resume. |
| 4. Bảo vệ `/approve` | **Cải thiện một phần, còn hở theo auth boundary** | Endpoint hiện yêu cầu admin dependency. Tuy nhiên `require_admin_role` vẫn tin header `X-User-Role` và tạo admin mặc định khi không có context; nếu header chưa được gateway xác thực thì caller vẫn có thể giả mạo quyền. |
| 5. Cost estimate fail-open | **DuckDB đã sửa; BigQuery còn hở** | DuckDB trả budget exceeded khi EXPLAIN lỗi. Nhưng BigQuery connector trả `is_within_budget=True` khi thiếu `google-cloud-bigquery` (`db_connector.py:321-330`), tức không có dry-run mà vẫn cho qua. Trường hợp này cần fail closed. |
| 6. Chặn event loop | **Đã xử lý tại analytics task executor** | `generate_sql` và `run_control_pipeline` đã được đưa qua `asyncio.to_thread`; diagnostic đồng bộ chạy bên trong worker thread. Tuy vậy preflight trong `arun_supervisor` vẫn gọi các hàm đồng bộ (`evaluate_input_preflight`); cần xác nhận latency/concurrency chấp nhận được hoặc chuyển sang async/thread. |
| 7. Giới hạn retries | **Đã xử lý, còn sai thông báo khi input vượt ngưỡng** | `effective_max_retries` đã clamp từ 0 đến 3 và vòng lặp dùng giá trị clamp. Log kết thúc vẫn dùng `max_retries + 1` thay vì `effective_max_retries + 1`, nên số lần thử được báo có thể sai; không làm vượt ngưỡng thực tế. |
| 8. Audit question | **Đã xử lý** | Pipeline nhận `question` và audit ghi `state.question` trước khi fallback sang SQL. |

### Các điểm còn phải sửa trước khi kết luận an toàn

1. Thay cơ chế role từ header bằng danh tính/role đã xác thực ở server hoặc gateway có trust boundary được đảm bảo; bỏ mặc định admin khi không có authenticated context. Ràng buộc `session_id` và `user_id` với chủ sở hữu đã xác thực.
2. Chuyển PendingApprovalStore sang storage dùng chung, bền vững và khóa theo approval/task ID duy nhất. Thực thi query đã duyệt với timeout; định nghĩa rõ cách trả kết quả vào tiến trình phân tích đang chờ.
3. Sửa nhánh BigQuery thiếu dependency thành fail closed.
4. Bổ sung tests hồi quy bảo mật cho giả mạo `X-User-Role`, wildcard, approve không quyền, restart/multi-worker pending store, query HITL timeout và dry-run BigQuery thiếu dependency.

**Kết luận re-review:** các sửa đổi đã khắc phục một số nguyên nhân gốc (wildcard RBAC, clamp retries, sync I/O trong task executor, audit question, lỗi EXPLAIN DuckDB, yêu cầu admin ở approve route). Chưa nên kết luận toàn bộ issue đã được sửa triệt để: ranh giới xác thực quyền vẫn yếu nếu headers không được xác minh, HITL store chưa bền vững/định danh đủ tốt, và BigQuery còn fail-open khi thiếu client. Không chạy test/lint trong lượt re-review này.

---

## Re-review lần 2 (2026-09-26)

Đã rà lại các điểm còn hở trong lượt trước và cập nhật code mới nhất. **Một số vấn đề đã được cải thiện, nhưng vẫn còn lỗi cần sửa; chưa thể kết luận đã an toàn hoàn toàn.** Đây tiếp tục là review tĩnh, chưa chạy regression tests.

### Các mục đã được sửa trong code hiện tại

- BigQuery fail-closed khi thiếu client hoặc dry-run lỗi (`src/utils/db_connector.py:321-359`).
- Store approval đã chuyển sang SQLite, có `approval_id` riêng và lưu `task_id` (`src/agents/control_pipeline/pending_store.py`).
- `/approve` đã yêu cầu admin dependency và truyền timeout thực thi (`src/api/routes/query.py:333-369`).
- API ask có kiểm tra session ownership; dependency admin đã chuyển sang `Depends(get_current_user_context)`.

### Các vấn đề vẫn còn

#### A. [P1] Admin vẫn có thể tự cấp quyền nếu `admin_api_key` chưa được cấu hình

`src/config.py` mặc định `app_env="development"` và `admin_api_key=None`. Trong `src/api/dependencies.py:69-85`, nếu role header là Admin và không cấu hình key, code cấp `UserRole.ADMIN` trực tiếp. Vì `get_current_user_context` chỉ đọc headers, client có thể đặt `X-User-Role: Admin`; `require_admin_role` sau đó chấp nhận context này. Nếu triển khai không ép cấu hình key hoặc không tắt nhánh dev này khi chạy production, `/approve` và `/audit/logs` vẫn bị chiếm quyền.

**Cần:** fail startup khi production thiếu secret/auth provider; không dùng header role làm credential; kiểm thử với `app_env=production` và key vắng/mismatch.

#### B. [P1] Bảo vệ session ownership hiện chỉ là dict trong RAM và anonymous không được phân biệt

`src/api/routes/query.py:39-56` lưu `_SESSION_OWNERS` trong bộ nhớ process. Nó mất sau restart và không đồng bộ nhiều worker. Ngoài ra điều kiện từ chối bỏ qua nếu `user_id == "anonymous_user"` hoặc owner là anonymous; mà danh tính mặc định/role đều được suy ra từ headers (`dependencies.py:48-95`). Do đó không tạo được ràng buộc sở hữu vững chắc giữa người thật và session; attacker có thể tranh session chung/được đoán. Session ID từ request tiếp tục được dùng làm thread ID.

**Cần:** ràng buộc phiên với principal đã xác thực, lưu ownership bền vững/chia sẻ, và không cho phép anonymous truy cập session đã tồn tại.

#### C. [P1] Approval có thể chạy lặp lại và kết quả chưa được nối về analytics task

`src/api/routes/query.py:355-369` tra approval mà không lọc `status="PENDING"`; store `get()` mặc định trả bản ghi mới nhất bất kể trạng thái (`pending_store.py:152-179`). Sau khi duyệt, trạng thái thành APPROVED nhưng không được tiêu thụ/xóa. Gửi lại cùng approval (hoặc session không có approval_id) có thể chạy lại câu SQL. Đây là truy vấn SELECT nhưng có thể gây chi phí/lặp tác vụ ngoài ý muốn.

Ngoài ra, kết quả được lưu trong `execution_result` (`query.py:384-397`) và trả về response approve, nhưng không thấy analytics graph/task đang `BLOCKED_HITL` được resume hoặc cập nhật artifact bằng kết quả đã duyệt. Đây là approval rồi chạy riêng, chưa phải resume đúng luồng nghiệp vụ.

**Cần:** atomic compare-and-set chỉ từ PENDING sang trạng thái đang xử lý; từ chối duplicate approve; bắt buộc `approval_id`; nối kết quả về task/session hoặc định nghĩa API rõ đây là một execution riêng và xử lý tiếp tục ở client.

#### D. [P2] SQLite store chưa chắc “chia sẻ giữa nhiều worker” trong mọi deployment

Store mặc định dùng đường dẫn tương đối `./data/pending_approvals.sqlite` (`pending_store.py:27`). Các worker cùng một máy/thư mục có thể chia sẻ file; container/replica với filesystem riêng thì không. `threading.Lock` chỉ đồng bộ trong một process. Tài liệu module hiện khẳng định multi-worker, nhưng điều đó chỉ đúng khi tất cả worker cùng mount chung file SQLite tương thích. Cần cấu hình đường dẫn tuyệt đối/chung hoặc dùng DB service khi scale nhiều host.

#### E. [P2] Xử lý approval đang ghép `session_id` và `approval_id` không nhất quán

Store ưu tiên tìm theo `approval_id` mà không kiểm tra `session_id` có khớp (`pending_store.py:164-172`), trong khi endpoint truyền cả hai (`query.py:355-359`). Người có quyền admin có thể gửi approval ID của session A kèm session B; lookup vẫn lấy record A, nhưng audit/resolve/response sau đó dùng `request.session_id` B. Cần xác thực cặp `approval_id + session_id` trong cùng truy vấn DB và dùng session lấy từ bản ghi cho mọi thao tác.

### Trạng thái tổng hợp sau re-review lần 2

| Nhóm | Trạng thái hiện tại |
|---|---|
| Body role escalation | Đã chặn khác role dependency, nhưng auth dependency còn cho tự khai Admin ở cấu hình dev/no-key. |
| Wildcard RBAC | Đã có triển khai mở rộng cột; cần regression tests cho CTE/subquery/schema lạ. |
| HITL durability | SQLite đã thêm; còn duplicate execution, không khớp session/approval và chưa resume analytics task. |
| `/approve` access control | Có admin dependency, nhưng phụ thuộc vào nguồn xác thực header và key cấu hình. |
| Cost estimate | DuckDB và BigQuery đã fail-closed theo code đã đọc. |
| Sync I/O và retries | Task executor đã chuyển sync calls sang worker thread; retry clamp đã có. |
| Audit question | Đã truyền câu hỏi nghiệp vụ xuống audit node. |

**Kết luận:** phần lớn issue được đề cập đã có thay đổi tương ứng, nhưng các lỗ hổng xác thực Admin và ownership phiên, cùng tính idempotent/consistency của HITL còn tồn tại. Cần sửa và chạy regression tests cho các tình huống nêu trên trước khi xác nhận “triệt để”.

---

## Re-review lần 3 (2026-09-26)

Đã kiểm tra code mới nhất cho các điểm A-E ở lần review trước. Một số issue đã được khắc phục rõ ràng; còn các vấn đề sau đây khiến tôi chưa thể xác nhận toàn bộ luồng đã ổn.

### Đã cải thiện

- `Settings.validate_production_security` bắt buộc `admin_api_key` có độ dài tối thiểu trong production; dependency từ chối cấp Admin nếu key thiếu/sai ở production (`src/config.py:114-123`, `src/api/dependencies.py:70-98`).
- Ownership session chuyển sang SQLite; `/approve` đã xác minh session/approval, claim `PENDING -> PROCESSING`, và trả kết quả cũ nếu đã duyệt.
- Cost guard BigQuery fail-closed khi thiếu client/dry-run lỗi.

### Còn lỗi cần xử lý

#### 1. [P1] User identity vẫn do client tự khai, làm vô hiệu hóa session ownership

`src/api/dependencies.py:49-68` tạo `user_id` trực tiếp từ `X-User-Id` (hoặc giá trị anonymous). Cơ chế SQLite ownership ở `query.py:40-53` chỉ so sánh user ID này với owner đã lưu. Caller có thể gửi `X-User-Id` của nạn nhân để vượt qua ownership check, hoặc chiếm phiên mới trước chủ sở hữu nếu biết/chọn session ID. `X-Admin-Token` bảo vệ role Admin trong production, nhưng không xác thực danh tính Analyst.

**Cần:** lấy user ID từ authentication principal đã xác minh (JWT/session/mTLS hoặc gateway có trust boundary chặt), không dùng header tùy ý làm danh tính; session mới nên do server tạo hoặc gắn với principal.

#### 2. [P1] Task ID tái sử dụng khiến analytics có thể nạp kết quả HITL cũ vào câu hỏi mới

`src/agents/analytics/task_executor.py:83-111` tìm approval đã APPROVED bằng cặp `session_id + task_id`, rồi trả ngay `execution_result`. Planner tạo task IDs như `task_1` theo từng AnalysisPlan. Nếu cùng session chạy câu hỏi mới và lại có `task_1`, nó có thể nhận kết quả approval của câu hỏi trước thay vì sinh/chạy SQL cho mục tiêu mới. Bản ghi APPROVED không được đánh dấu consumed và lookup không kiểm tra câu hỏi/hash SQL/request ID.

**Cần:** dùng run/analysis ID duy nhất cho mỗi lượt phân tích, gắn pending record với run/task/question hash, và consume nguyên tử sau khi analytics hydrate kết quả. Không đủ nếu chỉ dựa trên `session_id + task_id`.

#### 3. [P2] Approval bị kẹt PROCESSING nếu worker chết giữa claim và resolve

`claim_for_processing` cập nhật trạng thái `PENDING -> PROCESSING` trước khi chạy DB (`pending_store.py:263-315`). Nếu process/host dừng sau claim mà trước `resolve_pending_approval`, không có lease, timeout hay recovery path để trả trạng thái về PENDING/FAILED. Approval sẽ luôn trả `IN_PROGRESS` và không thể xử lý lại.

**Cần:** thêm `processing_started_at`/lease owner, cơ chế reclaim sau timeout, và trạng thái FAILED có thông tin lỗi; giữ chống chạy trùng khi worker cũ còn thực thi.

#### 4. [P2] Multi-host chia sẻ SQLite vẫn phụ thuộc filesystem triển khai

Store vẫn mặc định `./data/pending_approvals.sqlite` (`pending_store.py:27`). SQLite file có thể dùng chung giữa process trên cùng host khi cùng mount path; không tự đảm bảo chia sẻ giữa container/replica trên host khác. `threading.Lock` cũng chỉ bảo vệ mỗi process, dù transaction SQLite có thêm khóa file.

**Cần:** cấu hình persistent shared volume rõ ràng nếu triển khai single-host, hoặc dùng PostgreSQL/DB dùng chung khi có nhiều host; bỏ mô tả “multi-worker” không điều kiện.

### Kết luận lần 3

Các issue về admin key production, fail-closed BigQuery, duplicate approve đồng thời và session/approval mismatch đã được xử lý tốt hơn trong code. Nhưng identity của user thường vẫn spoofable qua `X-User-Id`; approval kết thúc có thể bị tái sử dụng sai cho lượt phân tích sau do task ID lặp; và PROCESSING không tự phục hồi sau crash. Vì vậy **chưa thể xác nhận các issue đã sửa triệt để**. Chưa chạy test/lint; cần regression tests cho các tình huống trên và kiểm thử đồng thời/restart store trước khi chốt.

---

## Re-review lần 4 (2026-09-26)

Đã rà các thay đổi hiện tại tập trung vào identity/session, định danh plan, lease approval và cấu hình store.

### Đã sửa trong code backend

- Session ownership được lưu SQLite và yêu cầu session token khi truy cập lại session; token được sinh ngẫu nhiên và so sánh constant-time (`pending_store.py:186-269`).
- Plan có UUID; task gắn `plan_id`. Pending record mang `plan_id`, hash mô tả task và trạng thái consumed; executor chỉ nạp kết quả approval chưa consumed theo các khóa này (`artifacts.py:122-164`, `task_executor.py:90-112`). Điều này giải quyết việc tái dùng kết quả cũ giữa các plan.
- Approval có trạng thái PROCESSING kèm thời điểm/owner và cho reclaim sau lease timeout (`pending_store.py:374-463`).
- Đường dẫn SQLite có cấu hình `pending_approvals_db_path`; nhiều host chỉ dùng chung nếu cấu hình cùng một storage thực sự dùng chung.

### Vấn đề còn lại

#### 1. [P1] Frontend không lưu hoặc gửi lại session token

Backend trả `session_token` trong `QueryResponse` (`query.py:307-310`) và yêu cầu token đó khi tiếp tục một session (`query.py:96-117`, `pending_store.py:247-269`). Nhưng frontend không có field token trong `src/frontend/types/api.ts`, `AppContext` không lưu token, và `page.tsx` chỉ gửi `session_id` cùng `role` (`page.tsx:50-56`). Vì vậy lượt hỏi đầu tạo token nhưng lượt hỏi tiếp theo cùng session sẽ không gửi token và bị HTTP 403. Cần lưu token an toàn ở client và gửi kèm request sau (body hoặc header), đồng thời không ghi token vào logs/local storage không cần thiết.

#### 2. [P1/P2] `X-User-Id` vẫn không xác thực danh tính; audit có thể bị giả mạo

`get_current_user_context` vẫn đặt `user_id` từ header `X-User-Id` (`dependencies.py:49-69`), và nếu không có thì endpoint dùng `request.user_id` (`query.py:98-105`). Session token ngăn người không có token đọc/tiếp tục một session đã tạo, nên lỗi chiếm quyền session trước đó đã được giảm đáng kể. Tuy vậy người gọi vẫn có thể tạo phiên mới với bất kỳ user ID nào; `audit_node` ghi user ID này làm actor. Do đó audit trail không chứng minh được ai đã thực sự gửi truy vấn. Đây là lỗi nếu hệ thống dùng user ID cho trách nhiệm giải trình hoặc chính sách theo từng cá nhân. Cần xác thực principal server-side hoặc ghi rõ rằng user ID hiện chỉ là nhãn tự khai, không phải danh tính đã xác minh.

#### 3. [P2] Reclaim lease có thể chạy query trùng nếu lease ngắn hơn thời gian thực thi thực tế

Lease mặc định 60 giây (`config.py:209-213`), query timeout mặc định 30 giây (`config.py:164-168`) nên mặc định có khoảng đệm. Nhưng đây là hai cấu hình độc lập; nếu timeout được tăng quá lease, worker thứ hai có thể reclaim PROCESSING trong khi worker đầu vẫn thực thi. Ngoài ra trạng thái store hiện không ràng buộc update resolve với `processing_owner`/lease owner. Cần validate `hitl_lease_timeout_seconds > query_timeout_seconds` hoặc dùng heartbeat/lease token và CAS theo owner khi hoàn tất.

#### 4. [P2, theo topology] SQLite không phải shared store đa host tự động

Đường dẫn cấu hình giải quyết việc chọn nơi lưu file nhưng vẫn là SQLite (`config.py:139-142`, `pending_store.py:36-45`). Nó phù hợp nếu mọi worker trên cùng host hoặc dùng filesystem mount có semantics khóa phù hợp. Các container/replica trên host riêng không tự chia sẻ file. Nếu deployment chỉ có một backend host thì đây không phải blocker; nếu scale đa host thì cần database service phù hợp hoặc xác nhận volume mount.

### Trạng thái tổng hợp lần 4

| Mục | Đánh giá hiện tại |
|---|---|
| Admin key production | Đã fail-closed ở production theo code; admin vẫn là shared-secret model, không phải identity provider. |
| Session ownership | Backend token hóa tốt hơn; frontend chưa truyền token nên multi-turn session bị lỗi. |
| Kết quả HITL cũ | Đã cô lập theo plan/task/hash và consumed flag. |
| PROCESSING crash | Có lease reclaim; còn cần bảo đảm lease không reclaim khi worker cũ vẫn chạy. |
| BigQuery estimate | Fail-closed. |
| SQLite deployment | Đủ cho single-host/shared mount được xác nhận; chưa tự đáp ứng multi-host. |

**Kết luận lần 4:** các lỗi backend về task/plan reuse và recovery approval đã được xử lý đáng kể. Chưa thể gọi toàn bộ luồng là OK vì frontend hiện không giữ session token để tiếp tục chat, và danh tính audit vẫn lấy từ giá trị tự khai. Nếu mục tiêu triển khai chỉ là một backend host, SQLite có thể phù hợp; cần xác nhận topology trước khi gọi phần lưu trữ đa worker/host là hoàn tất. Chưa chạy test/lint trong lần re-review này.
