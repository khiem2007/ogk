# Kế hoạch thực hiện A07 — Request approve/reject và grant

## Mục tiêu
- Triển khai vòng đời request `pending -> approved | rejected | expired`.
- Tạo đúng một grant khi approve, có scope và expiry theo UTC/local date.
- Chống race/double-approve và đồng thời tạo grant trùng.
- Đảm bảo approve không vượt manual lock hoặc quota tổng.
- Kết nối API parent/dashboard và agent đồng bộ grant.

## Công việc
1. Thêm router server `/api/v1/requests`, `/api/v1/agent/requests` và `GET /agent/grants`.
2. Validate ownership, role, request/UUID/payload, timezone và local date.
3. Dùng transaction ghi `BEGIN IMMEDIATE`, conditional state transition và audit `before/after`.
4. Tạo grant atomically: time extension theo local date; app exception theo app/duration.
5. Kiểm tra policy manual lock và tổng quota trước khi approve; từ chối với 409/422 rõ ràng.
6. Thêm integration tests cho approve/reject, replay, double approve, ownership, manual lock và concurrency.
7. Cập nhật API docs và trạng thái/evidence nếu test đạt.

## Tiêu chí hoàn thành
- [ ] Hai approve đồng thời chỉ tạo một grant.
- [x] Retry request không nhân bản grant/request.
- [x] Reject không tạo grant.
- [x] Agent chỉ nhận grant của device mình.
- [x] Integration test A07 pass.

## Kết quả thực thi
- Đã thêm API request/grant trong `server/app/api/requests.py`.
- Đã đăng ký router trong `server/app/main.py`.
- Đã thêm integration test `tests/integration/test_requests.py`.
- Validation: `python -m pytest tests/integration/test_requests.py -q` — 2 passed.
