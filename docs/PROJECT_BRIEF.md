# Kế hoạch đồ án và bộ prompt coding agent — Người Bạn Đồng Hành (OGK)

> Cập nhật 26/10/2026 theo yêu cầu người dùng: kế hoạch hiện hành là **5 tuần, 26/10–29/11/2026**. Chi tiết từng task và deadline xem [PHAN_CONG.md](PHAN_CONG.md); lịch gửi nhóm tại [calendar/README.md](calendar/README.md). [Bản nguồn trước cập nhật](reference/Ke-hoach-va-prompt-OGK.original.md).

## 1. Cơ sở và giả định

Tài liệu được xây dựng từ 9 ảnh người dùng cung cấp: 3 ảnh đầu mô tả kiến trúc; 6 ảnh sau thể hiện dashboard demo. Một số vùng ảnh bị mờ hoặc che, vì vậy các chi tiết không đọc rõ không được xem là yêu cầu đã xác nhận.

Giả định để lập kế hoạch: 3 sinh viên, 5 tuần (26/10–29/11/2026), trung bình 27,2 giờ/người/tuần; demo với 1 máy Windows được quản lý, 1 phụ huynh và 1 trẻ. Hệ thống dữ liệu vẫn hỗ trợ nhiều gia đình và thiết bị, nhưng bản đầu chỉ hỗ trợ 1 phiên trẻ hoạt động trên mỗi thiết bị; tổng hạn mức tính riêng từng thiết bị. Máy trẻ dùng tài khoản Windows standard user; tài khoản quản trị thuộc phụ huynh. Nếu cần tổng hạn mức chung cho nhiều máy hoặc Fast User Switching đầy đủ, phải mở rộng thiết kế.

Tên đề tài gợi ý: “Xây dựng hệ thống quản lý thời gian và hoạt động sử dụng máy tính của trẻ trên Windows, có cấu hình từ xa và hoạt động khi mất kết nối”.

Mục tiêu nghiệm thu: phụ huynh đặt quy tắc trên web; agent nhận, lưu và thực thi trên máy Windows; trẻ thấy quy tắc và có thể xin ngoại lệ; báo cáo được tạo từ sự kiện thực tế.

## 2. Yêu cầu đọc được từ ảnh

| Nguồn | Nội dung | Cách triển khai trong đồ án |
|---|---|---|
| Ảnh 1–3 | Python agent, Windows Service LocalSystem, Tray UI riêng | Service thực thi và lưu dữ liệu; session helper/UI chạy quyền user |
| Ảnh 1–3 | FastAPI, SQLAlchemy, SQLite; HTTPS; heartbeat 60 giây | Giữ kiến trúc; SQLite WAL cho quy mô lab |
| Ảnh 1–3 | Chính sách, sự kiện, lệnh, báo cáo, audit | API có phân quyền sở hữu, phiên bản chính sách, hàng đợi bền vững |
| Ảnh 4–5 | Tổng quan thời gian, giải trí, yêu cầu; lịch tuần | Dashboard có bộ chọn trẻ/thiết bị, trạng thái đồng bộ |
| Ảnh 6 | Lọc theo miền/danh mục, SafeSearch; không giải mã HTTPS | DNS proxy có danh sách mẫu; SafeSearch là phần mở rộng cần kiểm thử riêng |
| Ảnh 7 | Xin thêm thời gian hoặc mở ứng dụng; phụ huynh duyệt | Request → quyết định → ngoại lệ tạm thời → agent xác nhận |
| Ảnh 8 | Nghỉ giới hạn 15 phút, bỏ giới hạn hôm nay, khóa ngay | Định nghĩa rõ từng lệnh ở mục 5; không thực thi lệnh shell tùy ý |
| Ảnh 9 | Hồ sơ tuổi 6–8, 9–11, 12–14; ghi nhận đã giải thích | Template chính sách có preview; phụ huynh xác nhận trước khi áp dụng |

Các mức thời gian theo tuổi trong ảnh chỉ là cấu hình mẫu sản phẩm, không phải khuyến nghị y tế. Ảnh là prototype, không phải bằng chứng các tính năng bên trong đã hoạt động.

## 3. Phạm vi

### Bắt buộc: bản MVP hoàn chỉnh

1. Đăng nhập/đăng xuất phụ huynh; quản lý hồ sơ trẻ và ghép thiết bị bằng mã dùng một lần.
2. Lịch dùng máy theo thứ/ngày, tổng thời gian mỗi ngày; giới hạn riêng nhóm ứng dụng học tập/giải trí/game/khác.
3. Theo dõi ứng dụng foreground và trạng thái phiên; không cộng tất cả ứng dụng chạy nền thành thời gian dùng máy.
4. Chặn một số executable do phụ huynh cấu hình trong phiên trẻ; hiển thị lý do cho trẻ.
5. Tray UI: thời gian còn lại, lịch, lý do bị hạn chế, xin thêm giờ/xin mở app, trang “Phần mềm này làm gì?”.
6. Duyệt/từ chối yêu cầu và áp dụng ngoại lệ có thời hạn.
7. Lệnh khóa phiên, miễn giới hạn thời gian 15 phút, miễn giới hạn đến hết hôm nay; có trạng thái và thời hạn lệnh.
8. Cache chính sách, bộ đếm và outbox SQLite; mất mạng vẫn thực thi; kết nối lại không gửi trùng.
9. Báo cáo ngày/tuần, tổng theo ứng dụng/nhóm, số lần chặn, nhật ký thay đổi.
10. DNS proxy chặn theo miền; dữ liệu danh mục mẫu có ghi rõ nguồn và phạm vi; cài/gỡ có khôi phục DNS.

### Có sau khi luồng chính đã ổn định

- WebSocket để đánh thức agent nhận lệnh nhanh; polling dự phòng.
- SafeSearch và YouTube Restricted Mode trên môi trường trình duyệt đã kiểm thử.
- Mẫu chính sách độ tuổi, 2FA phụ huynh, xuất CSV, bộ cài thuận tiện.

### Ngoài phạm vi bản đầu

- Chụp màn hình, webcam, keylogger, đọc tin nhắn, giám sát bí mật.
- Điều khiển desktop, shell từ xa, thực thi mã tải từ server.
- Driver/kernel, chống vượt quyền administrator, chặn tuyệt đối VPN/DoH, phân loại web bằng AI.
- Windows/macOS/Linux đồng thời; đồng bộ quota chung nhiều máy khi offline.

