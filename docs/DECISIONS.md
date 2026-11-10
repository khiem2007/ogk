# Giả định và điểm cần chốt

| Mã | Vấn đề trong nguồn | Cách dùng cho kế hoạch / việc cần kiểm chứng |
|---|---|---|
| D01 | Nguồn cũ ghi 7/8 tuần; PDF chính thức ghi thời lượng môn học 6 tuần; người dùng đã chọn kế hoạch nội bộ 5 tuần | Lịch thực hiện hiện hành vẫn là **26/10–29/11/2026** để hoàn thành sớm; không diễn giải thành thay đổi yêu cầu 6 tuần của môn học. Deadline chi tiết ở PHAN_CONG.md. |
| D02 | Chưa có tên/năng lực thành viên | Dùng TV1–TV3; điền tên thật trước giao việc, không tự gán tài khoản GitHub cho người khác. |
| D03 | Prompt 4 yêu cầu đếm khi helper chết, quy tắc thường loại idle | Đề xuất tách measured_active và estimated_degraded; không bịa foreground/app time. Xem [ADR-0001](adr/ADR-0001-degraded-telemetry-accounting.md), đang Proposed và chờ TV1/TV3 review + test VM. |
| D04 | Fallback WTSDisconnectSession được gọi là khóa | Tách disconnected khỏi locked; không ghi “đã khóa” chỉ vì API return. Xem [ADR-0002](adr/ADR-0002-disconnect-is-not-lock.md), đang Proposed và chờ manual test VM. |
| D05 | Kế hoạch cũ xếp SafeSearch/WebSocket vào extension | PDF chính thức yêu cầu SafeSearch qua DNS và lệnh khẩn dưới 5 giây qua WebSocket, nên đưa hai mục này vào MVP. Extension còn lại: template tuổi, 2FA, CSV, proxy HTTP(S)/WFP và installer đẹp. |
| D06 | Ảnh mờ/che, tên file không thể hiện thứ tự | Dùng mục lục ảnh theo filename; hai ảnh tổng quan không được tự coi là ảnh đầy đủ màn hình lịch. |
| D07 | Chưa chọn phiên bản thư viện | Chọn và pin trong milestone triển khai sau kiểm tra tương thích. Bộ khung không có dependency giả hoặc lệnh chạy app không tồn tại. |
| D08 | PDF chính thức ngày 05/11/2026 bổ sung yêu cầu và ngưỡng nghiệm thu khác kế hoạch từ ảnh | PDF là nguồn yêu cầu ưu tiên; dùng [ma trận truy vết](REQUIREMENTS_TRACEABILITY.md). Quyết định nội bộ chỉ được chi tiết hóa, không được hạ yêu cầu bắt buộc. |
| D09 | PDF yêu cầu nhóm chọn fail-open hoặc fail-closed sau N ngày offline | Chưa chốt. Trước B06 phải lập ADR nêu N ngày, protected allowlist, UX cảnh báo, rủi ro an toàn và test mất server; không tự chọn trong code. |
| D10 | PDF làm tăng phạm vi bắt buộc trong khi lịch 5 tuần/408 giờ giữ nguyên | Phải re-estimate và ưu tiên lại cùng cả nhóm. Không cắt yêu cầu bắt buộc hoặc ghi giờ cũ như cam kết đã bao phủ; có thể hoãn các extension trong D05. |

Các mục “đề xuất” phải được nhóm xác nhận bằng ADR và kiểm thử trước khi trở thành hành vi sản phẩm.
