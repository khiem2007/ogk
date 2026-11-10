# agent/core

Phụ trách: **TV2**.

Thư mục này chứa logic Python thuần, không import Windows API:

- `clock.py`: `Clock`, `SystemClock`, `FakeClock`; tách UTC wall-clock dùng cho lịch khỏi monotonic dùng để đo thời lượng.
- `models.py`: mã lý do, `Decision` và các model policy bất biến.

Chạy kiểm thử từ thư mục gốc repo:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests/unit -q
```

Các module Windows phải nằm ngoài `agent/core`; việc phân giải tên timezone và engine đánh giá policy thuộc các task sau B02.