## 4. Kiến trúc đề xuất

### Công nghệ

| Thành phần | Lựa chọn | Vai trò |
|---|---|---|
| Backend | Python + FastAPI + SQLAlchemy + Alembic | API, nghiệp vụ, DB migration |
| Server DB | SQLite WAL, 1 backend worker cho lab | Giảm công vận hành; chuyển PostgreSQL nếu mở rộng |
| Dashboard | React + TypeScript + Vite | UI nhiều màn hình tương tự demo; giao diện tiếng Việt |
| UI styling | CSS hoặc Tailwind | Sidebar, card, biểu đồ; không cần bộ component quá lớn |
| Agent core | Python, SQLite, HTTP client | Policy engine, counter, sync, outbox |
| Windows adapter | pywin32, psutil | Service, session, IPC, process |
| Tray/session helper | PySide6 | UI, foreground/idle/session signals trong phiên user |
| DNS | dnslib hoặc thư viện phù hợp đã xác minh | DNS UDP/TCP localhost, forwarding, cache |
| Test | pytest; frontend test runner; Playwright | Unit, integration, E2E web |
| Đóng gói | PyInstaller + script cài/gỡ | Chỉ build và nghiệm thu Windows trên Windows |
| Lab deploy | Docker Compose backend/proxy; agent native | HTTPS tại reverse proxy; agent xác minh certificate |

Đây là quyết định thiết kế đề xuất. Coding agent phải kiểm tra tương thích và pin phiên bản tại thời điểm triển khai, không tự lấy “latest” không kiểm chứng. Jinja2 + HTMX là phương án giảm phạm vi nếu người làm chưa quen React; chọn một hướng ngay từ đầu.

### Phân chia tiến trình

- **Service**: giữ token thiết bị, chính sách, bộ đếm, DNS, process enforcement, sync và command executor. Service không tự vẽ giao diện lên desktop.
- **Session helper/Tray**: chạy trong phiên của trẻ, đọc foreground/idle và nhận thông báo phiên; hiển thị trạng thái; gửi request qua IPC. Service kiểm tra SID/session và độ mới của dữ liệu; không tin tùy ý dữ liệu UI gửi lên.
- **IPC**: ưu tiên named pipe có ACL giới hạn service và SID được quản lý; endpoint chỉ gồm status, session signals, request và notification acknowledgements. Không cung cấp stop-service, arbitrary path execution, command shell hay sửa chính sách từ Tray.
- **Server**: là nơi xác thực phụ huynh, phát hành chính sách và ngoại lệ, tiếp nhận event, tổng hợp báo cáo.
- **Dashboard**: chỉ nói chuyện với server; không cần mở cổng truy cập từ Internet vào máy trẻ. Agent luôn chủ động kết nối ra server.

Windows Service chạy ở Session 0 nên phải tách helper theo phiên. GetLastInputInfo chỉ cho biết hoạt động trong phiên gọi hàm. LockWorkStation yêu cầu interactive desktop; lệnh khóa phải chuyển đến helper đúng phiên và kiểm tra kết quả thông qua trạng thái session.

### Cây thư mục mục tiêu

```text
ogk/
  server/                 # API, auth, models, services, migrations
  dashboard/              # React TypeScript
  agent/
    core/                 # policy, counter, sync; không import Windows API
    windows/              # service, session helper, named pipe, process
    tray/                 # PySide6
    dns/                  # resolver và rules
  contracts/              # policy/event/command schema, fixture dùng chung
  tests/                  # unit/integration, Windows manual checklist
  scripts/                # bootstrap, seed, install, uninstall, backup
  deploy/                 # compose, reverse proxy, env example
  docs/                   # SRS, ERD, ADR, API, test evidence, demo
```
### Cơ chế chống tắt Helper & Dự phòng tại Service :
  1. Nếu phiên của trẻ đang active (`WTSActive`) nhưng tiến trình Tray/Helper không chạy hoặc mất kết nối IPC quá 10 giây, Service tự động khởi chạy lại Tray/Helper trong session của trẻ (`WTSQueryUserToken` + `CreateProcessAsUser`) hoặc qua Scheduled Task khi logon.
  2. Khi mất kết nối với Helper nhưng session của trẻ vẫn `WTSActive`, Service chuyển sang chế độ `degraded_active`: vẫn tiếp tục đếm tổng thời gian dùng máy (Screen-time Counter) và dùng `psutil` quét tiến trình theo SID trẻ để chặn các ứng dụng bị cấm.
  3. Để khóa máy từ xa hoặc khi hết giờ, Service ưu tiên gửi lệnh cho Helper gọi `LockWorkStation()`, đồng thời có fallback gọi trực tiếp `win32ts.WTSDisconnectSession` từ Session 0 nếu Helper không phản hồi sau 2 giây.

## 5. Chốt quy tắc nghiệp vụ trước khi viết code

