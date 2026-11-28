# Bảng phân công chi tiết — OpenGuard Kids

## Cơ sở và cách sử dụng

Phân công đề xuất cho **3 sinh viên, 5 tuần, trung bình 27,2 giờ/người/tuần**. Chưa có tên và năng lực thực tế;
thay TV1–TV3 bằng tên/MSSV/GitHub handle khi nhóm thống nhất. Lịch đã chốt: **26/10/2026–29/11/2026**, ngày địa phương UTC+7. Ngày kết thúc từng task là hạn hoàn thành trong ngày đó.
Đã đối chiếu [PDF đề bài chính thức ngày 05/11/2026](DoAn_UD_QL_SD_PC_TreEm.pdf), ma trận truy vết và 9 ảnh prototype. PDF quy định thời lượng 6 tuần; deadline nội bộ 5 tuần 26/10–29/11 vẫn giữ theo lựa chọn trước của người dùng để hoàn thành sớm.
Mỗi dòng là một task có thể chuyển thành GitHub issue; trạng thái thực tế xem `PROGRESS.md` (hiện mới có B01 spike và B02 core/tests).
Ước lượng bao gồm học, code, test và tài liệu; không phải cam kết. Quỹ cũ vẫn là 136 giờ/người (408 giờ nhóm), nhưng PDF đã đưa WebSocket, SafeSearch, security và M1–M6 thành bắt buộc nên nhóm phải re-estimate; không được ngầm coi các yêu cầu mới là đã nằm trọn trong số giờ cũ.

| Thành viên | Vai trò chính | Sở hữu file | Người review chính |
|---|---|---|---|
| TV1 — điền tên | Backend, dữ liệu, API; DNS resolver; triển khai server | server/, agent/dns/, deploy/, contracts/ | TV2; TV3 review API UI |
| TV2 — điền tên | Core policy/counter, Windows service/helper, sync; DNS adapter | agent/core/, agent/windows/, agent/spikes/ | TV1; TV3 review IPC/Tray |
| TV3 — điền tên | Dashboard, Tray, E2E, tài liệu người dùng và demo | dashboard/, agent/tray/, dashboard/e2e/ | TV1; TV2 review IPC |

DNS chia resolver (TV1) và adapter Windows (TV2); Tray do TV3 viết UI, TV2 giữ helper/IPC.
Không giao toàn bộ test cho TV3: ai viết module phải viết unit/integration của module đó.

## TV1: công việc và kiến thức cho từng việc

