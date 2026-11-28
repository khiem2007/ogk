# Kế hoạch thực hiện A08 — Command queue, ACK, audit và WebSocket notify

## Mục tiêu
- Hoàn thiện server-side command queue theo allowlist, expiry và idempotency.
- Tách rõ trạng thái `queued -> delivered -> executed | failed | expired`; không suy ra executed từ delivery.
- Cung cấp WebSocket notification bắt buộc và polling fallback bền vững.
- Ghi audit cho issue/delivered/ACK/expiry với dữ liệu lọc secret.
- Phạm vi: server-side A08; không triển khai agent core/Windows effect hoặc UI C06.

## Công việc
1. Mở rộng model/migration command lifecycle: issued/delivered/resolved timestamps, trạng thái và dedup key.
2. Thêm API parent tạo/lấy command; validate owner, role, CSRF, allowlist và expiry; trả `queued` chưa phải executed.
3. Thêm API agent polling và ACK; polling chỉ trả command của thiết bị và loại bỏ command hết hạn; ACK idempotent theo `command_id`.
4. Thêm WebSocket notification cho thiết bị; xác thực bằng device access token; socket chỉ phát tín hiệu command_id, không thay thế queue/polling.
5. Dùng transaction/conditional update để chặn race, replay và double ACK; giữ `delivered != executed`.
6. Ghi audit từng transition; payload/result chỉ chứa field allowlisted.
7. Viết integration tests cho allowlist/schema, expiry, ownership, duplicate, lost ACK, replay, concurrent ACK và reconnect/poll fallback.
8. Cập nhật API/contract/traceability/evidence và chạy test integration liên quan.

## Tiêu chí hoàn thành
- [x] Parent chỉ tạo command allowlisted.
- [x] Polling/ACK chỉ phục vụ đúng device.
- [x] Hết hạn không deliver hoặc không thực thi muộn.
- [x] Replay reconnect không nhân bản command/result/audit.
- [x] ACK trùng/idempotent không ghi đè result đã chốt.
- [x] WebSocket mất kết nối không làm mất intent; polling lấy lại command.
- [x] Audit ghi issue/delivery/result/expiry và test pass.

## Kết quả thực thi
- Đã thêm `server/app/api/commands.py` với tạo/lịch sử command, polling, ACK, lifecycle audit và WebSocket notify.
- Đã đăng ký router trong `server/app/main.py`.
- Đã mở rộng model `Command` và migration `20261128_004_command_lifecycle.py` với issued/delivered/resolved timestamps.
- Đã bổ sung API documentation và integration tests `server/tests/test_commands.py`.
- Validation: `python -m pytest server/tests -q` — 31 passed trên nhánh A08.

## Ghi chú
- Không shell: server không nhận payload tự do hay thực thi OS effect.
- WebSocket là notify nhanh; queue/poll là nguồn bền vững.
- Công việc Windows effect thuộc B07 và C06.
