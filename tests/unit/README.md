# tests/unit

Phụ trách: **theo chủ module**; bộ test B02 do **TV2** phụ trách.

Hiện có unit test cho:

- `FakeClock`, `advance`, wall-clock rollback độc lập và monotonic.
- `SystemClock` UTC/monotonic.
- tập `ReasonCode`, khởi tạo/validation/immutability của `Decision` và `PolicySnapshot`.

Chạy test:

```powershell
python -m pytest tests/unit -q
```

Test core không import Windows API và không dùng `sleep` thật.