| Vấn đề | Quyết định cho bản đầu |
|---|---|
| Thời gian dùng máy | Chỉ cộng khi đúng SID trẻ, session active, không khóa/sleep, idle dưới ngưỡng mặc định 5 phút; ngưỡng chỉnh được |
| Khoảng lấy mẫu | 1 giây để đo và đánh giá; checkpoint DB khoảng 5 giây; thời gian chạy dùng monotonic, không lấy hiệu đồng hồ lịch |
| App usage | Khoảng đo gán cho foreground executable; một thời điểm tối đa một app; thời gian app là tập con thời gian máy |
| Video/học không nhập liệu | Idle có thể làm thiếu số liệu; ghi rõ hạn chế; cho cấu hình ngưỡng, chưa tự nhận diện media |
| Timezone | Lưu UTC; chia ngày/lịch theo timezone thiết bị do phụ huynh đặt, mặc định Asia/Ho_Chi_Minh |
| Lịch | Khoảng [start,end); UI bản đầu không cho khung qua nửa đêm, yêu cầu tách 2 khung; kiểm tra trùng |
| Hạn mức | Tổng máy/ngày + nhóm app/ngày; quota nhóm cộng từ foreground app, không cộng các tiến trình nền |
| Ưu tiên | Khóa thủ công đang hiệu lực → chặn app/miền tường minh → điều kiện thời gian sau khi xét ngoại lệ hợp lệ → cho phép |
| Ngoại lệ thời gian | Chỉ thay đổi scope được duyệt; không gỡ chặn nội dung hoặc app tường minh |
| Xin mở app | Cho phép đúng app_id đến expires_at; có thể vượt riêng app block được chỉ định, không vượt khóa thủ công hoặc quota tổng |
| Xin thêm giờ | Tăng quota tổng cho ngày địa phương và thiết bị xác định; không tự mở lịch ngoài giờ; muốn nới lịch phải duyệt scope riêng |
| Miễn 15 phút | Bỏ kiểm tra lịch/quota thời gian trong 15 phút từ lúc agent áp dụng; lệnh phải được nhận trước expires_at; không bỏ content/app block |
| Miễn hôm nay | Bỏ lịch/quota đến nửa đêm timezone cấu hình; ghi rõ đây là miễn giới hạn, không buộc trẻ nghỉ |
| Khóa ngay | Ghi trạng thái manual_lock bền vững và yêu cầu khóa phiên; khi login/unlock lại vẫn kiểm tra manual_lock; phụ huynh có lệnh hủy khóa được audit |
| Hết quota | Cảnh báo trước 5 phút/1 phút; khóa phiên khi hết; thông báo lại khi unlock; đây không phải lớp bảo vệ như kiosk/driver |
| Quy tắc thay đổi | Snapshot bất biến có version tăng; agent áp dụng nguyên tử, giữ bản trước nếu snapshot sai |
| Online | Heartbeat 60 giây; quá 180 giây chưa nhận thì “mất liên lạc”, không suy ra máy đã tắt |
| Polling | Poll command khoảng 5 giây có jitter; policy check theo heartbeat; WebSocket chỉ tăng tốc |
| Offline | Giữ policy gần nhất, counter và ngoại lệ còn hạn; queue request/event; không tự duyệt yêu cầu |
| Đồng hồ đổi | Phát hiện sai lệch wall-clock so với monotonic trong một lần chạy; không reset quota; lưu high-water local date và báo clock_suspect; không nhận có thể chống chỉnh giờ tuyệt đối qua reboot |
| Chưa có policy | Enrollment chưa hoàn tất thì hiển thị “chưa được quản lý”; không bật DNS hệ thống hoặc chặn máy |
| Thiếu helper | Service báo degraded, không giả usage=0 là đáng tin; giữ process/DNS rules, ghi khoảng telemetry thiếu; không khóa hàng loạt chỉ vì lỗi IPC |
| Duyệt đồng thời | Một request chỉ chuyển pending → approved/rejected/expired đúng một lần bằng transaction |

Trong code, policy engine trả Decision(allowed, reason_code, rule_id, remaining_seconds, next_transition_at). Lý do hiển thị dùng mã ổn định như OUTSIDE_SCHEDULE, DAILY_QUOTA_EXCEEDED, APP_BLOCKED, MANUAL_LOCK, DOMAIN_BLOCKED. Tránh mỗi màn hình tính “còn lại” theo một cách khác nhau.

## 6. Dữ liệu và hợp đồng API

### Các bảng chính

| Bảng | Trường/quan hệ chính |
|---|---|
| users | id, email unique, password_hash, created_at |
| children | id, owner_id, display_name, age_band, timezone |
| devices | id, child_id, windows_sid, name, token_hash, last_seen, applied_policy_version, revoked_at |
| enrollment_codes | owner_id, code_hash, expires_at, consumed_at; dùng một lần, giới hạn thử |
| policies | id, child_id/device_id, version, document_json, created_by, created_at; snapshot |
| app_catalog | id, owner_id, display_name, normalized_exe_path/name, category |
| usage_intervals | event_id unique, device_id, start/end UTC, app_id, active_seconds, sequence, boot_id |
| device_events | event_id unique, device_id, type, observed_at, reason_code, rule_id; dữ liệu tối thiểu |
| requests | id, device_id, type, payload, reason, status, decided_by, expires_at |
| grants | id, request_id unique nếu có, device_id, scope, valid_from/until, amount_seconds, local_date |
| commands | id, device_id, type, payload, expires_at, status, dedup_key, result |
| audit_logs | actor, action, resource, before/after đã lọc bí mật, timestamp |
| transparency_records | child_id, explanation_version, acknowledged_at; không gọi đây là chứng nhận pháp lý |

Local agent DB: policy_cache, usage_checkpoints, outbox_events, pending_requests, executed_commands, active_grants, dns_original_settings. Thư mục DB/token được ACL cho service/admin; không để token device trong thư mục user hoặc dashboard.

### API dự kiến, tất cả dưới /api/v1

| Nhóm | Endpoint gợi ý |
|---|---|
| Parent auth | POST /auth/login, POST /auth/logout, GET /auth/me |
| Hồ sơ | GET/POST /children, PATCH /children/{id} |
| Pairing | POST /enrollment-codes; POST /agent/enroll |
| Thiết bị | GET /devices, POST /devices/{id}/revoke |
| Chính sách | GET/PUT /devices/{id}/policy; GET /agent/policy?version=... |
| Agent sync | POST /agent/heartbeat, POST /agent/events/batch |
| Yêu cầu | POST /agent/requests, GET /requests, POST /requests/{id}/decision |
| Lệnh | POST /devices/{id}/commands, GET /agent/commands, POST /agent/commands/{id}/ack |
| Báo cáo | GET /reports/daily, GET /reports/weekly; filter child/device/date |
| Audit | GET /audit; phân trang và filter |

Phụ huynh dùng session cookie HttpOnly, Secure khi HTTPS, SameSite và CSRF protection; phát triển dùng proxy cùng origin. Agent dùng bearer token riêng từng thiết bị, chỉ truy cập tài nguyên của thiết bị đó. Không cho agent chọn device_id của gia đình khác bằng payload. Rate-limit login/enroll; giới hạn batch/event size; API trả validation error nhất quán. Không dùng JWT nếu chưa có nhu cầu rõ ràng.

Event envelope: schema_version, event_id(UUID), device_id do server gắn theo token, boot_id, sequence, observed_at UTC, type, payload. Server ACK danh sách event_id sau commit; dedup bởi device_id/event_id. Outbox retry exponential backoff+jitter và batch nhỏ. Báo cáo tổng hợp từ interval đã dedup, chia interval qua nửa đêm. Không cộng chồng tổng máy và app thành hai lần usage.

