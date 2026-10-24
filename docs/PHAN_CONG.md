# Bảng phân công chi tiết — OpenGuard Kids

## Cơ sở và cách sử dụng

Phân công đề xuất cho **3 sinh viên, 8 tuần, 15–20 giờ/người/tuần**. Chưa có tên và năng lực thực tế;
thay TV1–TV3 bằng tên/MSSV/GitHub handle khi nhóm thống nhất. Tuần là tuần tương đối, chưa gán ngày bắt đầu.
Đã đối chiếu file kế hoạch và 9 ảnh. Giữ bản nguồn tại PROJECT_BRIEF.md; giải quyết khác biệt 7/8 tuần tại DECISIONS.md.
Mỗi dòng là một task có thể chuyển thành GitHub issue; **tất cả công việc sản phẩm hiện chưa bắt đầu**.
Ước lượng bao gồm học, viết code, test và tài liệu đầu việc; không phải cam kết thời gian.

| Thành viên | Vai trò chính | Sở hữu file | Người review chính |
|---|---|---|---|
| TV1 — điền tên | Backend, dữ liệu, API; DNS resolver; triển khai server | server/, agent/dns/, deploy/, contracts/ | TV2; TV3 review API UI |
| TV2 — điền tên | Core policy/counter, Windows service/helper, sync; DNS adapter | agent/core/, agent/windows/, scripts/spikes/ | TV1; TV3 review IPC/Tray |
| TV3 — điền tên | Dashboard, Tray, E2E, tài liệu người dùng và demo | dashboard/, agent/tray/, tests/e2e/ | TV1; TV2 review IPC |

DNS chia resolver (TV1) và adapter Windows (TV2); Tray do TV3 viết UI, TV2 giữ helper/IPC.
Không giao toàn bộ test cho TV3: ai viết module phải viết unit/integration của module đó.

## TV1: công việc và kiến thức cho từng việc

| Mã | Tuần | Giờ | Phụ thuộc | Công việc và đầu ra | Kiến thức cần học | Bài thực hành / tiêu chí nghiệm thu |
|---|---|---:|---|---|---|---|
| A01 | 1 | 12 | — | Chốt SRS, ERD và API; docs/SRS.md, ERD.md; contracts/schemas | Use case, khóa ngoại/index, REST, JSON Schema, ownership | Vẽ luồng policy → agent → event; fixture mẫu được TV2/TV3 review; mỗi MVP có acceptance ID |
| A02 | 2 | 7 | A01 | Khởi tạo FastAPI/SQLAlchemy/Alembic, migration; server/app/db | Python typing, dependency injection, transaction, WAL/busy_timeout | Tạo DB trống bằng migration; kiểm tra khóa ngoại và concurrent read/write |
| A03 | 2 | 10 | A02 | Login/logout/me, session cookie, CSRF, children ownership | Password hashing, cookie HttpOnly/Secure/SameSite, CSRF, authorization | Hai gia đình không đọc/sửa chéo; logout mất session; request thiếu CSRF bị từ chối |
| A04 | 3 | 7 | A03 | Enrollment một lần, device token/revoke; server/app/auth | Random token, hash secret, expiry, rate limiting, transaction | Mã hết hạn/dùng lại bị từ chối; token revoke không dùng được; không lộ token log |
| A05 | 3 | 7 | A01,A04 | Policy snapshot và optimistic concurrency; API agent policy | Versioning, immutable snapshot, conflict handling, schema validation | Hai lần sửa cùng version có một conflict; agent khác không đọc được policy |
| A06 | 4 | 8 | A04 | Heartbeat và event ingestion/ACK; server/app/services | HTTP retry, UUID, unique constraint, idempotency, batch bounds | Lost ACK rồi gửi lại không nhân event; ACK chỉ sau commit; 180 giây mất liên lạc |
| A07 | 4–5 | 9 | A05,A06 | Request approve/reject và grant scope/expiry | State machine, atomic update, race condition, UTC/local date | Approve đồng thời chỉ có một grant; mở app không vượt manual lock/quota tổng |
| A08 | 5 | 7 | A04,A06 | Command queue/delivery/ACK/audit; contracts command | At-least-once delivery, allowlist, expiry, idempotent effects | Lệnh hết hạn không chạy muộn; delivered khác executed; không nhận shell command |
| A09 | 6 | 10 | A06,A07 | Report ngày/tuần, audit, retention; server/app/services | Aggregation, timezone, interval splitting, pagination, redaction | Không cộng đôi app/máy; tách nửa đêm; cleanup 30/90 ngày có test; ownership reports |
| A10 | 6–7 | 14 | A01,B01 | DNS rules và proxy; agent/dns; fixture domain .test | DNS UDP/TCP, A/AAAA/CNAME, TTL, IDNA, suffix boundary, cache/timeout | Unit domain boundary; proxy upstream giả; chặn self-forward; không query log toàn bộ |
| A11 | 7 | 7 | A09 | HTTPS lab, env, backup/restore; deploy và scripts | Reverse proxy/TLS, Docker Compose, SQLite backup consistency | Một worker; agent verify certificate; backup phục hồi được trên DB thử |
| A12 | 8 | 12 | A01–A11 | Integration/security review, báo cáo backend và hỗ trợ demo | Threat modeling theo ownership/CSRF/replay, evidence, Git review | Chạy T01/T02/T08–T11; nộp log/commit; giải thích được luồng TCP/HTTPS/ACK |

