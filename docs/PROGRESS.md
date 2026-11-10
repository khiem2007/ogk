# Tiến độ thực tế

## 2026-10-24 — Khởi tạo bộ khung

- Đã đọc kế hoạch và xem 9 ảnh; giữ bản sao nguồn trong docs.
- Đã tạo cây thư mục theo đề xuất, README từng module, phân công 32 task cho 3 người/8 tuần.
- Đã thêm quy trình PR, issue template, CI chỉ kiểm tra cấu trúc và script kiểm tra không có dependency.
- Chưa triển khai backend/dashboard/agent/DNS, chưa có dependency runtime hay migration chạy được.
- Chưa cài Windows service, đổi DNS, kiểm thử tính năng hoặc đo mục tiêu lab.
- Kiểm tra: `python scripts/check_structure.py` — PASS: 17 thư mục bắt buộc, 9 ảnh và toàn bộ liên kết Markdown nội bộ. Chỉ xác minh bộ khung, chưa kiểm thử sản phẩm.

## 2026-10-26 — Điều chỉnh deadline thành 5 tuần

- Lịch hiện hành: 26/10–29/11/2026; đã cập nhật 32 task.
- Phân chia lại 5 mốc cuối tuần; tuần 5 chốt DNS, VM sạch, release candidate và demo.
- Giữ 136 giờ/người và 408 giờ nhóm; trung bình 27,2 giờ/người/tuần. Extension nằm sau deadline.
- Đồng bộ README, PROJECT_BRIEF, PHAN_CONG và DECISIONS; lưu nguồn trước cập nhật trong docs/reference.
- Tạo calendar iCalendar toàn nhóm và từng TV, cùng hướng dẫn chia sẻ/import; chưa tạo lịch trực tiếp trên tài khoản Calendar.
- Chỉ thay kế hoạch và lịch; chưa có bằng chứng mới về tiến độ triển khai sản phẩm.
- Kiểm tra bàn giao: script kiểm tra cấu trúc, đối chiếu 32 task với lịch, định dạng iCalendar và diff Git.

## 2026-11-02 — TV1 A01: SRS, ERD và API contract

- Đã viết `docs/SRS.md`: actors/use cases, MVP/extension/out-of-scope, 16 FR có AC riêng, NFR có acceptance ID, traceability đủ 9 ảnh và sequence policy → agent → event.
- Đã viết `docs/ERD.md` và `docs/API.md`; chốt ownership boundary, transaction/dedup, policy version, status/ACK, expiry, logical entities và endpoints v1.
- Đã bổ sung `docs/POLICY_RULES.md` để hoàn tất liên kết từ architecture và ghi truth table schedule/quota/grant/domain; phần này đang chờ review TV1/TV2/TV3 và chưa phải implementation.
- Đã tạo JSON Schema Draft 2020-12 v1 cho common, policy, event, command/ACK, request, grant và IPC; fixtures hợp lệ cho các luồng chính, dùng UUID/domain/SID giả.
- TV2/TV3 review: **chờ xác nhận**; chưa ghi nhận review hoặc acceptance contract v1.
- Diagnostics: VS Code `get_errors` không báo lỗi cho SRS/ERD/API, schema/fixture JSON và README liên quan. Đây là diagnostics cú pháp, chưa phải semantic validation đầy đủ.
- Chưa có server/OpenAPI/migration/runtime; schema format validation không thay semantic checks về ownership, temporal ordering, expiry, policy precedence hay session authorization.
- Bước tiếp: TV2 review policy/event/command/IPC và TV3 review request/UI states; cập nhật contract trước khi implementation lấy schema làm nguồn chuẩn.

## 2026-11-02 — TV2 triển khai B01 và B02

### B01 — Windows technical spikes

