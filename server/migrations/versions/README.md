# server/migrations/versions

Phụ trách: **TV1**.

- `20261123_001_initial_schema.py`: migration baseline tạo toàn bộ bảng ERD, indexes và constraints.
- Migration bật foreign keys/busy timeout và WAL trước tạo schema.
- Dùng `python -m alembic upgrade head` để tạo DB trống; không chỉnh sửa revision đã phát hành.

Trạng thái: baseline A02 đã triển khai. Xem [bảng phân công](../../../docs/PHAN_CONG.md).