Tổng đầu việc TV1: **110 giờ**, dành thêm **26 giờ** cho review, họp tích hợp và dự phòng; tổng kế hoạch **136 giờ/người**.

## TV2: công việc và kiến thức cho từng việc

| Mã | Tuần | Giờ | Phụ thuộc | Công việc và đầu ra | Kiến thức cần học | Bài thực hành / tiêu chí nghiệm thu |
|---|---|---:|---|---|---|---|
| B01 | 1 | 16 | — | Spike SID/session, foreground/idle, IPC ACL, lock/disconnect, DNS backup; scripts/spikes | Windows Session 0, LocalSystem, SID, WTS, named pipe ACL, quyền admin | VM có phụ huynh/trẻ; đọc đúng phiên; phân biệt locked/disconnected; ghi ADR D03/D04 |
| B02 | 2 | 8 | A01,B01 | Thiết kế core models, Decision, clock; agent/core | Dataclass/typing, dependency inversion, wall-clock vs monotonic, fake clock | Core import không cần Windows; test fixture decision với reason_code thống nhất |
| B03 | 3 | 12 | B02,A05 contract | Engine lịch/quota/app/manual lock/grant; simulator | Interval [start,end), timezone, precedence, scope/expiry | Fake clock test biên lịch, quota nhóm, grant hết hạn; không dùng sleep thật |
| B04 | 3–4 | 10 | B02,B03 | Counter, SQLite checkpoint/restart, midnight/clock rollback | Foreground intervals, idle/sleep, persistence, high-water date | T03–T07/T17; app ≤ tổng máy; sleep không tăng; sai số crash đo theo checkpoint |
| B05 | 4 | 13 | B01,B03,B04 | Service/helper lifecycle, IPC validation và process enforcement | pywin32, psutil SID/session filtering, bounded IPC, recovery/backoff | T12/T16; không kill process phụ huynh/hệ thống; helper restart có giới hạn |
| B06 | 5 | 10 | A04–A06,B04 | Enroll client, heartbeat, policy cache, outbox/retry; agent/core | HTTP timeout/backoff/jitter, SQLite outbox, atomic apply | Offline 10 phút vẫn áp dụng; reconnect không nhân event; invalid policy giữ bản trước |
| B07 | 5–6 | 9 | A07,A08,B05,B06 | Command executor và request queue, manual lock/grant persist | Durable intent/result, idempotency, expiry, IPC ACK | T09–T11/T18; crash/replay không kéo dài grant; xác nhận session trước ACK |
| B08 | 6 | 6 | B05,C05 | Tích hợp Tray/helper, degraded counters và minh bạch telemetry | IPC schema, stale timestamp, thread boundary, measured vs estimated | Tray chết không giả usage=0; không gán app khi thiếu foreground; UI báo degraded |
| B09 | 7 | 12 | A10,B01 | DNS adapter preflight/backup/apply/rollback/restore; agent/windows | DHCP/static, IPv4/IPv6, adapter identity, port 53, loopback | T14/T15: proxy healthy trước đổi; restore đúng DHCP/static; lỗi có rollback |
| B10 | 8 | 12 | B05–B09 | Build PyInstaller, install/uninstall; VM sạch và báo cáo Windows | Packaging, SCM, scheduled logon helper, ACL file, recovery | Cài → enroll → restart → uninstall; DNS về gốc; ghi ca chưa chạy đúng thực trạng |

