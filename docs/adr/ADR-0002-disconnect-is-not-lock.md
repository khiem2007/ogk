# ADR-0002: WTS disconnect không đồng nghĩa khóa màn hình (D04)

- Trạng thái: **Proposed — nhánh API đã được cài đặt, hành vi cần kiểm chứng Windows VM**
- Ngày: 2026-11-02
- Chủ trì: TV2

## Bối cảnh

Tray có thể bị tắt nên service cần phương án dự phòng từ Session 0. `WTSDisconnectSession` ngắt phiên khỏi trạm hiển thị, nhưng không chứng minh đã tạo trạng thái khóa theo nghĩa của UI Windows.

## Quyết định đề xuất

- Gọi kết quả API là `DISCONNECT_REQUESTED`, sau đó enumerate lại WTS để xác minh `DISCONNECTED` hoặc lỗi.
- Không phát ACK `LOCKED` chỉ vì `WTSDisconnectSession` trả về thành công.
- Tín hiệu lock/unlock phải đến từ session notification/helper và được lưu khác với connected/disconnected.
- Chỉ cho phép target phiên trẻ đã xác định bằng SessionId + SID; cấm Session 0, phiên phụ huynh và phiên hệ thống.

## Hệ quả

Command contract và UI phải phân biệt lock với disconnect. Spike hiện có guard Session 0, target và confirmation token; vẫn cần manual test trên VM với tài khoản parent Admin và child Standard trước khi ADR được Accepted.
