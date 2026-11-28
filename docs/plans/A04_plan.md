# Kế hoạch A04 — Enrollment và token cho device

## Vấn đề và hướng tiếp cận

Theo A04 trong `docs/PHAN_CONG.md`, bổ sung luồng ghép device với enrollment code 8 ký tự, hiệu lực 10 phút, dùng một lần; cấp access token có hạn 15 phút và refresh/revoke gắn với đúng device. Mọi secret chỉ trả về một lần, lưu dạng hash ở server và không xuất hiện trong log. Luồng consume code, tạo device và credential phải là một transaction để tránh code bị dùng lặp khi có request đồng thời.

Codebase hiện có FastAPI/SQLAlchemy, `EnrollmentCode`, `Device.token_hash` và migration nền. Chưa có endpoint/services cho enrollment hoặc device token. Kế hoạch ưu tiên mở rộng các patterns hiện có và API contract v1.

## Phạm vi đề xuất

- Thêm endpoint cho parent tạo enrollment code, agent enroll bằng code, refresh credential; thêm thao tác parent revoke device.
- Gắn enrollment code với child thuộc parent đã đăng nhập; không tin `owner_id`/`device_id` do agent gửi để quyết định quyền.
- Sinh code/token bằng nguồn ngẫu nhiên mật mã; chỉ lưu hash, áp giới hạn thử code và trả lỗi không tiết lộ trạng thái nhạy cảm.
- Lưu trạng thái token/refresh expiry và revoke theo device; kiểm tra access-token expiry/revocation ở mọi request agent.
- Thêm migration, ORM/service/API schemas, tests unit/integration và cập nhật `docs/API.md` cùng tài liệu liên quan.
- Không triển khai Windows agent token storage/DPAPI, certificate pinning, heartbeat hay policy sync (thuộc B06/A11); không đổi luồng đăng nhập parent A03.

## Các bước thực hiện

1. Chốt contract request/response, loại token và quy tắc refresh/revoke; đối chiếu A04, API, ERD và threat model.
2. Thiết kế migration/model cho enrollment expiry/consume, device credentials, refresh rotation/revoke và indexes/constraints cần thiết.
3. Cài đặt service có transaction cho tạo code, enroll một lần, refresh và revoke; bảo đảm kiểm tra ownership và thiết bị.
4. Cài đặt endpoint/schema và dependency xác thực agent; token hết hạn/revoked hoặc gắn device khác phải bị từ chối.
5. Viết unit/integration tests cho code hết hạn/dùng lại, enroll cạnh tranh, rate limit, refresh/rotation, revoke đúng device, ownership và không lộ secret trong logs/responses.
6. Cập nhật API/ERD hoặc README liên quan; chạy tests server phù hợp, migration tests và kiểm tra cấu trúc.

## Tiêu chí nghiệm thu

- Enrollment code đúng 8 ký tự, hết hạn sau 10 phút, chỉ dùng thành công một lần kể cả khi có request đồng thời.
- Access token hết hạn sau 15 phút; refresh/revoke chỉ ảnh hưởng credential/device tương ứng.
- Credential hết hạn hoặc bị revoke không còn cấp quyền; secret plaintext không lưu trong DB hay log.
- Agent không thể chọn device/child tùy ý để vượt qua ownership boundary.
- Migration chạy được trên DB mới và DB đã có; tests xác nhận cả happy path lẫn lỗi/đua tranh.

## Quyết định đã xác nhận

- Access token opaque, lưu hash server-side để kiểm tra expiry/revoke ngay.
- Refresh token opaque, hạn 30 ngày, rotate sau mỗi lần dùng và từ chối token cũ.
- Enrollment code bind với child thuộc parent; tối đa 5 lần nhập sai trước khi vô hiệu hóa code.

## Ghi chú triển khai

- Dùng một bảng/session credential riêng nếu `Device.token_hash` không đủ biểu diễn access expiry và vòng đời refresh; quyết định schema cuối cùng sau khi kiểm tra migration hiện có.
- Chọn alphabet code 8 ký tự tránh ký tự dễ nhầm; rate-limit thử sai phù hợp với cả code lẫn nguồn request.
- Lưu verifier của enrollment code theo cách chống dò offline phù hợp entropy thấp; không ghi code hay token plaintext vào log.

## Todos

- Chốt alphabet/format mã và cách lưu verifier.
- Thiết kế migration/model và contract A04.
- Triển khai endpoint/service enrollment, refresh và revoke.
- Bổ sung kiểm thử A04 và cập nhật tài liệu.
- Chạy xác minh migration, tests và cấu trúc.