Tổng đầu việc TV2: **108 giờ**, dành thêm **28 giờ** cho review, họp tích hợp và dự phòng; tổng kế hoạch **136 giờ/người**.

## TV3: công việc và kiến thức cho từng việc

| Mã | Tuần | Giờ | Phụ thuộc | Công việc và đầu ra | Kiến thức cần học | Bài thực hành / tiêu chí nghiệm thu |
|---|---|---:|---|---|---|---|
| C01 | 1 | 12 | — | Phân tích 9 ảnh, user flow, acceptance UI và test plan | UX states, wireframe, actor/use case, traceability | Map từng màn hình đến API/FR; vùng mờ ghi giả định; kế hoạch T01–T18 |
| C02 | 2 | 9 | A01,C01 | Khởi tạo React TS Vite, layout, API client và CI frontend | TypeScript, React state/hooks, fetch, routing, CSS responsive | Build thật; có loading/empty/error; cookie/CSRF tích hợp cùng origin |
| C03 | 3 | 10 | C02,A03,A04 | Login, children/devices/pairing, selector; dashboard/src/pages | Forms, controlled input, session expiry, async error handling | Ghép thiết bị thật; mã hết hạn có lỗi rõ; đổi child/device không lẫn dữ liệu |
| C04 | 4 | 12 | C03,A05 | Form lịch/quota/app và hiển thị server/applied version | Validation, optimistic concurrency, immutable UI state | Không lưu lịch trùng/qua nửa đêm; conflict có thông báo; lưu khác đã áp dụng |
| C05 | 4–5 | 15 | C01,B02,B05 contract | Tray PySide6: trạng thái, lịch, cảnh báo, request, trang minh bạch | Qt signals/slots, event loop/thread, system tray, IPC client | UI không block khi mất IPC; không có device token; cảnh báo 5/1 phút; offline queued |
| C06 | 5–6 | 10 | A07,A08,B07,C03 | Màn hình request/command; luồng duyệt, khóa/hủy, miễn thời gian | State machine UI, polling, scope/expiry, retry feedback | queued/delivered/executed/failed/expired khác nhau; không toast thành công trước ACK |
| C07 | 6 | 10 | A09,C03 | Tổng quan và báo cáo tuần/ngày từ API; dashboard | Date/timezone formatting, chart data, missing/delayed telemetry | Số liệu khớp event dedup; đổi ngày/thiết bị đúng; không hard-code Bé An |
| C08 | 7 | 8 | A10,B09 contract,C04 | UI lọc web, domain/category/schedule và help | Domain normalization, allowlist/blocklist, giới hạn DNS/DoH | Lưu/đọc rule thật; giải thích Hạn chế=lịch; không bật SafeSearch giả |
| C09 | 7 | 10 | C04,C06,C07,C08 | Playwright E2E, accessibility cơ bản, test lỗi mạng | Locator ổn định, web E2E, fixture isolation, keyboard navigation | Luồng policy → applied → request → duyệt → grant; không bỏ assertion khi lỗi |
| C10 | 8 | 12 | C05–C09,B10 | Hướng dẫn người dùng, video/demo 8–10 phút, test evidence | Technical writing, test report, trình bày kiến trúc và giới hạn | VM demo thật; ảnh/log gắn commit; bản báo cáo tách đã làm/chưa làm |

Tổng đầu việc TV3: **108 giờ**, dành thêm **28 giờ** cho review, họp tích hợp và dự phòng; tổng kế hoạch **136 giờ/người**.