Command lifecycle: queued → delivered → executed/failed/expired. delivered không có nghĩa đã chạy. Mỗi command có id, expires_at, loại allowlist và kết quả ACK. Service lưu intent/result để xử lý replay và crash; các hiệu ứng thiết kế idempotent: set trạng thái hoặc upsert grant theo command_id. Không hứa “exactly once” cho mọi tác động ngoài DB. Dashboard phân biệt policy server version và applied version.

## 7. Lọc web: phạm vi thực tế

- Chặn theo domain; chuẩn hóa lowercase, bỏ dấu chấm cuối, xử lý IDNA; rule example.com khớp example.com và subdomain hợp lệ, không khớp badexample.com.
- Category là tập domain được quản lý thủ công/import có nguồn và ngày cập nhật. Demo dùng domain thử nghiệm an toàn; không mở website độc hại để chứng minh.
- Chế độ allowlist hoặc blocklist; ngoại lệ domain tường minh ưu tiên category, nhưng hard-block do phụ huynh đặt vẫn thắng allow ngoại lệ thông thường. Viết truth table riêng trước khi code.
- Nhãn “Hạn chế” phải nghĩa là chỉ mở trong lịch web cấu hình, không tuyên bố đo quota thời gian duyệt miền bằng DNS. DNS lookup không đo được thời gian ở trên một trang.
- DNS proxy listen 127.0.0.1:53, và ::1 nếu có cấu hình IPv6; UDP + TCP; có upstream timeout/cache, tránh trỏ upstream về chính mình. Chỉ quản lý adapter được chọn; kiểm tra xung đột port 53.
- Lưu trạng thái DNS gốc của từng adapter, gồm DHCP/static và IPv4/IPv6; bật proxy khỏe mạnh rồi mới đổi DNS; khi lỗi cấu hình phải rollback; gỡ cài đặt phải khôi phục.
- DNS chỉ thấy miền, không thấy đường dẫn HTTPS. Không cài CA để giải mã HTTPS. Trình duyệt thường có thể chỉ hiện lỗi DNS, không bảo đảm redirect thành trang “bị chặn” có giải thích; Tray cung cấp thông báo lý do theo sự kiện chặn gần nhất.
- Không lưu query log toàn bộ; báo cáo chỉ giữ tổng số lần chặn theo category/rule. Unknown domain không đưa vào lịch sử duyệt web.
- DoH, VPN, cache DNS và kết nối đã mở có thể làm quy tắc không có tác dụng ngay. Demo ghi rõ cấu hình trình duyệt và làm sạch cache có kiểm soát. Không tuyên bố chặn tuyệt đối.
- SafeSearch/YouTube phải có adapter riêng và test trên môi trường hỗ trợ; không tạo công tắc UI báo “đã bật” khi chỉ lưu boolean.

## 8. Màn hình và luồng sử dụng

### Dashboard phụ huynh

1. Login và thiết lập gia đình.
2. Hồ sơ trẻ, chọn thiết bị, tạo mã ghép, trạng thái kết nối/đồng bộ.
3. Tổng quan: dùng hôm nay/tổng quota, giải trí còn lại, request chờ, biểu đồ tuần, lịch hôm nay.
4. Ứng dụng & Khung giờ: rule theo nhóm/app, lịch tuần, quota, cảnh báo xung đột, preview chính sách.
5. Lọc web: category, danh sách miền, chế độ, thời khóa biểu cho “Hạn chế”; giải thích giới hạn DNS.
6. Báo cáo: chọn ngày/tuần và thiết bị; trạng thái dữ liệu chưa đồng bộ/thiếu telemetry.
7. Yêu cầu: lý do, thời lượng/app, trạng thái; approve có scope/expiry rõ ràng.
8. Điều khiển: miễn 15 phút, miễn hôm nay, khóa/hủy khóa; hiển thị queued/delivered/executed/failed/expired.
9. Hồ sơ & Độ tuổi: 3 template như ảnh; xem trước thay đổi; giải thích cho trẻ; lưu phiên bản bản giải thích.

Phong cách demo: nền sáng, sidebar trái, xanh lá nhạt, card bo góc, chữ tiếng Việt dễ đọc. Dashboard responsive. Loading/empty/error/offline/degraded đều có UI; không hard-code số thống kê của Bé An vào production. Có thể seed Bé An, 11 tuổi, PC-Phong-hoc để demo.

### Máy trẻ

Tray hiển thị rõ phần mềm đang hoạt động, số phút còn lại, lịch, trạng thái server, lý do hạn chế, nút xin thêm giờ/xin mở app và trạng thái gửi/chờ/được duyệt. Chế độ offline vẫn cho tạo request trong queue nhưng ghi “chưa gửi”. Đóng cửa sổ Tray không đồng nghĩa tắt service. Màn hình minh bạch mô tả dữ liệu được thu thập và không thu thập.

## 9. Lịch thực hiện 5 tuần

| Tuần | Ngày | TV1 | TV2 | TV3 | Mốc nghiệm thu cuối tuần |
|---|---|---|---|---|---|
| 1 | 26/10–01/11 | A01–A02; bắt đầu A03 | B01–B02 | C01–C02 | SRS/ERD/contracts, spike SID/session/IPC/DNS, core và UI shell; auth đang triển khai |
| 2 | 02/11–08/11 | Hoàn tất A03; A04–A05; bắt đầu A06 | B03–B04; bắt đầu B05 | C03; bắt đầu C04 | Ghép thiết bị và policy thật; simulator/counter pass; bắt đầu tích hợp service |
| 3 | 09/11–15/11 | Hoàn tất A06; A07–A08 | Hoàn tất B05; B06–B07 | Hoàn tất C04; C05 | Service/Tray thật; offline/reconnect, request/grant và command qua API/agent; UI quản trị hoàn tất đầu tuần 4 |
| 4 | 16/11–22/11 | A09–A10 | B08; chuẩn bị B09 | C06–C07 | Luồng UI → API → agent hoàn chỉnh; báo cáo thật; DNS proxy pass, adapter chuẩn bị tích hợp |
| 5 | 23/11–29/11 | A11–A12 | Hoàn tất B09; B10 | C08–C10 | 25/11: DNS tích hợp; 28/11: chốt release candidate và test VM; 29/11: nghiệm thu, demo, bàn giao |

