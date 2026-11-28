# Nội dung cốt lõi tuần 1 — Thành viên 2

OpenGuard Kids (OGK) · Tuần 1: **26/10–01/11/2026** · Soạn ngày 31/10/2026.

> Cập nhật 05/11/2026 theo [PDF đề bài chính thức](DoAn_UD_QL_SD_PC_TreEm.pdf): B01–B02 vẫn đúng hướng, nhưng telemetry tuyệt đối không lưu/xuất tiêu đề cửa sổ hoặc URL. Các nghĩa vụ TV2 ở tuần sau được nâng thành bắt buộc gồm nhận diện app bằng tên + SHA-256, cảnh báo 10/5/1 phút và grace 60 giây, policy integrity/TLS pinning, WebSocket cho lệnh khẩn <5 giây, SafeSearch DNS và phụ lục kỹ thuật M3–M6. Xem [ma trận truy vết](REQUIREMENTS_TRACEABILITY.md).

Tài liệu học và chuẩn bị cho **B01–B02**, dựa trên [phân công](PHAN_CONG.md), [kiến trúc](ARCHITECTURE.md), [brief](PROJECT_BRIEF.md) và [các quyết định cần chốt](DECISIONS.md). Checklist bên dưới là việc cần chuẩn bị, không xác nhận đã triển khai hoặc kiểm thử.

## 1. Mục tiêu và phạm vi của bạn

Bạn phụ trách phần logic và tích hợp Windows của agent: đánh giá chính sách, tính thời gian, service/helper, đồng bộ và cấu hình DNS. Tuần 1 tập trung chứng minh các cơ chế Windows và thiết kế nền tảng core.

| Mã | Lịch theo kế hoạch | Đầu ra cần chuẩn bị |
|---|---|---|
| B01 | 26–29/10 · 16 giờ | Spike SID/session, foreground/idle, IPC ACL, lock/disconnect, DNS backup; kết luận D03/D04 |
| B02 | 30/10–01/11 · 8 giờ | Core models, Decision, clock/fake clock; fixture và test; core import được mà không cần Windows |

**Spike** là đoạn chương trình nhỏ để kiểm chứng một giả thuyết kỹ thuật, ví dụ “helper trong phiên trẻ có đọc đúng idle không?”. Mỗi spike cần có cách chạy, kết quả mong đợi và kết quả thực tế.

**Mức cần đạt:** giải thích được cơ chế, làm được thử nghiệm nhỏ, chỉ ra giới hạn và có bằng chứng. Engine đầy đủ, bộ đếm bền vững, service hoàn chỉnh và bộ cài lần lượt thuộc các tuần sau.

## 2. Hiểu luồng hoạt động của OGK

```text
Phụ huynh đặt quy tắc trên Dashboard
                  |
                  v
              API Server
                  ^
                  | HTTPS do agent chủ động kết nối ra
                  v
        Windows Service / LocalSystem
          |                    |
          v                    | IPC có kiểm soát quyền
     Core + dữ liệu            v
                       Helper trong phiên trẻ
                         + Tray do TV3 làm
```

- **Server:** lưu và cung cấp chính sách, tiếp nhận sự kiện và lệnh.
- **Service:** giữ dữ liệu/token, điều phối đánh giá và thực thi trên Windows.
- **Helper:** thu thập foreground, idle và tín hiệu phiên tại phiên trẻ.
- **Tray:** giao diện hiển thị trạng thái và gửi yêu cầu của trẻ.
- **Core:** nhận dữ liệu đầu vào và trả quyết định; không gọi trực tiếp Windows API.

