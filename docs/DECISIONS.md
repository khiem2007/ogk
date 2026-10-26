# Giả định và điểm cần chốt

| Mã | Vấn đề trong nguồn | Cách dùng cho kế hoạch / việc cần kiểm chứng |
|---|---|---|
| D01 | Nguồn ban đầu ghi 7/8 tuần; người dùng yêu cầu rút còn 5 tuần và đã chọn ngày | Lịch hiện hành **26/10–29/11/2026**; 136 giờ/người/5 tuần = 27,2 giờ/người/tuần, 408 giờ nhóm. Giữ nguồn trong reference/Ke-hoach-va-prompt-OGK.original.md; deadline chi tiết ở PHAN_CONG.md. |
| D02 | Chưa có tên/năng lực thành viên | Dùng TV1–TV3; điền tên thật trước giao việc, không tự gán tài khoản GitHub cho người khác. |
| D03 | Prompt 4 yêu cầu đếm khi helper chết, quy tắc thường loại idle | Đề xuất tách measured_active và estimated_degraded; không bịa foreground/app time. TV2 chốt truth table với TV1/TV3 tuần 1 và hiển thị thiếu telemetry. |
| D04 | Fallback WTSDisconnectSession được gọi là khóa | Phải kiểm chứng trạng thái disconnected khác locked; tách kết quả ACK, không ghi “đã khóa” chỉ vì API return. Spike Windows tuần 1, manual tuần 3 (09–15/11). |
| D05 | Nguồn ban đầu xếp age templates tuần 6, nhưng phạm vi ghi mở rộng | Trong lịch 5 tuần, toàn bộ extension sau 29/11: template tuổi, SafeSearch, WebSocket, 2FA, CSV, installer đẹp. Giữ installer script tối thiểu và DNS rollback trong MVP. |
| D06 | Ảnh mờ/che, tên file không thể hiện thứ tự | Dùng mục lục ảnh theo filename; hai ảnh tổng quan không được tự coi là ảnh đầy đủ màn hình lịch. |
| D07 | Chưa chọn phiên bản thư viện | Chọn và pin trong milestone triển khai sau kiểm tra tương thích. Bộ khung không có dependency giả hoặc lệnh chạy app không tồn tại. |

Các mục “đề xuất” phải được nhóm xác nhận bằng ADR và kiểm thử trước khi trở thành hành vi sản phẩm.