Tổng kế hoạch **136 giờ/người**, **408 giờ toàn nhóm**, gồm review và dự phòng; trung bình
27,2 giờ/người/tuần. Chi tiết 32 đầu việc, ngày bắt đầu/hạn hoàn thành và phụ thuộc xem PHAN_CONG.md.
Ngày 28/11 chốt release candidate, 29/11 nghiệm thu/demo/bàn giao. Không thêm tính năng mới tuần 5.
Giữ MVP, dùng domain list thủ công; WebSocket/SafeSearch/2FA/CSV/template tuổi/installer đẹp sau deadline.
Nếu nhóm chỉ có 15–20 giờ/người/tuần, phải thống nhất giảm phạm vi vì 5 tuần chỉ có 225–300 giờ nhóm.

## 10. Kiểm thử và định nghĩa hoàn thành

| Ca | Thao tác | Kỳ vọng |
|---|---|---|
| T01 | Dùng token phụ huynh A lấy device B | Không trả dữ liệu; không sửa được |
| T02 | Dùng lại enrollment code hoặc code hết hạn | Bị từ chối; không tạo thiết bị mới |
| T03 | Fake clock chạy 90 giây foreground, 30 giây locked | Tổng máy/app bằng 90 giây |
| T04 | 2 app đổi foreground, app nền vẫn chạy | Tổng app không lớn hơn tổng máy; không cộng app nền |
| T05 | Chạm đầu/cuối lịch; interval qua nửa đêm | Áp dụng đúng [start,end); tách số liệu đúng ngày |
| T06 | Sleep 30 phút rồi wake | Không cộng 30 phút sleep; không bù thời gian mù |
| T07 | Restart agent khi đã dùng quota | Khôi phục bộ đếm; sai lệch crash đo được, mục tiêu không quá checkpoint 5 giây trong ca đã thử |
| T08 | Mất mạng 10 phút rồi reconnect, gửi lại batch | Policy vẫn dùng; mỗi event xuất hiện một lần; báo cáo không tăng gấp đôi |
| T09 | Hai thao tác approve đồng thời/retry ACK | Một grant duy nhất, không cộng thời gian hai lần |
| T10 | Lệnh khóa hết hạn mới tới agent | expired, không khóa muộn |
| T11 | Lệnh miễn 15 phút nhận lại sau crash | Cùng grant_id/expires_at; không kéo dài thêm 15 phút |
| T12 | Tài khoản admin phụ huynh mở app bị chặn của trẻ | Không bị agent áp dụng nhầm |
| T13 | Rule example.test, sub.example.test, badexample.test | Chỉ hai miền đầu khớp |
| T14 | Upstream DNS timeout, port 53 bận, đổi adapter | Báo lỗi rõ, không đổi DNS khi proxy chưa sẵn sàng; rollback có kiểm chứng |
| T15 | Gỡ phần mềm sau khi DNS từng là DHCP/static | Khôi phục đúng cấu hình gốc IPv4/IPv6 đã quản lý |
| T16 | Tray chết, IPC message sai SID hoặc payload | Service báo degraded; không thực thi lệnh trái phép |
| T17 | Chỉnh giờ lùi và đổi ngày | Không reset quota để được dùng lại; báo clock_suspect; ghi giới hạn qua reboot |
| T18 | Khóa ngay rồi unlock/login lại | Manual lock vẫn hiệu lực cho đến khi phụ huynh hủy |

Mục tiêu demo khi lab khỏe: policy mới applied trong 70 giây; command polling được tiếp nhận trong 10 giây; process mẫu bị xử lý trong 3 giây. Đây là mục tiêu cần đo, không phải bảo đảm thời gian thực. Process polling có thể để app khởi chạy ngắn trước khi đóng; không quảng cáo như OS launch prevention. Chỉ thử chặn executable dành riêng cho demo, không thử kết thúc phần mềm có dữ liệu chưa lưu.

Hoàn thành khi: API và UI dùng dữ liệu thật; unit/integration pass; manual Windows checklist có bằng chứng; cài/gỡ được; không có secret trong repo; README có lệnh chạy và giới hạn; các mục chưa hỗ trợ được ghi đúng thực trạng. Mock Windows trên Linux chỉ kiểm tra logic, không chứng minh API Windows hoạt động.

## 11. Tài liệu nộp và kịch bản bảo vệ

Tài liệu: SRS/use case; architecture và ADR; ERD/data dictionary; API; policy truth table; test plan/report; hướng dẫn cài/gỡ và vận hành; hạn chế; hướng phát triển. README dẫn đến từng tài liệu. Báo cáo phân biệt rõ phần đã triển khai, đã test thực tế và chỉ mới đề xuất.

Demo 8–10 phút:
1. Giới thiệu vấn đề, nguyên tắc minh bạch và kiến trúc 3 phần.
2. Ghép Windows device bằng mã một lần; mở Tray.
3. Phụ huynh đặt hạn mức demo 2 phút và chặn app thử nghiệm; chỉ ra version applied.
4. Mở app, hiện lý do; thời gian máy/app đi lên từ hoạt động thật.
5. Trẻ xin thêm 1 phút; phụ huynh duyệt; số phút cập nhật một lần.
6. Dừng kết nối mạng, chứng minh rule vẫn tồn tại; kết nối lại và xem outbox đồng bộ.
7. Chặn domain thử nghiệm, xem lý do trên Tray; nêu giới hạn DoH/HTTPS.
8. Khóa phiên bằng lệnh từ dashboard, chỉ ra ACK executed sau xác nhận session; hủy khóa bằng tài khoản phụ huynh.
9. Xem báo cáo và audit; kết thúc bằng bằng chứng cài/gỡ và giới hạn đã biết.

## 12. Cách dùng bộ prompt

Tạo repository trên máy phát triển và chép file này thành docs/PROJECT_BRIEF.md. Đính kèm 9 ảnh hoặc đặt trong docs/reference nếu coding agent đọc được ảnh. Đưa Prompt 0 trước, sau đó từng Prompt 1–10. Mỗi lượt chỉ giao một milestone; xem diff, test và demo rồi mới chuyển bước. Không yêu cầu agent sinh toàn bộ hệ thống trong một lượt.

Nếu agent đã có repo, bắt buộc khảo sát trước và giữ phần đang hoạt động. Prompt 0 là ngữ cảnh dùng xuyên suốt; khi mở phiên agent mới, gửi lại Prompt 0 và milestone hiện tại. Các prompt yêu cầu tạo file thật; không cần dùng writing block hoặc sinh code trong chat.