## Lịch giao việc và điểm tích hợp theo tuần

| Tuần | TV1 | TV2 | TV3 | Điểm nghiệm thu chung |
|---|---|---|---|---|
| 1 | A01: SRS/ERD/contracts | B01: spike Windows và DNS | C01: ảnh, flow, test plan | Chốt contract và cách thử Session 0; spike thất bại phải sửa phạm vi |
| 2 | A02–A03: DB/auth | B02: core/clock | C02: shell/client | CI cấu trúc + test module mới; schema review cả nhóm |
| 3 | A04–A05: pairing/policy | B03, bắt đầu B04 | C03: auth/pairing UI | Auth → enroll → đọc policy thật; simulator chạy fixture |
| 4 | A06, bắt đầu A07 | Hoàn tất B04, B05 | C04, bắt đầu C05 | Policy → service → đếm/chặn app mẫu đúng SID |
| 5 | Hoàn tất A07, A08 | B06, bắt đầu B07 | Hoàn tất C05, bắt đầu C06 | Offline/reconnect; request/command đi hết API và agent |
| 6 | A09, bắt đầu A10 | Hoàn tất B07, B08 | Hoàn tất C06, C07 | Duyệt → grant đúng một lần; báo cáo từ event thật |
| 7 | Hoàn tất A10, A11 | B09 | C08–C09 | DNS test domain, restore; E2E và HTTPS lab |
| 8 | A12 | B10 | C10 | VM sạch, đo chỉ tiêu, video, tài liệu và review bảo vệ |

Quỹ mỗi người 136 giờ/8 tuần = 17 giờ/tuần; toàn nhóm 408 giờ. Tuần nhiều việc cần
chuyển phần chuẩn bị/fixture sang tuần trước; mỗi cuối tuần cập nhật giờ thực tế và điều chỉnh.
Không đẩy triển khai Windows sang tuần cuối. Nếu trễ, hoãn toàn bộ extension trước.

## Hợp đồng bàn giao bắt buộc

| Bàn giao | Người viết → người nhận | Nội dung cần thống nhất | Hạn |
|---|---|---|---|
| Policy/Decision | TV1 + TV2 → TV3 | version, timezone, schedule, quotas, reason_code, remaining_seconds, next_transition_at | Tuần 1 bản nháp; tuần 2 chốt |
| Event/ACK | TV1 ↔ TV2 | UUID, boot_id, sequence, timestamp UTC, ACK sau commit, batch limit, dedup | Trước A06/B06 |
| Request/grant | TV1 ↔ TV2/TV3 | scope, app_id, device, local_date, expiry; pending/approved/rejected/expired | Trước A07/C06 |
| Command | TV1 ↔ TV2/TV3 | allowlist, expires_at, queued/delivered/executed/failed/expired, persistent result | Trước A08/B07 |
| IPC/Tray | TV2 ↔ TV3 | SID/session, stale telemetry, status/request/notification, ACL, error envelope | Tuần 1 nháp; trước B05/C05 |
| DNS | TV1 ↔ TV2/TV3 | rule precedence, UDP/TCP health, upstream/loopback, rollback, báo cáo tối thiểu | Tuần 1 nháp; trước A10/B09 |

Không chờ backend hoàn thành mới làm UI/core: dùng fixture hợp đồng trong test,
nhưng mock phải có nhãn và chỉ ở test/demo mode. Nghiệm thu luôn chạy API/agent thật.

## Lộ trình học trước khi nhận việc