| Mã | Tuần | Bắt đầu | Deadline | Giờ | Phụ thuộc | Công việc và đầu ra | Kiến thức cần học | Bài thực hành / tiêu chí nghiệm thu |
|---|---|---|---|---:|---|---|---|---|
| A01 | 1 | 26/10/2026 | 28/10/2026 | 12 | — | Chốt SRS, ERD, API và traceability PDF; docs/SRS.md, ERD.md; contracts/schemas | Use case, privacy schema, REST, JSON Schema, ownership | Map F1–F5/NT1–NT6; fixture được TV2/TV3 review; mỗi yêu cầu có acceptance ID |
| A02 | 1 | 29/10/2026 | 30/10/2026 | 7 | A01 | Khởi tạo FastAPI/SQLAlchemy/Alembic, migration; server/app/db | Python typing, dependency injection, transaction, WAL/busy_timeout | Tạo DB trống bằng migration; kiểm tra khóa ngoại và concurrent read/write |
| A03 | 1–2 | 31/10/2026 | 02/11/2026 | 10 | A02 | Login/logout/me, role parent/child-view/admin, CSRF, ownership | Argon2id/scrypt, cookie 12h, lockout/rate limit, IDOR | Mật khẩu ≥10; 5 lỗi khóa 15 phút; hai gia đình không đọc chéo; logout server-side; thiếu CSRF bị từ chối |
| A04 | 2 | 03/11/2026 | 04/11/2026 | 7 | A03 | Enrollment 8 ký tự/10 phút, access token 15 phút + refresh/revoke | Random token, hash secret, expiry, rate limiting, transaction | Mã hết hạn/dùng lại bị từ chối; refresh/revoke đúng device; không lộ token log |
| A05 | 2 | 05/11/2026 | 06/11/2026 | 7 | A01,A04 | Policy snapshot versioned + HMAC/chữ ký, optimistic concurrency | Canonical serialization, integrity, immutable snapshot, schema validation | Sửa một byte bị agent từ chối; conflict giữ bản hợp lệ trước |
| A06 | 2–3 | 07/11/2026 | 09/11/2026 | 8 | A04 | Heartbeat và event ingestion/ACK; server/app/services | HTTP retry, UUID, unique constraint, idempotency, batch bounds | Lost ACK rồi gửi lại không nhân event; ACK chỉ sau commit; 180 giây mất liên lạc |
| A07 | 3 | 10/11/2026 | 11/11/2026 | 9 | A05,A06 | Request approve/reject và grant scope/expiry | State machine, atomic update, race condition, UTC/local date | Approve đồng thời chỉ có một grant; mở app không vượt manual lock/quota tổng |
| A08 | 3 | 12/11/2026 | 13/11/2026 | 7 | A04,A06 | Command queue/ACK/audit + WebSocket notify bắt buộc | At-least-once, allowlist, expiry, idempotency, reconnect | Lệnh khẩn <5 giây; polling fallback; delivered khác executed; không shell |
| A09 | 4 | 16/11/2026 | 18/11/2026 | 10 | A06,A07 | Report parent/child-view, audit, retention 90 ngày và delete-all | Aggregation, timezone, pagination, redaction, distributed deletion | Top 10; không cộng đôi; cleanup 90 ngày; xóa server + agent cache; ownership |
| A10 | 4 | 19/11/2026 | 22/11/2026 | 14 | A01,B01 | DNS proxy, 6 nhóm/≥200 mục, protected allowlist, SafeSearch | DNS UDP/TCP, IDNA/suffix, cache, SafeSearch mapping, dataset provenance | ≥95%/50, 0 false positive/20 giáo dục; nslookup/browser SafeSearch; không full query log |
| A11 | 5 | 23/11/2026 | 24/11/2026 | 7 | A09 | TLS 1.2+, certificate pinning, env, backup/restore | Reverse proxy/TLS, pin rotation, Docker Compose, SQLite backup | Pin sai bị từ chối; không disable verify; backup phục hồi được |
| A12 | 5 | 25/11/2026 | 28/11/2026 | 12 | A01–A11 | Integration/security review, báo cáo backend và hỗ trợ demo | Threat modeling theo ownership/CSRF/replay, evidence, Git review | Chạy T01/T02/T08–T11; nộp log/commit; giải thích được luồng TCP/HTTPS/ACK |

Tổng đầu việc TV1: **110 giờ**, dành thêm **26 giờ** cho review, họp tích hợp và dự phòng; tổng kế hoạch **136 giờ/người**.

## TV2: công việc và kiến thức cho từng việc