### Prompt 0 — Ngữ cảnh và quy tắc làm việc chung

```text
Bạn là coding agent triển khai đồ án Người Bạn Đồng Hành/OGK. Đọc docs/PROJECT_BRIEF.md và các ảnh tham chiếu nếu có. Mục tiêu là hệ thống thật gồm FastAPI server, React TypeScript dashboard, Python Windows Service, session helper/Tray và DNS proxy. Làm đúng milestone tôi giao; hoàn thành code, kiểm tra và tài liệu cho milestone đó.

Trước khi sửa, khảo sát repository, AGENTS.md, môi trường và phần đã có. Không ghi đè code người dùng hoặc khởi tạo lại repo đã tồn tại. Nếu repo trống, dựng theo cấu trúc brief. Nêu giả định cần thiết; chỉ hỏi khi thiếu thông tin làm thay đổi kiến trúc hoặc không thể tiếp tục đúng yêu cầu.

Các ràng buộc bắt buộc:
- Policy engine/counter là Python thuần, có fake clock, không phụ thuộc Windows.
- Service và helper chạy khác session; không gọi API interactive như đang chạy trong user session từ LocalSystem.
- Parent session và device token tách biệt; kiểm tra ownership từng tài nguyên.
- HTTPS môi trường tích hợp, không tắt certificate verification; secret lấy từ môi trường/kho bảo vệ, không hard-code.
- Offline cache/outbox bền vững, dedup event, policy version, expiry lệnh, grant idempotent.
- Chỉ thu thập dữ liệu tối thiểu trong brief; không screenshot/keylogger/full URL, không shell từ xa.
- Luôn có simulator/dry-run mặc định cho phần ảnh hưởng OS. Script đổi DNS/cài service/chặn app phải có preflight, rollback và tài liệu; không tự chạy lên máy phát triển ngoài Windows VM lab đã được chỉ định.
- Không tuyên bố test Windows pass nếu chỉ chạy mock hoặc đang ở Linux.
- Không làm UI “thành công” khi backend chưa ACK; dữ liệu seed chỉ nằm trong chế độ demo.
- Kiểm tra tài liệu chính thức cho API/thư viện chưa rõ; pin phiên bản tương thích; không giả lập API mình chưa xác minh.

Mỗi milestone cập nhật docs/PROGRESS.md: phần đã làm, phần chưa làm, file đổi, lệnh kiểm tra, kết quả thực, giới hạn và bước tiếp. Cuối lượt báo ngắn gọn những nội dung trên. Nếu lỗi, sửa trong phạm vi milestone; không che bằng mock hoặc bỏ assertion. Không tiếp tục milestone kế tiếp khi chưa báo kết quả hiện tại.
- Tên dự án thống nhất là "OpenGuard Kids (OGK)" (gồm OGK-Server, OGK-Agent Service, OGK-Agent Tray UI, Dashboard phụ huynh).
- Với SQLite trên OGK-Server và OGK-Agent, luôn bật `PRAGMA journal_mode=WAL;` và `PRAGMA busy_timeout=5000;` ngay khi mở kết nối để tránh lỗi khóa DB khi đọc/ghi đồng thời.
- IPC giữa Tray UI và Service có thể dùng Named Pipe (có ACL) hoặc HTTP 127.0.0.1 kèm Local Bearer Token (lưu ở file có ACL chỉ cho SYSTEM và SID trẻ đọc), miễn là vượt qua bài kiểm thử bảo mật và không bị treo luồng (deadlock).
```

### Prompt 1 — Đặc tả và thử nghiệm kỹ thuật rủi ro

```text
Áp dụng Prompt 0. Thực hiện milestone 1, chưa xây toàn bộ sản phẩm.
1. Viết docs/SRS.md: actors, use cases, MVP/extension, FR/NFR có ID và acceptance criteria. Truy vết với 9 ảnh; đánh dấu chi tiết ảnh không đọc rõ.
2. Viết docs/ARCHITECTURE.md, docs/ERD.md, docs/POLICY_RULES.md và ADR về service/helper, quota theo thiết bị, auth, offline, DNS.
3. Chốt truth table cho lịch/quota/app block/manual lock/grant và web allowlist/blocklist/category, interval [start,end), day boundary.
4. Tạo spike tối thiểu trong scripts/spikes để chạy thủ công trên Windows VM: đọc SID/session, foreground/idle ở helper; trao đổi named pipe ACL; khóa phiên và xác nhận WTS state; kiểm tra/sao lưu/khôi phục DNS một adapter. Mặc định dry-run, không cài hoặc đổi mạng tự động. Trong `scripts/spikes`, kiểm tra thêm khả năng khóa phiên trực tiếp từ Service (Session 0) bằng `win32ts.WTSDisconnectSession` và khả năng kiểm tra trạng thái phiên (`WTSActive`, `WTSDisconnected`) qua `WTSEnumerateSessions` để làm phương án dự phòng khi Tray UI bị tắt..
5. Viết checklist chứng minh Session 0 không bị nhầm với user session. Nếu không có Windows, chỉ tạo script và ghi “chưa test Windows”.
Đầu ra là tài liệu cụ thể và mã spike có thể kiểm tra. Ghi các quyết định đề xuất so với yêu cầu từ ảnh; nêu điểm chưa chứng minh được. Không dựng dashboard đẹp để thay thế spike.
```

### Prompt 2 — Repo, backend, auth và pairing

```text
Áp dụng Prompt 0 và docs/PROJECT_BRIEF.md. Dựng nền tảng server/contracts/dashboard shell/agent core, lint và test commands, CI phù hợp. Dùng FastAPI, SQLAlchemy, Alembic, SQLite WAL cho lab; chọn và pin dependency tương thích.
Triển khai parent login/logout/me bằng server session cookie với CSRF; hash mật khẩu bằng thư viện chuẩn phù hợp; seed tài khoản demo chỉ qua lệnh riêng, mật khẩu lấy từ env hoặc tạo khi seed. Xây CRUD children, tạo enrollment code ngắn hạn một lần, agent enroll, device token riêng và revoke. Ownership scope bắt buộc.
Tạo policy snapshot versioned và GET/PUT policy với optimistic concurrency; GET agent policy không cho token thiết bị khác đọc chéo. Sinh OpenAPI và fixture schema trong contracts.
Nghiệm thu: migration từ DB trống; duplicate enrollment không thành công; code hết hạn không dùng được; device revoke mất quyền; hai gia đình không truy cập chéo; cookie/CSRF và input validation có test. Chạy test server và cập nhật README/PROGRESS. Chưa làm Windows enforcement.
```

