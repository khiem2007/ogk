# Tiến độ thực tế

## 2026-10-24 — Khởi tạo bộ khung

- Đã đọc kế hoạch và xem 9 ảnh; giữ bản sao nguồn trong docs.
- Đã tạo cây thư mục theo đề xuất, README từng module, phân công 32 task cho 3 người/8 tuần.
- Đã thêm quy trình PR, issue template, CI chỉ kiểm tra cấu trúc và script kiểm tra không có dependency.
- Chưa triển khai backend/dashboard/agent/DNS, chưa có dependency runtime hay migration chạy được.
- Chưa cài Windows service, đổi DNS, kiểm thử tính năng hoặc đo mục tiêu lab.
- Kiểm tra: `python scripts/check_structure.py` — PASS: 17 thư mục bắt buộc, 9 ảnh và toàn bộ liên kết Markdown nội bộ. Chỉ xác minh bộ khung, chưa kiểm thử sản phẩm.
- Bước tiếp: điền tên thật; làm A01/B01/C01; chốt D03/D04 bằng spike và ADR.


## 2026-10-26 — Điều chỉnh deadline thành 5 tuần

- Lịch đã được người dùng chọn: 26/10–29/11/2026; cập nhật ngày bắt đầu/deadline cho 32 task.
- Phân chia lại 5 mốc cuối tuần; tuần 5 chốt DNS, VM sạch, release candidate và demo.
- Giữ 136 giờ/người và 408 giờ nhóm; trung bình 27,2 giờ/người/tuần. Extension nằm sau deadline.
- Đồng bộ README, PROJECT_BRIEF, PHAN_CONG và DECISIONS; lưu nguồn trước cập nhật trong docs/reference.
- Tạo calendar iCalendar toàn nhóm và từng TV, cùng hướng dẫn chia sẻ/import; chưa tạo lịch trực tiếp trên tài khoản Calendar.
- Chỉ thay kế hoạch và lịch; chưa có bằng chứng mới về tiến độ triển khai sản phẩm.
- Kiểm tra bàn giao: script kiểm tra cấu trúc, đối chiếu 32 task với lịch, định dạng iCalendar và diff Git.

## 2026-11-02 — TV1 A01: SRS, ERD và API contract

- Đã viết `docs/SRS.md`: actors/use cases, MVP/extension/out-of-scope, 16 FR có AC riêng, NFR có acceptance ID, traceability đủ 9 ảnh và sequence policy → agent → event.
- Đã viết `docs/ERD.md` và `docs/API.md`; chốt ownership boundary, transaction/dedup, policy version, status/ACK, expiry, logical entities và endpoints v1.
- Đã tạo JSON Schema Draft 2020-12 v1 cho common, policy, event, command/ACK, request, grant và IPC; fixtures hợp lệ cho các luồng chính, dùng UUID/domain/SID giả.
- TV2/TV3 review: **chờ xác nhận**; chưa ghi nhận review hoặc acceptance contract v1.
- Diagnostics: VS Code `get_errors` báo không có lỗi cho SRS/ERD/API, các schema/fixture JSON và các README liên quan. Đây là diagnostics cú pháp, chưa phải chạy JSON Schema validator trên instance. `python scripts/check_structure.py` chưa chạy vì terminal không trỏ tới working tree VFS; repo chưa có runtime validator dependency.
- Chưa có server/OpenAPI/migration/runtime; schema format validation không thay semantic checks về ownership, temporal ordering, expiry, policy precedence hay session authorization.
- Bước tiếp: TV2 review policy/event/command/IPC và TV3 review request/UI states; cập nhật contract trước khi implementation lấy schema làm nguồn chuẩn.