| Mã | Tuần | Bắt đầu | Deadline | Giờ | Phụ thuộc | Công việc và đầu ra | Kiến thức cần học | Bài thực hành / tiêu chí nghiệm thu |
|---|---|---|---|---:|---|---|---|---|
| B01 | 1 | 26/10/2026 | 29/10/2026 | 16 | — | Spike SID/session, foreground/idle, IPC ACL, lock/disconnect, DNS backup; agent/spikes | Windows Session 0, LocalSystem, SID, WTS, named pipe ACL, quyền admin | VM có phụ huynh/trẻ; đọc đúng phiên; phân biệt locked/disconnected; ghi ADR D03/D04 |
| B02 | 1 | 30/10/2026 | 01/11/2026 | 8 | A01,B01 | Thiết kế core models, Decision, clock; agent/core | Dataclass/typing, dependency inversion, wall-clock vs monotonic, fake clock | Core import không cần Windows; test fixture decision với reason_code thống nhất |
| B03 | 2 | 02/11/2026 | 04/11/2026 | 12 | B02, A01/A05 contract | Engine lịch 7×48/quota/app/manual lock/grant; warnings/grace; simulator | Interval [start,end), timezone, precedence, 10/5/1 phút, grace 60s | Quota 3 phút; slot 30 phút; khóa trong 5s sau grace; fake clock không sleep thật |
| B04 | 2 | 05/11/2026 | 07/11/2026 | 10 | B02,B03 | Counter/checkpoint/restart, midnight/clock rollback và server-time check | Foreground intervals, idle>5m, persistence, monotonic, high-water | Sai số ≤±30s/giờ; lùi 3h không tăng quota và phát clock event; sleep không tăng |
| B05 | 2–3 | 08/11/2026 | 10/11/2026 | 13 | B01,B03,B04 | Service/helper, IPC, app enforcement theo name+SHA-256 | pywin32, psutil SID/session/hash, bounded IPC, SCM recovery | Không thu window title; đổi tên app vẫn nhận hash; không kill parent/system; helper restart bounded |
| B06 | 3 | 11/11/2026 | 13/11/2026 | 10 | A04–A06,B04 | Enroll/token refresh, heartbeat 60s, signed policy cache, outbox | TLS pinning, HMAC/signature verify, backoff/jitter, DPAPI, server-time skew | Pin/policy sai bị reject; offline áp policy; reconnect không nhân event; secret có ACL |
| B07 | 3 | 14/11/2026 | 15/11/2026 | 9 | A07,A08,B05,B06 | WebSocket command notify + polling fallback, request queue, lock/grant persist | Reconnect, durable intent/result, idempotency, expiry, IPC ACK | Lệnh khẩn <5s; crash/replay không kéo dài grant; session xác nhận trước ACK |
| B08 | 4 | 16/11/2026 | 18/11/2026 | 6 | B05,C05 | Tích hợp Tray luôn hiện, degraded counter và minh bạch telemetry | IPC schema, stale timestamp, measured vs estimated, anti-stalkerware | Không icon thì dừng; không title/URL; Tray chết không giả usage=0; UI báo degraded |
| B09 | 4–5 | 20/11/2026 | 25/11/2026 | 12 | B01; A10 contract | DNS adapter preflight/backup/apply/rollback/restore + SafeSearch | DHCP/static, IPv4/IPv6, port 53, loopback, SafeSearch DNS | Restore đúng; rollback; nslookup/browser SafeSearch; dữ liệu adapter không lộ secret |
| B10 | 5 | 26/11/2026 | 28/11/2026 | 12 | B05–B09 | Build PyInstaller, install/uninstall; VM sạch và báo cáo Windows | Packaging, SCM, scheduled logon helper, ACL file, recovery | Cài → enroll → restart → uninstall; DNS về gốc; ghi ca chưa chạy đúng thực trạng |

Tổng đầu việc TV2: **108 giờ**, dành thêm **28 giờ** cho review, họp tích hợp và dự phòng; tổng kế hoạch **136 giờ/người**.

## TV3: công việc và kiến thức cho từng việc

