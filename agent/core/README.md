# agent/core

Phụ trách: **TV2**.

Thư mục này chứa logic Python thuần, không import Windows API:

- `clock.py`: `Clock`, `SystemClock`, `FakeClock`; tách UTC wall-clock dùng cho lịch khỏi monotonic dùng để đo thời lượng.
- `models.py`: mã lý do, `Decision` và các model policy bất biến.
- `engine.py`: đánh giá precedence manual lock, app, lịch và quota; tính cảnh báo 10/5/1 phút.
- `counter.py`: ghi nhận usage đo được theo monotonic và checkpoint SQLite, không cộng gap khi restart/sleep.

Chạy kiểm thử từ thư mục gốc repo:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest agent/tests -q
```

Các module Windows nằm ngoài `agent/core`. Engine nhận `PolicySnapshot` đã được xác minh chữ ký và usage snapshot từ caller; hiện chưa nối vào helper/service để thi hành khóa hoặc cảnh báo grace.