- Đã viết `spike_session_sid.py`: enumerate WTS, đọc WinStation/User/Domain, tra SID, nhận diện Session 0/Admin/Standard và lập kế hoạch fallback `WTSDisconnectSession` có guard Session 0 + token xác nhận.
- Đã viết `spike_foreground_idle.py`: đọc foreground HWND/PID/process/session và idle time qua `GetLastInputInfo`.
- Đã viết `spike_ipc_pipe.py`: Named Pipe message mode, DACL chỉ LocalSystem + SID trẻ, giới hạn 4096 byte, allowlist message type, UUID replay cache và timestamp skew tối đa 30 giây.
- Đã viết `spike_dns_backup.py`: đọc adapter active và DNS IPv4/IPv6, phân biệt DHCP/Static, backup JSON, lập kế hoạch/restore có đối chiếu GUID và `ipconfig /flushdns`.
- Tất cả CLI mặc định dry-run/read-only; thao tác ngắt phiên và restore DNS chỉ chạy khi có `--execute` và confirmation token.
- Đã ghi ADR đề xuất cho D03 và D04. Hai ADR chưa Accepted vì còn cần review nhóm và bằng chứng Windows VM.

### B02 — Pure Python core

- Đã thêm `Clock`, `SystemClock`, `FakeClock`; wall-clock UTC và monotonic độc lập, có `advance()` và mô phỏng chỉnh wall-clock.
- Đã thêm `ReasonCode`, `Decision`, `ScheduleWindow`, `CategoryQuota`, `AppRule`, `Grant`, `PolicySnapshot` dưới dạng frozen dataclass.
- `agent/core` không import pywin32/psutil hay Windows API.
- Đã thêm unit test pytest cho khởi tạo/immutability của model, validation và hành vi clock.

### Phạm vi kiểm chứng và giới hạn

- `pytest tests/unit -q` đạt **15 passed**; `compileall`, import `agent.core` và `scripts/check_structure.py` đều PASS.
- Smoke-test read-only trên Windows host bằng CPython 3.13 + pywin32 312 + psutil 7.2.2: WTS đọc đúng Session 0 và phiên console; foreground/PID/process/idle đọc được; IPC từ chối replay/payload quá cỡ/timestamp cũ; DNS backup và restore plan chạy được. Không gọi nhánh `--execute`.
- Chưa có Windows VM hai tài khoản, nên smoke-test host không phải nghiệm thu đầy đủ B01. Chưa thử live Named Pipe với SID sai, disconnect/lock thật, DNS restore thật hoặc adapter DNS Static.
- B01 mới là spike, chưa phải Windows service B05 hay DNS adapter transactional B09.

### Bước tiếp theo

1. Chạy checklist `scripts/spikes/README.md` trên snapshot VM và lưu evidence đã che dữ liệu.
2. TV1/TV3 review ADR D03/D04; chỉ Accepted sau test VM.
3. Dùng model/clock B02 làm nền cho B03/B04.

## 2026-11-05 — Đồng bộ đề bài PDF chính thức

- Đã đọc và render kiểm tra đủ 12 trang `docs/DoAn_UD_QL_SD_PC_TreEm.pdf`; xác định đây là nguồn yêu cầu ưu tiên so với 9 ảnh prototype.
- Đã thêm `REQUIREMENTS_TRACEABILITY.md`, `PRIVACY.md`, `THREATMODEL.md`, `AI_USAGE.md` và khung `BaoCaoKyThuatMang.md` cho M1–M6.
- Đã cập nhật brief, kiến trúc, phân công, quyết định, checklist Windows, README và lịch `.ics`: WebSocket/SafeSearch chuyển thành bắt buộc; retention dữ liệu trẻ 90 ngày; video 5–7 phút; ngưỡng policy 60 giây/lệnh 5 giây; tối thiểu 15 unit + 5 integration.
- Đã loại bỏ `window_title` khỏi spike foreground theo NT2. Không có cấu hình Windows/DNS nào bị thay đổi trong lần cập nhật này.
- Chưa triển khai các tính năng mới từ PDF chỉ bằng thay đổi tài liệu. Policy integrity, certificate pinning, child-view, SafeSearch, dataset 200 mục, retention/delete-all, WebSocket và M1–M6 vẫn phải được code/test theo task đã gán.
- Lịch nội bộ 5 tuần được giữ nguyên vì là quyết định trước của người dùng; PDF ghi thời lượng môn học 6 tuần và được ghi rõ như nguồn chính thức.
- Rủi ro tiến độ: tại ngày 05/11, deadline B03 trong kế hoạch là 04/11 nhưng repo chưa có policy engine; phạm vi bắt buộc cũng tăng. Nhóm cần re-estimate D10 trước khi coi mốc tuần 2 còn khả thi.
