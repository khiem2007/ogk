# Kế hoạch A03 — Login/logout/me và phân quyền

## Vấn đề

Task **TV1-A03** cần hoàn thiện cơ chế xác thực phiên cho ba vai trò `parent`, `child-view` và `admin`, bảo vệ mutation bằng CSRF, khóa tài khoản sau lần thất bại, áp dụng ownership chống IDOR, và cho phép logout làm session cũ mất hiệu lực. A02 đã có FastAPI, SQLite migration và models cơ sở; chưa có auth runtime/API test.

## Phương án đề xuất

1. Bổ sung dependency/password hashing bằng **Argon2id** (ưu tiên) hoặc fallback kiểm tra scrypt; cập nhật user schema/runtime chỉ trong phạm vi auth cần thiết.
2. Thêm lớp session server-side với session ID ngẫu nhiên, thời hạn 12 giờ, cookie `HttpOnly`, `Secure` khi production/HTTPS và `SameSite=Lax`; lưu/hash session secret hoặc session record mà API không trả secret.
3. Triển khai `POST /api/v1/auth/login`, `POST /auth/logout` và `GET /auth/me`, thống nhất error envelope 401/403/429 theo `docs/API.md`.
4. Thêm dependency xác thực role; `parent` quản trị tài nguyên, `child-view` chỉ xem dữ liệu của chính mình, `admin` giới hạn đúng phạm vi được contract chốt. Không nhận `user_id/owner_id` làm authority từ body/query nếu có thể suy ra từ session.
5. Mutation tạo session/đăng xuất và các mutation auth sau A03 dùng CSRF double-submit hoặc signed CSRF token gắn session; POST login không yêu cầu CSRF; login/logout/me theo vai trò hiện tại.
6. Áp dụng password tối thiểu 10 ký tự, lockout 5 lần sai trong cửa sổ rate limit, khóa 15 phút; giới hạn login theo IP/email bằng store server-side/bounded cache, tránh timing leak cơ bản.
7. Viết audit auth tối thiểu khi login/logout failure? Ghi không secret/password/token/CSRF trong log.
8. Viết unit/integration test: login/logout/me; password hash; 5 sai/khóa 15 phút; login hết hạn khóa; role permissions; hai gia đình không đọc chéo; thiếu/sai CSRF bị 403; logout server-side; session expired; ownership 404/403 nhất quán.

## Phạm vi file dự kiến

- `server/app/auth/`: dependencies, password/session/CSRF helpers.
- `server/app/api/`: router auth và schemas request/response.
- `server/app/models/`: bổ sung bảng session, role hoặc trường auth cần migration.
- `server/migrations/versions/`: migration auth.
- `server/app/main.py`: đăng ký router/dependencies app.
- `server/tests/`: test auth/lockout/role/ownership/CSRF.
- `docs/API.md`, `docs/THREATMODEL.md`, `docs/PROGRESS.md`: cập nhật contract và bằng chứng trực tiếp liên quan.
- `requirements-dev.txt`: dependency password hashing nếu Argon2 được chọn.

## Phụ thuộc và thứ tự thực hiện

1. A02 đã hoàn tất migration/database foundation.
2. Chốt lại role/owner trong fixtures và migration trước khi viết API.
3. Dùng TestClient/httpx + SQLite tạm/migrated fixture để kiểm tra endpoint qua HTTP.
4. Review TV2/TV3: TV2 kiểm tra session/IPC? TV3 kiểm tra API/UI token và trạng thái 401/403/429.

## Bài nghiệm thu A03

- Mật khẩu tối thiểu 10 ký tự, mật khẩu sai đủ 5 lần khóa 15 phút.
- Login hợp lệ tạo session cookie đúng thuộc tính; session hết hạn và logout làm session cũ không dùng lại được.
- Login public có rate limit; mutation thiếu/sai CSRF bị từ chối.
- Parent/child-view/admin được kiểm tra theo role; child-view không có quyền mutation.
- Hai gia đình không đọc/sửa tài nguyên chéo; IDOR bị giữ ở query hoặc dependency, không chỉ frontend.
- Không ghi password, session secret, CSRF secret hoặc token vào log/output.
- `pytest`/migration/health/test suite liên quan PASS và có bằng chứng test trong `docs/PROGRESS.md`.

## Todo theo từng bước

- Tạo migration/model cho auth và session.
- Viết password hash/session/lockout/CSRF helpers.
- Cài endpoint login/logout/me và role dependency.
- Viết unit/integration tests auth và ownership.
- Cập nhật tài liệu contract/progress và chạy validation nhỏ nhất.
