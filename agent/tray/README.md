# OpenGuard Kids — Tray Agent Module

## Mô tả

`agent/tray/` là ứng dụng PySide6 chạy trong session của trẻ, hiển thị icon trên system tray bar.
Đây là giao diện duy nhất trẻ nhìn thấy và tương tác trực tiếp.

## Kiến trúc

```
agent/tray/
├── __init__.py      # Package marker
├── models.py        # TrayState dataclass (pure Python, không import Qt)
├── ipc_client.py    # IPCClient — giao tiếp với agent core qua Unix socket
├── app.py           # OgkTrayApp (QApplication) — main entry point
└── README.md        # (tài liệu này)
```

## Cài đặt

```bash
# Đã có trong .venv
source .venv/bin/activate
pip show PySide6  # PySide6 6.12.0
```

## Chạy (development)

```bash
source .venv/bin/activate
QT_QPA_PLATFORM=offscreen python -m agent.tray.app   # headless/CI
# hoặc bình thường (cần display)
python -m agent.tray.app
```

## Chạy Tests

```bash
source .venv/bin/activate
QT_QPA_PLATFORM=offscreen python -m pytest tests/unit/test_tray_state.py -v
```

Kết quả dự kiến: **14 passed**

## Quy tắc bắt buộc

| Rule | Mô tả |
|------|--------|
| **NT1** | Tab "Phần mềm này làm gì?" dùng ngôn ngữ cấp 1 tiếng Việt |
| **NT2** | KHÔNG log / truyền `window_title`, `url`, `screenshot`, `keylog` |
| **Tray guard** | Nếu `QSystemTrayIcon.isSystemTrayAvailable()` = False → `sys.exit(1)` |
| **Khởi động** | Luôn hiện notification: "OpenGuard Kids đang chạy công khai" |
| **Offline queue** | Requests chưa gửi được hiển thị "Chưa gửi (N)" |

## Luồng hoạt động

1. `OgkTrayApp` khởi động → kiểm tra tray availability
2. `QTimer` 1 giây: giảm `remaining_seconds`, tính `warning_level`
3. Ngưỡng cảnh báo: 10 phút → 5 phút → 1 phút → grace 60s → `BlockingDialog`
4. `IPCClient._poll_ipc()`: nhận `telemetry.sample` từ agent core → cập nhật state
5. Nhận `command.lock` → `manual_lock = True` → hiện `BlockingDialog`
6. Trẻ click "Xin thêm giờ" → `RequestDialog` → gửi `request.submit` IPC
   - Nếu offline: enqueue → hiện "Chưa gửi" → flush khi reconnect
