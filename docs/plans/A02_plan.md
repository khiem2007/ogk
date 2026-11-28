# Kế hoạch triển khai Task A02

## Phát biểu vấn đề

A02 (`TV1`, 29–30/10/2026, phụ thuộc A01) cần đưa bộ khung FastAPI/SQLAlchemy/Alembic thành nền backend có thể khởi tạo SQLite trống bằng migration, bật khóa ngoại và WAL/busy timeout 5000ms, đồng thời cung cấp bộ test đơn vị/tích hợp cho migration, khóa ngoại và truy cập đọc/ghi đồng thời. Task này chỉ tạo nền dữ liệu/runtime của A02; chưa triển khai auth, enrollment hoặc endpoint nghiệp vụ của A03 trở đi.

## Mục tiêu thiết kế

- FastAPI chạy được bằng một worker lab; SQLite là engine mặc định, cấu hình DB lấy từ environment và có giá trị dev an toàn.
- SQLAlchemy ORM có declarative base/session factory; dependency FastAPI tạo session theo transaction/request.
- Alembic là nguồn duy nhất tạo schema; chạy nâng cấp từ DB trống phải tạo đầy đủ bảng/migration baseline theo ERD.
- Mỗi kết nối SQLite thực thi `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`; không dùng SQLite memory ngoài test, hoặc nếu dùng test thì chia implementation-engine riêng để tránh thiếu locking/foreign-key semantics.
- Timestamp lưu UTC; khóa ngoại, index và unique constraint theo ERD được khai báo cả ORM và migration để không phụ thuộc ORM để giữ dữ liệu hợp lệ.

## Các file cần tạo

- `alembic.ini`: cấu hình Alembic, script_location trỏ tới `server/migrations`, URL mặc định trùng cấu hình ứng dụng.
- `server/__init__.py`: đánh dấu package server.
- `server/app/__init__.py`: đánh dấu package application.
- `server/app/config.py`: đọc database URL/env, chuẩn hóa đường dẫn SQLite dev; không hard-code secret.
- `server/app/main.py`: tạo FastAPI app, include health/version smoke route tối thiểu nếu phù hợp; không triển khai auth/API nghiệp vụ của task sau.
- `server/app/db/__init__.py`: export engine/session/dependency hiện trạng.
- `server/app/db/base.py`: declarative Base, metadata và helper registry model.
- `server/app/db/session.py`: tạo engine, SQLite pragmas, session factory, `get_db_session`, lifespan/startup validation theo yêu cầu.
- `server/app/models/__init__.py`: import/register tất cả ORM models để Alembic autogenerate thấy metadata.
- `server/app/models/entities.py`: khai báo baseline ORM cho bảng server trong ERD: `users`, `children`, `devices`, `enrollment_codes`, `policies`, `app_catalog`, `usage_intervals`, `device_events`, `requests`, `grants`, `commands`, `audit_logs`, `transparency_records`.
- `server/migrations/env.py`: Alembic async/sync selection phù hợp SQLAlchemy, import metadata/app config, migration offline/online, đặt URL runtime.
- `server/migrations/script.py.mako`: template migration chuẩn Alembic.
- `server/migrations/versions/<revision>_initial_schema.py`: migration baseline, tạo tất cả bảng/khóa ngoại/index/unique constraints theo ERD và migration date; đặt `PRAGMA foreign_keys=ON` ở môi trường migration.
- `tests/conftest.py`: fixture temporary SQLite database, engine/session/DB override, gọi Alembic upgrade tới `head`, cleanup DB/WAL/SHM.
- `server/tests/test_db_config.py`: kiểm tra parsing config và dependency không phụ thuộc Windows.
- `server/tests/test_db_foreign_keys.py`: kiểm tra foreign key enforcement và quan hệ cascade/restrict/reject theo quyết định model.
- `server/tests/test_migrations.py`: upgrade DB trống, downgrade/upgrade lại (nếu được hỗ trợ), so khớp critical table/column/index/unique/FK sau migrate.
- `server/tests/test_db_concurrency.py`: kiểm tra concurrent read/write, locked writer timeout/busy timeout và WAL cho phép reader không bị chặn bởi writer đang giữ transaction.

## Các file có thể cần cập nhật

- `requirements-dev.txt`: pin dependency runtime/dev sau kiểm tra tương thích môi trường: FastAPI, Uvicorn, SQLAlchemy, Alembic, HTTPX/asgi-lifter nếu smoke-test TestClient, pytest; khóa phiên bản tương thích Python hiện dùng và ghi lệnh setup.
- `.gitignore`: đã có quy tắc DB/WAL/SHM/env, chỉ cập nhật nếu phát sinh artifact mới cần loại trừ.
- `server/README.md`: thêm setup env, `alembic upgrade head`, chạy migration/health app và lệnh test cụ thể; ghi rõ một worker lab.
- `server/app/db/README.md`, `server/app/models/README.md`, `server/migrations/versions/README.md`: thay placeholder trạng thái bằng hướng dẫn implementation và các invariant đã hoàn thành.
- `docs/PROGRESS.md`: ghi kết quả A02 chỉ sau khi migration/test thực sự pass, kèm lệnh và phạm vi chưa hoàn thành.

## Database và Alembic — thứ tự thực hiện

