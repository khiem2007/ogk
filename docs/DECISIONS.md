# Giả định và điểm cần chốt

| Mã | Vấn đề trong nguồn | Cách dùng cho kế hoạch / việc cần kiểm chứng |
|---|---|---|
| D01 | Mục 1 ghi 7 tuần, mục 9 ghi 8 tuần | Dùng lịch chi tiết 8 tuần. 15–20 giờ/người/tuần tương đương 120–160 giờ/người, 360–480 giờ toàn nhóm. |
| D02 | Chưa có tên/năng lực thành viên | Dùng TV1–TV3; điền tên thật trước giao việc, không tự gán tài khoản GitHub cho người khác. |
| D03 | Prompt 4 yêu cầu đếm khi helper chết, quy tắc thường loại idle | Đề xuất tách measured_active và estimated_degraded; không bịa foreground/app time. TV2 chốt truth table với TV1/TV3 tuần 1 và hiển thị thiếu telemetry. |
| D04 | Fallback WTSDisconnectSession được gọi là khóa | Phải kiểm chứng trạng thái disconnected khác locked; tách kết quả ACK, không ghi “đã khóa” chỉ vì API return. Spike Windows tuần 1, manual tuần 4. |
| D05 | Mục 9 xếp age templates tuần 6, mục 3 xếp mở rộng | Ưu tiên luồng MVP; template tuổi chỉ sau luồng chính ổn định. Không báo 2FA/SafeSearch đã bật nếu chưa thực thi. |
| D06 | Ảnh mờ/che, tên file không thể hiện thứ tự | Dùng mục lục ảnh theo filename; hai ảnh tổng quan không được tự coi là ảnh đầy đủ màn hình lịch. |
| D07 | Chưa chọn phiên bản thư viện | Chọn và pin trong milestone triển khai sau kiểm tra tương thích. Bộ khung không có dependency giả hoặc lệnh chạy app không tồn tại. |

Các mục “đề xuất” phải được nhóm xác nhận bằng ADR và kiểm thử trước khi trở thành hành vi sản phẩm.