Service và helper tách nhau vì service chạy ở Session 0, còn tương tác desktop thuộc phiên người dùng. Đọc [Microsoft: Interactive Services](https://learn.microsoft.com/en-us/windows/win32/services/interactive-services).

Kiến thức mạng chung cần ôn: TCP là kết nối vận chuyển; HTTP là giao thức request/response; TLS bảo vệ kết nối HTTPS. Phân biệt API qua mạng với IPC nội bộ máy. Trong luồng OGK, Dashboard làm việc với server; agent chủ động liên lạc server. Chưa cần triển khai client đồng bộ trong B01–B02.

## 3. B01 — Danh tính và phiên Windows

| Khái niệm | Cần nhớ | Dùng trong dự án |
|---|---|---|
| SID | Định danh tài khoản Windows | Xác định tài khoản trẻ được quản lý |
| Session ID | Định danh phiên đăng nhập | Đọc tín hiệu và tác động đúng phiên |
| PID | Định danh tiến trình đang chạy | Tra cứu tiến trình của ứng dụng foreground |
| Access token | Chứa danh tính và quyền của tiến trình | Kiểm tra người đang kết nối IPC |
| LocalSystem | Tài khoản có quyền cao cho service | Phải giới hạn chặt giao diện mà user có thể gọi |
| Session 0 | Phiên chạy service | Không dùng làm nguồn foreground/idle của trẻ |

SID và session ID giải quyết hai câu hỏi khác nhau: **“tài khoản nào?”** và **“phiên nào?”**. Theo brief, MVP quản lý một phiên trẻ hoạt động trên một thiết bị.

**Cần thực hành:** tạo VM có tài khoản phụ huynh và tài khoản trẻ standard user. Chạy script in SID/session ID/PID ở từng tài khoản; đối chiếu với phiên service. Giữ log cho thấy không nhầm phiên trẻ với Session 0.

**API/từ khóa để tra cứu:** `WTSEnumerateSessions`, `WTSQuerySessionInformation`, process token, `pywin32`, `psutil`. Chỉ cài và pin phiên bản thư viện sau khi kiểm tra tương thích môi trường.

## 4. B01 — Foreground, idle và thời gian sử dụng

**Foreground** là ứng dụng người dùng đang tương tác. Một ứng dụng mở nhưng chạy nền không tự động được cộng thời gian sử dụng. Luồng thu thập cần hiểu: cửa sổ foreground → PID → executable → danh tính/phiên tương ứng. Chỉ dùng handle/PID để suy ra executable; không đọc, lưu hoặc gửi `window title`.

**Idle** là thời gian từ tương tác đầu vào gần nhất. `GetLastInputInfo` chỉ lấy thông tin của phiên gọi hàm, nên helper phải chạy đúng phiên trẻ. Đọc [Microsoft: GetLastInputInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getlastinputinfo).

Quy tắc đã nêu trong brief: tính thời gian đo được khi đúng SID trẻ, session active, không khóa/sleep và idle dưới ngưỡng cấu hình; ngưỡng mặc định là 5 phút. Ví dụ ngưỡng 300 giây: `idle = 299` còn thỏa điều kiện idle; `idle = 300` không thỏa.

| Tình huống | Tổng thời gian đo được | Thời gian app |
|---|---|---|
| Đúng phiên, đủ tín hiệu, active và idle dưới ngưỡng | Có | Gán cho foreground app khi xác định được |
| Khóa phiên, sleep hoặc disconnected | Không cộng vào active usage | Không cộng |
| Chỉ có ứng dụng chạy nền | Không dùng sự tồn tại process để kết luận đang sử dụng | Không cộng app nền |
| Helper mất kết nối hoặc tín hiệu quá cũ | Không gắn nhãn là đo chính xác; xử lý degraded cần chốt D03 | Không tự đoán foreground |

**D03 cần thống nhất với TV1/TV3:** khi thiếu helper nhưng phiên vẫn active, phần tổng thời gian ước lượng được tính và hiển thị thế nào? Đề xuất hiện tại là tách `measured_active` và `estimated_degraded`. Đây chưa phải quyết định đã nghiệm thu.

**Bài thử:** chuyển giữa hai app; ngừng thao tác; khóa/mở khóa; sleep/resume; dừng helper. Ghi tín hiệu trước/sau và khoảng thiếu dữ liệu. Video hoặc học không dùng chuột/phím có thể bị xem là idle; cần nêu giới hạn này.

## 5. B01 — IPC và ACL

**IPC** là giao tiếp giữa các tiến trình. **Named pipe** là kênh được ưu tiên trong thiết kế OGK. **ACL/DACL** quy định danh tính nào được quyền truy cập kênh đó. Đọc [Microsoft: Named Pipe Security and Access Rights](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights).

Service cần kiểm tra hai lớp: quyền truy cập pipe và nội dung thông điệp. Không coi trường `sid` do client gửi là bằng chứng danh tính; cần đối chiếu danh tính phía kết nối với phiên được quản lý.

Nội dung cần học và áp dụng trong spike:

- Tạo pipe server/client; gửi và nhận thông điệp có ranh giới rõ ràng.
- Cấu hình ACL cho các danh tính cần thiết; kiểm tra tài khoản ngoài phạm vi.
- Kiểm tra schema, loại thông điệp, kích thước tối đa và độ mới của tín hiệu.
- Có timeout để việc mất helper không làm treo service.
- Chỉ cho phép thao tác nghiệp vụ đã định nghĩa; không nhận shell hoặc yêu cầu chạy file tùy ý.

**Bài thử:** một client hợp lệ gửi trạng thái thành công; client ngoài phạm vi bị từ chối; payload sai cấu trúc/quá lớn/quá cũ bị loại. Lưu expected/actual cho từng ca. Giá trị giới hạn cụ thể phải chốt trong contract IPC với TV3.

## 6. B01 — Khóa phiên khác ngắt kết nối

| Thao tác | Ý nghĩa | Cần kiểm chứng |
|---|---|---|
| `LockWorkStation()` | Yêu cầu khóa workstation từ interactive desktop | Kết quả gọi chỉ thể hiện đã khởi tạo thao tác; theo dõi thông báo phiên để xác nhận khóa |
| `WTSDisconnectSession()` | Ngắt kết nối khỏi phiên, không đóng phiên | Đúng session ID và trạng thái disconnected sau thao tác |

Không suy ra “đã khóa” từ `WTSActive` hoặc chỉ từ giá trị trả về của API. Theo dõi khóa/mở khóa qua session notifications; ghi kết quả disconnected riêng với locked. Đây là nội dung **D04** cần kiểm chứng.

Đọc [Microsoft: LockWorkStation](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-lockworkstation) và [Microsoft: WTSDisconnectSession](https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsdisconnectsession).

**Bài thử:** thực hiện riêng thao tác khóa và disconnect trên VM; ghi nguồn gọi, phiên đích, kết quả API, tín hiệu xác nhận và kết quả quan sát. Kế hoạch fallback qua disconnect phải được mô tả đúng tác động.

## 7. B01 — DNS backup và khôi phục

DNS phân giải tên miền thành thông tin địa chỉ. Với OGK, proxy DNS cục bộ dự kiến nhận truy vấn rồi chuyển đến upstream hoặc chặn theo quy tắc. Phần TV2 cần chuẩn bị là thay đổi cấu hình adapter và khôi phục được; resolver do TV1 phụ trách.

| Thuật ngữ | Ý nghĩa cần nắm |
|---|---|
| Adapter | Giao diện mạng được chọn để quản lý |
| DNS tự động / tĩnh | Nhận cấu hình tự động hoặc đặt thủ công; phải phục hồi đúng chế độ |
| IPv4 / IPv6 | Hai họ địa chỉ, cần lưu cấu hình DNS tương ứng |
| Loopback | Địa chỉ nội bộ máy như `127.0.0.1`, `::1` |
| Upstream | DNS server mà proxy chuyển truy vấn tới |
| Rollback | Trả cấu hình về trạng thái trước khi thao tác gặp lỗi |

Thông tin cần lưu: định danh adapter, chế độ cấu hình DNS, danh sách server theo thứ tự và theo từng họ địa chỉ. Chỉ lưu địa chỉ hiện tại chưa đủ để chứng minh có thể khôi phục đúng chế độ tự động/tĩnh.

**Nguyên tắc dự án:** backup trước; proxy phải healthy trước khi đổi DNS; lỗi phải rollback; upstream không trỏ về chính proxy. DNS lookup không chứng minh người dùng dành bao nhiêu thời gian trên website.

**Bài thử:** sao lưu cấu hình adapter VM thành JSON, đối chiếu với cấu hình thực tế, chuẩn bị dry-run và cách restore. Mọi ca thay đổi thật chỉ chạy trên VM theo [quy định đóng góp](../CONTRIBUTING.md); ghi ca chưa thử rõ ràng.

## 8. B02 — Mô hình dữ liệu và Decision

Python tối thiểu cần dùng: module/package, type hints, `dataclass`, `Enum`, exception, JSON, logging và test có `assert`. Type hints giúp mô tả kiểu dữ liệu; việc kiểm tra payload bên ngoài vẫn cần validation riêng.

Thiết kế cần phân biệt:

- **Policy:** dữ liệu quy tắc, version và timezone.
- **Session signals:** tín hiệu quan sát được, kèm thời điểm và nguồn.
- **Usage state:** số liệu sử dụng cần cho đánh giá quy tắc.
- **Decision:** kết quả đánh giá để service và Tray dùng thống nhất.

| Trường Decision theo brief | Ý nghĩa cần thống nhất trong contract |
|---|---|
| `allowed` | Hành động/phạm vi đang xét có được phép không |
| `reason_code` | Mã lý do ổn định để UI diễn giải |
| `rule_id` | Quy tắc dẫn đến kết quả, thống nhất cách biểu diễn khi không có |
| `remaining_seconds` | Số giây còn lại trong phạm vi đang xét; định nghĩa rõ trường hợp không giới hạn |
| `next_transition_at` | Mốc dự kiến cần đánh giá lại do lịch/thời hạn; thống nhất trường hợp không có |

Các mã bị chặn đã gợi ý trong brief: `OUTSIDE_SCHEDULE`, `DAILY_QUOTA_EXCEEDED`, `APP_BLOCKED`, `MANUAL_LOCK`, `DOMAIN_BLOCKED`. Mã cho kết quả cho phép và ý nghĩa giá trị rỗng cần chốt với TV1/TV3.

**Dependency inversion trong bài này:** core nhận clock và tín hiệu từ bên ngoài. Adapter Windows phụ trách lấy dữ liệu thật. Nhờ đó test core dùng dữ liệu giả và không cần import `win32api` hoặc các module Windows.

**Bài thử B02:** thiết kế model và fixture Decision cho các tình huống cơ bản; test đọc fixture và các trường thống nhất; chứng minh import core không cần Windows. Chưa cần hoàn thiện engine B03.

## 9. B02 — Clock, timezone và fake clock

| Loại thời gian | Dùng để làm gì | Ví dụ |
|---|---|---|
| Wall-clock | Xác định ngày, lịch và timestamp | Hiện tại có nằm trong lịch 18:00–20:00 không? |
| Monotonic | Đo khoảng trôi qua trong một lần chạy | Đã có thêm 30 giây sử dụng |
| UTC và timezone | Lưu mốc thống nhất và xác định ngày địa phương | Quota reset theo ngày của timezone cấu hình |

`time.monotonic()` không bị việc chỉnh đồng hồ hệ thống làm lùi giá trị; dùng chênh lệch giữa hai lần đọc, không dùng nó như timestamp lịch. Không mặc định rằng chênh lệch monotonic luôn là active usage: vẫn phải xét sleep, lock và chất lượng tín hiệu. Đọc [Python: time.monotonic](https://docs.python.org/3/library/time.html#time.monotonic).

**Fake clock** là đối tượng clock do test điều khiển. Thiết kế clock nên cho phép đọc wall-clock, đọc monotonic và tăng thời gian giả độc lập khi kiểm thử chỉnh giờ. Nhờ đó test chạy nhanh, lặp lại được và không phải đợi `sleep()` thật.

Ví dụ cần hiểu:

- Lịch `[18:00, 20:00)`: 18:00 thuộc lịch; 20:00 đã ngoài lịch.
- 90 giây active đủ tín hiệu rồi 30 giây locked: kỳ vọng bộ đếm ở B04 là 90 giây.
- Chỉnh giờ lịch lùi 10 phút trong khi mới trôi qua 30 giây: không lấy hiệu giờ lịch để kết luận usage âm.
- Sleep/resume hoặc thiếu telemetry: không tự cộng toàn bộ khoảng mù thành active usage.

**Bài thử B02:** test đọc và tăng fake clock, test wall-clock có thể thay đổi độc lập với monotonic. Chuẩn bị timeline active/locked làm fixture cho engine/counter ở tuần 2; chưa ghi counter đã pass khi chưa triển khai.

## 10. Hồ sơ cần có để bàn giao tuần 1

- [ ] Script và hướng dẫn chạy spike trong `agent/spikes/`.
- [ ] Log SID/session của phụ huynh, trẻ và service; chứng minh đọc đúng phiên.
- [ ] Kết quả foreground/idle, khóa/mở khóa và tình huống mất helper.
- [ ] Kết quả IPC hợp lệ, sai danh tính và payload không hợp lệ.
- [ ] Kết quả phân biệt locked/disconnected; ghi bằng chứng xác nhận.
- [ ] DNS backup của adapter VM và kết quả/giới hạn thử restore.
- [ ] ADR ghi phương án D03/D04, căn cứ, người review và điểm chưa kiểm chứng.
- [ ] Model/Decision/clock trong `agent/core/`; fixture hợp đồng và test phù hợp.
- [ ] Review contract với TV1 và IPC/Decision với TV3; dùng fixture khi API chưa hoàn thành.
- [ ] Cập nhật tiến độ và evidence, có liên kết commit khi thực hiện triển khai.

Mỗi ca thử ghi: **môi trường/Windows build, commit, tài khoản/phiên, bước chạy, expected, actual, pass/fail/chưa chạy và vị trí log/ảnh**. Không chứa token hoặc dữ liệu thật trong evidence. Theo [checklist Windows](../agent/windows/CHECKLIST.md), các thao tác khóa/ngắt phiên/đổi mạng thực hiện trong VM lab.

## 11. Tự kiểm tra trước buổi báo cáo

| Câu hỏi | Ý chính cần trả lời được |
|---|---|
| Vì sao tách service và helper? | Session 0 tách với phiên tương tác; helper cung cấp tín hiệu đúng phiên |
| Vì sao cần cả SID và session ID? | Một cái nhận diện tài khoản, một cái nhận diện phiên |
| Chạy nền có tính thời gian app không? | Chỉ gán thời gian cho foreground khi đủ điều kiện sử dụng |
| Helper mất thì usage bằng 0 không? | Không đủ căn cứ; đánh dấu thiếu tín hiệu, tách phần ước lượng theo D03 |
| API khóa trả thành công đã đủ chưa? | Chưa; cần bằng chứng trạng thái khóa, phân biệt disconnect |
| Tại sao IPC cần ACL và validation? | Hạn chế bên được truy cập và loại dữ liệu/thao tác không hợp lệ |
| Tại sao dùng monotonic? | Đo khoảng trôi qua không phụ thuộc việc chỉnh giờ lịch |
| Làm sao test logic khi không chạy Windows? | Core nhận tín hiệu và clock qua giao diện; test dùng fixture/fake clock |
| Vì sao phải lưu chế độ DNS gốc? | Restore phải trả về đúng tự động/tĩnh, IPv4/IPv6 của adapter |

Thứ tự ôn đề xuất: **luồng hệ thống → SID/session → foreground/idle → IPC → lock/disconnect → DNS backup → models/Decision → clock/test**. Nếu thiếu bằng chứng B01, ghi rõ phần còn thiếu trước khi dựa vào kết luận đó để tích hợp B02 và các tuần sau.
