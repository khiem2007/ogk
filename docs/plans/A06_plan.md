# Kế hoạch triển khai A06 — Heartbeat và event ingestion/ACK

## Vấn đề
A06 thuộc TV1, phụ thuộc A04, và phải hoàn thiện đồng bộ trạng thái thiết bị cùng đầu ra telemetry có thể gửi lại an toàn. Hiện mã đã có mô hình `Device`, `UsageInterval`, `DeviceEvent`, khóa dedup theo `(device_id, event_id)`, cùng xác thực bearer của agent; chưa có route heartbeat/batch và dịch vụ ingest.

## Hướng tiếp cận
1. Chốt hợp đồng API trong các Pydantic model và response:
   - `POST /api/v1/agent/heartbeat`: nhận `applied_policy_version`, `agent_version`, bounded health state; server suy ra `device_id` từ bearer token, cập nhật `last_seen_at` trong transaction, và trả `server_time`, `desired_policy_version`, `connection_state`/command hint theo dữ liệu hiện có.
   - `POST /api/v1/agent/events/batch`: nhận một batch tối đa cố định (ví dụ 100 event), validate envelope theo hợp đồng và chặn payload/type không hợp lệ.

2. Tách logic vào `server/app/services/ingest.py`:
   - Chỉ chấp nhận đúng sự sở hữu device; không tin `device_id` do client gửi.
   - Chuẩn hóa timestamp thành UTC và xử lý trạng thái heartbeat.
   - Với mỗi event, phân biệt event đã tồn tại và event mới bằng khóa `(device_id, event_id)`.
   - Với `usage.interval`, ghi `UsageInterval`; với các event còn lại, ghi `DeviceEvent` cùng `reason_code/payload_json` tối thiểu.
   - Commit toàn batch trong một transaction, rồi mới trả danh sách ACK của các event đã commit.

3. Thiết kế retry/dedup/idempotency:
   - Re-submit cùng `event_id` là replay: không tạo dòng, không nhân dữ liệu và vẫn trả ACK.
   - Batch trùng lẫn nhau và event trùng trong cùng batch vẫn được xử lý an toàn.
   - Sử dụng unique constraint làm hàng rào cuối; bắt lỗi/race có kiểm soát ở transaction thay vì trả ACK trước commit.
   - Giới hạn số event và kích thước payload; từ chối malformed/batch quá tải bằng mã 4xx rõ ràng.

4. Bổ sung test tích hợp tập trung:
   - Device bearer hợp lệ/cảnh báo thiếu/hết hạn/token revoke.
   - Heartbeat cập nhật `last_seen_at` và trả `server_time`/desired policy version; mất liên lạc là trạng thái suy ra sau 180 giây, không suy ra máy đã tắt.
   - Batch usage/event hợp lệ commit đúng bảng.
   - Lost ACK/replay không nhân event hoặc usage.
   - Batch có event trùng, một invalid event, hoặc vượt bound không gây partial ACK sai; quyết định atomic rõ ràng trong thiết kế test.
   - Ngoài lề kiểm tra concurrency cơ bản nếu SQLite cho phép.

5. Cập nhật tài liệu trực tiếp liên quan: API.md và PROGRESS.md khi triển khai xong; không sửa lịch hoặc tài liệu ngoài phạm vi A06.

## Danh sách công việc (todos)
- `a06-contracts`: Chốt Pydantic/API response và giới hạn batch cho heartbeat/events.
- `a06-ingest-service`: Thực thi transaction ingest, dedup, ACK và mapping usage/device event.
- `a06-api-routes`: Thêm route heartbeat/events vào FastAPI và dùng device auth.
- `a06-ingest-tests`: Viết test integration cho auth, dedup, retry, replay, ACK sau commit và 180 giây.
- `a06-a06-docs`: Cập nhật API/progress sau khi implementation/test pass.

## Phụ thuộc thực thi
- `a06-ingest-service` phụ thuộc `a06-contracts`.
- `a06-api-routes` phụ thuộc `a06-contracts` và `a06-ingest-service`.
- `a06-ingest-tests` phụ thuộc `a06-api-routes`.
- `a06-a06-docs` phụ thuộc `a06-ingest-tests`.

## Lưu ý
- Giữ ACK nằm sau `db.commit()`/flush thành công.
- Không đưa ACK của event invalid hoặc chưa commit vào response.
- Không dùng nội dung URL/title/keylog/screenshot: payload chỉ nằm trong allowlist của event contract.
- Không mở rộng schema/tính năng sang request/grant/command thuộc A07/A08.
- Hạn chế đổi migration: hiện đã có unique constraint và bảng cần thiết; nếu implementation xác nhận cần field mới, phải bổ sung migration nhưng không dự đoán trước.