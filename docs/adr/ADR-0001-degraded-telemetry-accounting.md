# ADR-0001: Tách usage đo được khỏi khoảng thiếu telemetry (D03)

- Trạng thái: **Proposed — cần TV1/TV3 review và kiểm chứng VM**
- Ngày: 2026-11-02
- Chủ trì: TV2

## Bối cảnh

Foreground và idle chỉ đáng tin khi helper trong phiên trẻ còn gửi telemetry. Service ở Session 0 không được tự suy diễn ứng dụng foreground của phiên tương tác. Nếu helper chết nhưng vẫn cộng thời gian như dữ liệu đo thật, báo cáo sẽ sai nguồn gốc; nếu tự động đưa về 0, quota có thể bị lách.

## Quyết định đề xuất

- `measured_active_seconds`: chỉ tăng khi có telemetry hợp lệ, đúng SID/session, phiên active/unlocked, không idle và app được quan sát.
- Khi tín hiệu quá hạn, trạng thái chuyển `DEGRADED`; không bịa foreground/app/category.
- Nếu sau này sản phẩm cần ước lượng tổng thời gian thiết bị, lưu riêng `estimated_degraded_seconds`, không cộng nó vào app/category measured và phải hiển thị nhãn ước lượng.
- Monotonic đo khoảng thời gian trong một lần chạy; UTC wall-clock phục vụ lịch và timestamp.

## Hệ quả

UI/API cần truyền freshness/source của telemetry. Counter B04 phải có truth table cho active, idle, locked, disconnected, sleep và degraded. Chưa thể đánh dấu Accepted trước review nhóm và test mất helper trên Windows VM.