| Mã | Tuần | Bắt đầu | Deadline | Giờ | Phụ thuộc | Công việc và đầu ra | Kiến thức cần học | Bài thực hành / tiêu chí nghiệm thu |
|---|---|---|---|---:|---|---|---|---|
| C01 | 1 | 26/10/2026 | 28/10/2026 | 12 | — | Phân tích PDF chính thức + 9 ảnh, user flow, acceptance UI/test plan | NT1–NT6, UX states, actor/use case, traceability | Map F1–F5 và T01–T23; ảnh chỉ là prototype; không hạ yêu cầu PDF |
| C02 | 1 | 29/10/2026 | 01/11/2026 | 9 | A01,C01 | Khởi tạo React TS Vite, layout, API client và CI frontend | TypeScript, React state/hooks, fetch, routing, CSS responsive | Build thật; có loading/empty/error; cookie/CSRF tích hợp cùng origin |
| C03 | 2 | 05/11/2026 | 07/11/2026 | 10 | C02,A03,A04 | Login, children/devices/pairing, selector; dashboard/src/pages | Forms, controlled input, session expiry, async error handling | Ghép thiết bị thật; mã hết hạn có lỗi rõ; đổi child/device không lẫn dữ liệu |
| C04 | 2–3 | 08/11/2026 | 10/11/2026 | 12 | C03,A05 | Form lịch 7×48/quota/app, integrity và server/applied version | Validation slot 30 phút, optimistic concurrency, immutable UI | Không lịch trùng/qua nửa đêm; conflict rõ; policy integrity/applied khác saved |
| C05 | 3 | 11/11/2026 | 15/11/2026 | 15 | C01,B02,B05 contract | Tray luôn hiện: trạng thái, cảnh báo 10/5/1, grace, request/báo chặn nhầm, minh bạch | Qt tray lifecycle, IPC, ngôn ngữ cấp 1, NT1–NT4 | Không icon thì agent dừng; không device token/title/URL; offline queued; lý do + người đặt luật |
| C06 | 4 | 16/11/2026 | 18/11/2026 | 10 | A07,A08,B07,C03 | Màn hình request/command; luồng duyệt, khóa/hủy, miễn thời gian | State machine UI, polling, scope/expiry, retry feedback | queued/delivered/executed/failed/expired khác nhau; không toast thành công trước ACK |
| C07 | 4 | 19/11/2026 | 21/11/2026 | 10 | A09,C03 | Parent + child-view: ngày/tuần, top 10, block/request, audit | Role UI, timezone, chart, missing telemetry, data deletion | Trẻ xem cùng dữ liệu/audit; delete-all có trạng thái; không hard-code Bé An |
| C08 | 5 | 23/11/2026 | 25/11/2026 | 8 | A10,B09 contract,C04 | UI 6 nhóm/domain/category/protected allowlist/SafeSearch và help | Dataset ≥200, DNS/DoH limits, source/provenance | Rule thật; SafeSearch chỉ báo bật sau nslookup/browser pass; protected allowlist không bị override |
| C09 | 5 | 26/11/2026 | 28/11/2026 | 10 | C04,C06,C07,C08 | Playwright E2E, accessibility cơ bản, test lỗi mạng | Locator ổn định, web E2E, fixture isolation, keyboard navigation | Luồng policy → applied → request → duyệt → grant; không bỏ assertion khi lỗi |
| C10 | 5 | 23/11/2026 | 29/11/2026 | 12 | Soạn từ 23/11; chốt sau C09/B10 | BaoCao.docx, M1–M6 PDF, PRIVACY/THREATMODEL/AI_USAGE, video 5–7 phút | Technical writing, traceability, evidence, % đóng góp | Đủ deliverable PDF trang 11; video tiếng Việt; README cài máy sạch ≤15 phút |

Tổng đầu việc TV3: **108 giờ**, dành thêm **28 giờ** cho review, họp tích hợp và dự phòng; tổng kế hoạch **136 giờ/người**.

## Lịch giao việc và điểm tích hợp theo tuần

| Tuần | Ngày | TV1 | TV2 | TV3 | Mốc nghiệm thu cuối tuần |
|---|---|---|---|---|---|
| 1 | 26/10–01/11 | A01–A02; bắt đầu A03 | B01–B02 | C01–C02 | SRS/ERD/contracts, spike SID/session/IPC/DNS, core và UI shell; auth đang triển khai |
| 2 | 02/11–08/11 | Hoàn tất A03; A04–A05; bắt đầu A06 | B03–B04; bắt đầu B05 | C03; bắt đầu C04 | Ghép thiết bị và policy thật; simulator/counter pass; bắt đầu tích hợp service |
| 3 | 09/11–15/11 | Hoàn tất A06; A07–A08 | Hoàn tất B05; B06–B07 | Hoàn tất C04; C05 | Service/Tray thật; offline/reconnect, request/grant và command qua API/agent; UI quản trị hoàn tất đầu tuần 4 |
| 4 | 16/11–22/11 | A09–A10 | B08; chuẩn bị B09 | C06–C07 | Luồng UI → API → agent hoàn chỉnh; báo cáo thật; DNS proxy pass, adapter chuẩn bị tích hợp |
| 5 | 23/11–29/11 | A11–A12 | Hoàn tất B09; B10 | C08–C10 | 25/11: DNS tích hợp; 28/11: chốt release candidate và test VM; 29/11: nghiệm thu, demo, bàn giao |

Quỹ mỗi người 136 giờ/5 tuần = 27,2 giờ/tuần; toàn nhóm 408 giờ. Thời gian làm việc trong
calendar là khoảng triển khai task, không phải đặt chỗ họp hoặc làm việc cả ngày.
Review và xử lý lỗi diễn ra xuyên suốt; ngày 29/11 dành cho nghiệm thu và bàn giao.
Các khoảng 23–29/11 của C10 bao gồm soạn hướng dẫn trước, ghi hình/evidence cuối cùng sau C09/B10.
B09 chỉ chuẩn bị adapter/rollback theo contract ngày 20–22/11; tích hợp DNS thật sau A10 ngày 23–25/11.