### Prompt 3 — Policy engine, counter và simulator

```text
Áp dụng Prompt 0. Triển khai agent/core thuần Python theo POLICY_RULES: typed policy, Decision và reason_code; schedule theo timezone; tổng quota và category quota; app rule; manual lock; scoped grant/expiry; precedence đúng truth table.
Xây clock abstraction wall-clock/monotonic; usage interval foreground; session active/lock/sleep/idle; tách interval qua nửa đêm; SQLite checkpoint bền vững. Với gap sau sleep/không có telemetry, không cộng toàn bộ khoảng mù. Theo dõi clock_suspect và high-water ngày, không reset quota khi chỉnh giờ lùi.
Tạo CLI simulator dùng fixture để phát foreground/session/time events và in quyết định/time remaining; không gọi Windows API.
Test có fake clock cho biên lịch, overlapping/invalid schedule, midnight, category limit, grant hết hạn, manual lock, restart counter, sleep, idle và đổi giờ. Kiểm tra một thời điểm chỉ thuộc một foreground app. Chạy toàn bộ test core; ghi rõ định nghĩa idle và sai số checkpoint. Không dùng sleep thật để test thời gian.
```

### Prompt 4 — Windows Service, helper và Tray thực tế

```text
Áp dụng Prompt 0. Dùng core đã có, triển khai adapter pywin32/psutil và Tray PySide6. Service chạy LocalSystem; helper/Tray chạy trong session SID trẻ. Named pipe ACL và validation session; không có generic shell/execute endpoint. Tạo service lifecycle start/stop/recovery và helper startup có tài liệu.
Helper lấy foreground executable, idle và session notifications; service xác thực/bounds-check telemetry, tính thời gian và lưu. Service áp dụng app rules chỉ trong SID/session được quản lý. Không kết thúc process hệ thống hoặc tài khoản khác. Thêm executable test vô hại, dry-run mặc định, cảnh báo trước khi thực thi thật.
Tray hiển thị usage, remaining, schedule, online/degraded, reason; cảnh báo 5 phút/1 phút và trang minh bạch. Lệnh khóa gửi đến helper interactive, xác nhận session locked trước ACK executed. Manual lock bền vững qua unlock/restart, hỗ trợ clear từ command hợp lệ. Không coi overlay là cơ chế bảo vệ OS.
Tạo script cài/gỡ preflight và quyền admin khi cần, không tự chạy trên host. Test logic bằng mock ở mọi OS; manual integration checklist trên Windows cho foreground/idle/lock/sleep/Tray crash/restart và account phụ huynh. Báo chính xác các ca Windows đã hoặc chưa chạy.
- Xử lý trường hợp trẻ tắt Tray UI từ Task Manager:
  1. Service phát hiện mất heartbeat IPC trong khi session của SID trẻ vẫn `WTSActive` -> chuyển sang trạng thái `degraded` nhưng VẪN ĐẾM tổng thời gian dùng máy và VẪN CHẶN executable bị cấm qua `psutil` (lọc theo SID trẻ).
  2. Service có cơ chế tự khởi chạy lại Tray UI trong session của trẻ (có giới hạn tần suất restart để tránh fork bomb nếu lỗi).
  3. Khi cần khóa máy (hết giờ hoặc lệnh `LOCK_SESSION`), nếu gửi IPC cho Tray gọi `LockWorkStation()` không thành công trong 2 giây, Service gọi `win32ts.WTSDisconnectSession` trực tiếp từ Session 0.
```

### Prompt 5 — Sync bền vững, commands và requests

```text
Áp dụng Prompt 0. Hoàn thiện enrollment/config client, heartbeat 60 giây, policy atomic apply/cache, event outbox có UUID/boot_id/sequence, ACK sau DB commit, retry backoff+jitter, batch limits và dedup server.
Triển khai command allowlist: LOCK_SESSION, CLEAR_MANUAL_LOCK, TEMPORARY_TIME_EXEMPTION, EXEMPT_UNTIL_LOCAL_DAY_END. Poll 5 giây; queued/delivered/executed/failed/expired; không chạy command quá expires_at. Persist command intent/result, dùng grant id cố định theo command_id để retry/crash không kéo dài ngoại lệ. WebSocket nếu làm chỉ là notify, reconnect không làm mất command.
Triển khai request xin quota/app; request offline queued; parent approve/reject atomic một lần; grant scope/expiry theo brief, audit. Trẻ không được tự cấp grant. Phân biệt request được duyệt, policy/grant được nhận và được áp dụng.
Nghiệm thu tự động: duplicate event, lost ACK, retry batch, concurrent approvals, command expired, duplicate command, crash quanh apply/ACK, policy invalid giữ bản trước. Tạo bài manual mất mạng 10 phút/reconnect. Không tuyên bố exactly-once cho tác động ngoài DB.
```

### Prompt 6 — Dashboard theo ảnh và dữ liệu thật

```text
Áp dụng Prompt 0. Xây React TypeScript dashboard tiếng Việt theo bố cục ảnh: nền sáng/xanh lá nhạt, sidebar trái, card, biểu đồ tuần, responsive. Không cần sao chép các vùng mờ; ghi rõ giả định.
Màn hình: login; children/devices/pairing; tổng quan; ứng dụng & lịch tuần/quota; lọc web; báo cáo; requests; điều khiển; hồ sơ & độ tuổi. Có child/device selector. Mỗi thao tác gọi API thật; nếu API thiếu, triển khai backend tương ứng kèm ownership/validation/test.
Hiển thị loading/empty/error/offline/degraded, server version/applied version, last_seen và trạng thái command ACK. Form cảnh báo lịch trùng và reject khoảng qua nửa đêm theo brief. Approve request cho xem scope/expiry. Template tuổi preview thay đổi trước khi lưu. Không gắn nhãn “2FA đã bật” khi chưa triển khai.
Seed Bé An/PC-Phong-hoc qua chế độ demo tách biệt. Test UI ít nhất cho tạo rule, lỗi validation, approve, command queued đến executed và lỗi mạng. Báo cáo phải từ event đã dedup; chỉ dùng mock ở test/demo mode có nhãn. Chạy build và E2E luồng chính có evidence.
```

