# server/app/db

Phụ trách: **TV1**.

- `base.py`: DeclarativeBase dùng chung cho ORM và Alembic metadata.
- `session.py`: engine, session factory, dependency request, per-connection SQLite pragmas và health query.
- WAL và `busy_timeout=5000`; foreign-key enforcement bật cho app và migration.
- `create_app_engine()` dùng cho app và test engine; không dùng SQLite memory cho locking test.

Trạng thái: nền database A02 đã triển khai. Xem [bảng phân công](../../../docs/PHAN_CONG.md).