Mỗi cuối tuần đối chiếu đầu ra với mốc chung. Nếu nguồn lực thực tế vẫn chỉ 15–20 giờ/người/tuần,
nhóm có 225–300 giờ trong 5 tuần và phải chốt giảm phạm vi; lịch hiện tại giữ đủ MVP 408 giờ.
Không bỏ ownership/CSRF, offline dedup, SID/session hoặc DNS rollback để bù tiến độ.
Không được cắt WebSocket, SafeSearch, bảng phân loại ≥200 mục, policy integrity, retention 90 ngày hoặc tài liệu M1–M6 vì đây là yêu cầu bắt buộc. Có thể hoãn 2FA, PDF/CSV export, template tuổi, proxy HTTP(S)/WFP và installer đẹp.

Xem [lịch gửi nhóm và cách nhập Calendar](calendar/README.md).

## Hợp đồng bàn giao bắt buộc

| Bàn giao | Người viết → người nhận | Nội dung cần thống nhất | Hạn |
|---|---|---|---|
| Policy/Decision | TV1 + TV2 → TV3 | version, timezone, schedule, quotas, reason_code, remaining_seconds, next_transition_at | Chốt contract 28/10; API policy thật 06/11 |
| Event/ACK | TV1 ↔ TV2 | UUID, boot_id, sequence, timestamp UTC, ACK sau commit, batch limit, dedup | Contract 28/10; API 09/11; agent 13/11 |
| Request/grant | TV1 ↔ TV2/TV3 | scope, app_id, device, local_date, expiry; pending/approved/rejected/expired | Contract 28/10; API 11/11; agent 15/11; UI 18/11 |
| Command | TV1 ↔ TV2/TV3 | allowlist, expires_at, queued/delivered/executed/failed/expired, persistent result | Contract 28/10; API 13/11; agent 15/11; UI 18/11 |
| IPC/Tray | TV2 ↔ TV3 | SID/session, stale telemetry, status/request/notification, ACL, error envelope | Contract 28/10; service/helper 10/11; Tray 15/11 |
| DNS | TV1 ↔ TV2/TV3 | rule precedence, UDP/TCP health, upstream/loopback, rollback, báo cáo tối thiểu | Contract 28/10; proxy 22/11; adapter/UI 25/11 |

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
ca chưa chạy ghi “chưa chạy”. Ngưỡng chính thức: policy ≤60s, command khẩn <5s, khóa ngoài lịch ≤5s, usage ±30s/giờ; M4 dùng ≥30 mẫu/phép đo.

### Phân công phụ lục kỹ thuật mạng M1–M6

| Mục | Người viết chính | Người review/bằng chứng |
|---|---|---|
| M1 luồng DNS + capture | TV1 | TV2 chạy capture Windows |
| M2 so sánh hosts/DNS/HTTP(S)/WFP | TV1 | TV2 review giới hạn hệ thống |
| M3 ít nhất 7 bypass | TV2 | TV1/TV3 kiểm chứng, chỉ dùng miền an toàn |
| M4 CPU/RAM/DNS p50-p95/policy latency | TV2 | TV1 cung cấp server/upstream, ≥30 mẫu |
| M5 mất mạng/server down/agent kill | TV2 | TV3 đối chiếu trạng thái UI |
| M6 monotonic/server-time/clock skew | TV2 | TV1 cung cấp timestamp heartbeat |

## Việc mở rộng — chưa tính trong 408 giờ

| Việc | Chủ trì | Điều kiện bắt đầu |
|---|---|---|
| Template tuổi preview, CSV | TV3/TV1 | E2E MVP pass; CSV có kiểm tra injection |
| 2FA, YouTube Restricted Mode và installer đẹp | TV1 / TV2 | Sau deadline 29/11/2026; không nằm trong lịch 5 tuần |
| Proxy HTTP(S) hoặc WFP | TV1/TV2 | Chỉ làm khi MVP và M1–M6 đã pass; không TLS interception tùy tiện |