1. Chốt engine/config: mặc định SQLite theo env, ví dụ `OGK_DATABASE_URL=sqlite:///./runtime/ogk.db`; tạo thư mục runtime an toàn trước khi tạo engine.
2. Tạo SQLAlchemy engine singleton dùng `check_same_thread=False` cho kết nối SQLite; bắt PRAGMA bằng SQLAlchemy event `connect` theo từng connection.
3. Cấu hình session: `expire_on_commit=False`, autocommit false, autoflush false; dependency `get_db_session()` commit/rollback theo request và đóng session trong `finally`.
4. Tạo declarative models baseline từ ERD: UUID-like text/UUID column theo lựa chọn hỗ trợ SQLite; UTC datetime; JSON text/JSON; các trường secret dùng hash, không lưu plaintext; quan hệ rõ owner/device/child.
5. Khai báo invariant quan trọng: FK với `ondelete` phù hợp, `email` normalized unique, `policies(device_id, version)` unique, event `(device_id,event_id)` unique, grant `request_id` unique, command `(device_id,dedup_key)` unique, index report/audit/device/status/time.
6. Khởi tạo Alembic: template/env; migration baseline là snapshot ERD hiện tại. Bất kỳ thay đổi sau A02 phải qua revision mới, không sửa migration đã phát hành.
7. Bật foreign keys qua PRAGMA cả Alembic engine và app engine; tránh pin hoặc xóa cứng SQLite file trong production; migration phải chạy trên SQLite và rollback/schema strategy ghi rõ nếu có.
8. Kiểm tra nâng cấp: tạo DB temporary, `alembic upgrade head`, mở bằng SQLAlchemy đọc metadata; chạy lại upgrade là idempotent qua Alembic.

## Unit tests

- Config đơn giản: database URL được đọc, SQLite URL tạo thư mục cần thiết, không dùng config Windows.
- Engine pragmas: mỗi fresh connection bật `foreign_keys=1` và `busy_timeout=5000`; metadata xác nhận mode WAL sau khi engine/fixture khởi tạo.
- Foreign key: thêm child trỏ owner không tồn tại phải rollback/raise; thêm usage/event trỏ device không tồn tại bị từ chối; unique `(device_id,event_id)` và `(device_id,dedup_key)` bị trùng phải conflict.
- Session: rollback lỗi không để transaction một phần; session dependency đóng kết nối và không reuse state chéo test.
- Timestamp/timezone: các trường UTC có timezone-aware policy; không đưa naive datetime vào cột cần timestamp UTC.

## Integration tests

- **Migration trống:** temp DB không có file/schema trước test; chạy `alembic upgrade head`; xác nhận tất cả ERD table, primary/foreign/unique key và index tồn tại.
- **Foreign keys thực:** bật `PRAGMA foreign_keys`, thử insert parent-child/dependent không hợp lệ và xóa parent đang có child; kiểm tra NoAction/Restrict hoặc cascade đã khai báo nhất quán ORM/migration.
- **WAL/busy timeout:** query `PRAGMA journal_mode`, `PRAGMA foreign_keys`, `PRAGMA busy_timeout`; tạo temporary DB và xác nhận mode `wal`, busy 5000.
- **Concurrent read/write:** worker 1 giữ writer transaction lâu hơn read? Thiết kế hai luồng: reader đọc snapshot trong khi writer đang commit; không dùng sleep thật để điều tiết—dùng barrier/Event.
- **Lock contention:** writer giữ lock, writer hoặc transaction thứ hai cố ghi trong cửa sổ ngắn; test chấp nhận timeout SQLite trong khoảng busy_timeout hoặc thành công sau busy wait, không assert race nondeterministic. Tách test dưới 5 giây tùy CI.
- **Read consistency:** hai session đồng thời insert device/child hoặc usage; commit/rollback theo isolation và xác nhận một fixture không bị orphan.
- **Migration + concurrency:** chạy migration trên DB temp trước hai session; không chạy multiple Alembic upgrades đồng thời.
- **Retry/idempotent baseline:** duplicate unique event key bị từ chối, sau đó retry có cùng key không nhân bản (dùng ORM constraint hoặc transaction-level test; semantic service ACK thuộc A06/A07).

## Tiêu chí nghiệm thu A02

- `alembic upgrade head` trên DB trống tạo được schema đầy đủ baseline mà không cần SQL thủ công.
- App engine/session/service có thể mở connection, rollback/commit, đóng session và không import Windows API.
- Foreign key enforcement được kích hoạt và test tích hợp chứng minh row không hợp lệ bị từ chối.
- SQLite journal là WAL và busy timeout là 5000ms trên mỗi connection trong app/migration fixture.
- Test reader/writer đồng thời không chết lock, không mất/corrupt dữ liệu, có timeout giới hạn và có kết quả xác định.
- `python scripts/check_structure.py` vẫn pass; bộ test A02 pass hoặc failure được ghi rõ, không giả nghiệm thu khi chưa chạy.

## Thứ tự triển khai khi được duyệt

1. Cài dependency đã pin và xác nhận version.
2. Tạo config/engine/session/base.
3. Tạo ORM models baseline.
4. Tạo Alembic env và migration initial.
5. Viết fixtures/unit/integration.
6. Chạy migration trống và test targeted; sửa lỗi; cập nhật README/PROGRESS sau nghiệm thu.
