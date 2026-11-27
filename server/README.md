# server

Phụ trách: **TV1**.

FastAPI, SQLAlchemy và Alembic; nền dữ liệu SQLite WAL cho lab, một worker.

## Cấu trúc dự kiến

- `server/app/api/`: router `/api/v1` và kiểm tra ownership.
- `server/app/auth/`: session, CSRF, token thiết bị và enrollment.
- `server/app/schemas/`: validation request/response theo contracts.
- `server/app/services/`: policy, approvals, ingest, commands, report và audit.

## Cài đặt

```powershell
python -m pip install -r requirements-dev.txt
```

## Database

- URL mặc định: `sqlite:///./runtime/ogk.db`.
- Ghi đè bằng environment `OGK_DATABASE_URL`, ví dụ `OGK_DATABASE_URL=sqlite:///./runtime/ogk.db`.
- Mỗi connection SQLite bật `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL` và `PRAGMA busy_timeout=5000`.
- Alembic là nguồn tạo schema. Không chạy `Base.metadata.create_all()` ngoài migration/test.

```powershell
python -m alembic -c server/alembic.ini upgrade head
python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

## Kiểm thử A02

```powershell
python -m pytest server/tests/test_db_config.py server/tests/test_db_foreign_keys.py server/tests/test_migrations.py server/tests/test_db_concurrency.py -q
python -m pytest -q
python scripts/check_structure.py
```

Xem [bảng phân công](../docs/PHAN_CONG.md) và task tiếp theo A03.