### Prompt 7 — DNS filtering và khôi phục cấu hình

```text
Áp dụng Prompt 0. Triển khai domain rule engine và DNS localhost proxy thật. Hỗ trợ UDP/TCP, A/AAAA/CNAME cần thiết, forwarding timeout, bounded cache, TTL và loop protection. Chuẩn hóa IDNA/lowercase/trailing dot, suffix boundary; chế độ allowlist/blocklist và category theo POLICY_RULES. “Hạn chế” = schedule, không suy ra web usage time từ DNS.
Quản lý adapter được chọn trên Windows: preflight port 53, backup DNS DHCP/static IPv4/IPv6, start và health-check proxy trước khi đổi; rollback nếu lỗi; stop/uninstall khôi phục đúng trạng thái. Mặc định dry-run, không tự đổi DNS host. Chỉ bind loopback, không tạo open resolver LAN.
Không TLS interception/full URL/query history. Sự kiện chỉ giữ rule/category/count cần báo cáo. Tray giải thích block; không hứa trình duyệt HTTPS có trang redirect tùy biến. Category fixture dùng domain test an toàn, ghi nguồn và độ bao phủ.
Unit test domain boundary/IDNA/priority/schedule; integration proxy bằng upstream giả; manual Windows cho TCP/UDP, IPv6, cache, upstream fail, adapter change, restore DHCP/static. Đưa DoH/VPN/cache/HTTPS limitations vào UI help và README. SafeSearch/YouTube tách feature flag, chỉ bật khi có adapter đã test.
- Trước khi trỏ DNS của adapter về `127.0.0.1`, phải lưu lại danh sách DNS server gốc (hoặc dùng upstream cố định như `1.1.1.1:53`, `8.8.8.8:53`) làm upstream cho DNS Proxy; tuyệt đối không để DNS Proxy tự forward gói tin lại vào `127.0.0.1:53` gây vòng lặp vô hạn.
- Sau khi áp dụng cấu hình DNS mới hoặc thay đổi rule chặn miền, gọi `ipconfig /flushdns` (khi không ở chế độ dry-run) để xóa cache DNS của Windows, đảm bảo trình duyệt áp dụng ngay quy tắc trong lúc demo.
```

### Prompt 8 — Báo cáo, audit và bảo vệ dữ liệu

```text
Áp dụng Prompt 0. Hoàn thiện daily/weekly reports từ usage intervals dedup, timezone và split midnight; tổng theo app/category; counts chặn; missing telemetry/offline delayed indicators. Tổng app không cộng lần nữa vào tổng máy. Audit parent actions và command/grant decision, lọc secret.
Thêm retention cấu hình (mặc định lab: usage/event 30 ngày, audit 90 ngày), cleanup có test và backup/restore DB được tài liệu hóa. DB/token local dùng ACL service/admin; secret không lộ log. Endpoint report/audit phân trang và ownership.
Rà soát CSRF, auth, enrollment brute force, batch size, IPC authorization, grant bounds, revoked token, CSV injection nếu có export. Test phải chứng minh các thuộc tính cụ thể, không chỉ snapshot. Không viết kết luận “an toàn tuyệt đối”. Báo phát hiện, sửa và những giới hạn còn lại.
```

### Prompt 9 — Đóng gói, tích hợp và nghiệm thu

```text
Áp dụng Prompt 0. Chuẩn bị lab end-to-end: server/dashboard qua HTTPS reverse proxy, cấu hình env example không secret; agent build trên Windows bằng PyInstaller; script admin install/uninstall có preflight, backup/rollback DNS, service/helper registration và removal.
Viết README từng lệnh setup/run/test/build; docs/DEPLOYMENT.md; docs/TEST_REPORT.md; docs/DEMO_SCRIPT.md. Chạy unit/integration/frontend build, E2E web phù hợp. Trên Windows VM sạch kiểm tra cài, enroll, login child, policy apply, app/time enforcement, request approve, offline/reconnect, remote lock/clear, restart, DNS filter và uninstall restore. Không có Windows thì đánh dấu blocked, cung cấp lệnh và checklist, không ghi pass giả.
Đo mục tiêu lab: policy <=70 giây, command tiếp nhận <=10 giây, xử lý app test <=3 giây; ghi cấu hình và kết quả thực, không sửa số liệu để đạt. Kiểm tra không còn mock trong luồng production. Tổng kết ma trận FR → implementation → test evidence; đánh dấu phần mở rộng chưa làm.
```

### Prompt 10 — Rà soát trước khi bảo vệ

```text
Áp dụng Prompt 0. Review repository hiện tại như người chấm đồ án, chưa thêm tính năng mới. Đọc SRS, POLICY_RULES, kiến trúc, PROGRESS và test report; tìm lỗi logic nghiêm trọng và khác biệt giữa tài liệu/UI/code.
Tập trung: Session 0/idle/lock, quota qua sleep/midnight/reboot/clock rollback, ownership, device token và IPC, duplicate grant/command/event, mất mạng, DNS restore, báo cáo cộng đôi, UI thông báo thành công sớm, hard-code/demo data. Với mỗi phát hiện nêu file, cách tái hiện, tác động và đề xuất sửa; ưu tiên blocker trước.
Sửa các lỗi trong phạm vi đã thống nhất, thêm regression test có ý nghĩa rồi chạy kiểm tra liên quan. Cập nhật tài liệu theo trạng thái cuối; không tự tuyên bố các ca Windows chưa chạy là pass. Chuẩn bị danh sách câu hỏi hội đồng có thể hỏi và câu trả lời dựa trên implementation thật, gồm giới hạn anti-tamper, DoH/VPN, idle video và nhiều thiết bị.
```

## 13. Nguồn kỹ thuật cần coding agent tham khảo

- Microsoft, Interactive Services: https://learn.microsoft.com/en-us/windows/win32/services/interactive-services
- Microsoft, GetLastInputInfo: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo
- Microsoft, LockWorkStation: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-lockworkstation
- Google, Lock SafeSearch for devices you manage: https://support.google.com/websearch/answer/186669?hl=en

Các nguồn trên làm rõ ranh giới session và SafeSearch; phần lịch trình, schema, scope và prompt là đề xuất thiết kế cho đồ án, không phải trích từ tài liệu nhà cung cấp.