| Người | Học trước | Bài thực hành nhỏ để chứng minh đã hiểu | Gắn với công việc |
|---|---|---|---|
| Cả nhóm | Git branch/PR/conflict; HTTP/TCP/TLS; JSON; unit vs integration; yêu cầu có acceptance | Mỗi người tạo nhánh, sửa một fixture, mở PR và review một PR; vẽ đường đi request/ACK | Tuần 1 và mọi PR |
| TV1 | Python typing → FastAPI validation → SQL/ORM/migration → session/CSRF/ownership | API thử với 2 owner; transaction unique constraint; giải thích vì sao ACK sau commit | A01–A08 |
| TV1 | DNS packet UDP/TCP, TTL/cache, IDNA/suffix → proxy và upstream | Resolve domain .test với upstream giả; test badexample.test không khớp example.test | A10 |
| TV2 | Python module/test/fake clock → state machine/timezone → SQLite bền vững | Cho fake clock tiến 90 giây active + 30 giây locked, tổng phải là 90 | B02–B04 |
| TV2 | Process/user/SID → Session 0/WTS → ACL/IPC → recovery | Helper chạy phiên trẻ gửi foreground; từ chối SID sai; ghi trạng thái lock/disconnect thật | B01/B05/B07 |
| TV2 | DHCP/static DNS, IPv4/IPv6 → backup/rollback → service packaging | Lưu DNS VM, dry-run thay đổi, khôi phục chính xác sau lỗi giả | B09/B10 |
| TV3 | HTML/CSS → TypeScript → React hooks/forms → API async và auth | Form lịch báo lỗi trùng, loading/lỗi mạng, không hiện saved nếu server từ chối | C02–C04 |
| TV3 | Qt event loop/signals/slots → worker thread → IPC client | Tray vẫn phản hồi khi service ngắt; status chuyển degraded, request hiện chưa gửi | C05 |
| TV3 | Playwright locator/assertion → E2E isolation → evidence | Thử request approve đến agent ACK; lỗi mạng phải có kỳ vọng rõ | C06/C09/C10 |

Tài liệu kỹ thuật cần đọc được liệt kê ngay trong PROJECT_BRIEF mục 13 (Microsoft Session 0,
GetLastInputInfo, LockWorkStation, SafeSearch). Với framework/thư viện, đọc tài liệu chính thức
đúng phiên bản đã chọn khi bắt đầu triển khai; bảng này chưa thay cho kiểm tra tương thích.

## Phân công nghiệm thu và bảo vệ

| Nhóm ca từ brief | Người chạy chính | Người kiểm chứng | Bằng chứng cần nộp |
|---|---|---|---|
| T01–T02 ownership/enrollment | TV1 | TV3 | API test, DB mới, 2 gia đình |
| T03–T07, T17 counter/time | TV2 | TV1 | Fake clock output, checkpoint/restart |
| T08–T11 offline/dedup/grant/expiry | TV1 + TV2 | TV3 | Log trước/sau reconnect, số event/grant không đổi khi replay |
| T12, T16, T18 Windows/IPC/lock | TV2 | TV1 | VM accounts/SID, trạng thái phiên, video/log không secret |
| T13 DNS boundary | TV1 | TV2 | Unit + proxy integration |
| T14–T15 DNS restore | TV2 | TV1 | DNS trước/sau, DHCP/static IPv4/IPv6 |
| Web/Tray và E2E toàn luồng | TV3 | TV1 + TV2 | Playwright report, screenshot và demo dữ liệu thật |

TV1 trình bày API/DB/bảo mật/DNS protocol; TV2 trình bày session/counter/offline/Windows;
TV3 trình bày UX, luồng E2E, kết quả thử và giới hạn. Cả ba phải giải thích kiến trúc tổng thể,
vì sao DNS không đo thời gian website và vì sao delivered chưa phải executed.

Mỗi task hoàn thành khi có file/code, test phù hợp, một review, tài liệu cập nhật và evidence;
ca chưa chạy ghi “chưa chạy”. Chỉ tiêu lab cần đo: policy ≤70s, nhận command ≤10s, xử lý app mẫu ≤3s.

## Việc mở rộng — chưa tính trong 408 giờ

| Việc | Chủ trì | Điều kiện bắt đầu |
|---|---|---|
| WebSocket notify + polling fallback | TV1/TV2 | Outbox/command qua retry đã ổn định |
| SafeSearch/YouTube adapter | TV1/TV2; TV3 UI | DNS MVP/restore pass, có môi trường kiểm thử cụ thể |
| Template tuổi preview, CSV | TV3/TV1 | E2E MVP pass; CSV có kiểm tra injection |
| 2FA và installer đẹp | TV1 / TV2 | Còn thời gian sau nghiệm thu tuần 8 |
