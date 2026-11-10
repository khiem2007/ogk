# Lịch dự án 5 tuần để gửi nhóm

Lịch đã chốt **26/10/2026–29/11/2026**, ngày địa phương UTC+7. Hạn cuối là hết ngày
**Chủ nhật 29/11/2026**. Chi tiết công việc và kiến thức tại [PHAN_CONG.md](../PHAN_CONG.md).

## Tải file lịch

| File | Nội dung | Dành cho |
|---|---|---|
| [OGK-5-tuan-toan-nhom.ics](OGK-5-tuan-toan-nhom.ics) | 39 sự kiện: 32 công việc, kickoff, 5 mốc cuối tuần và chốt bản nghiệm thu | Một lịch dùng chung cho cả nhóm |
| [OGK-5-tuan-TV1.ics](OGK-5-tuan-TV1.ics) | 12 công việc TV1 và 7 mốc chung | TV1 |
| [OGK-5-tuan-TV2.ics](OGK-5-tuan-TV2.ics) | 10 công việc TV2 và 7 mốc chung | TV2 |
| [OGK-5-tuan-TV3.ics](OGK-5-tuan-TV3.ics) | 10 công việc TV3 và 7 mốc chung | TV3 |

Các sự kiện là **cả ngày**, thể hiện khoảng triển khai; ngày cuối sự kiện là deadline task.
Không đặt giờ họp hoặc tự chặn lịch bận. Mô tả chứa mã việc, chủ trì, ước lượng,
phụ thuộc, đầu ra, kiến thức cần học và tiêu chí nghiệm thu. Không có danh sách người nhận.

**Chọn một cách nhập:** dùng file toàn nhóm cho lịch chung, hoặc dùng file riêng cho từng người.
Không nhập cả hai vào cùng một calendar vì các mốc chung và công việc sẽ trùng.

## Cách dùng và gửi nhóm

1. Trên GitHub, mở file `.ics` và dùng **Download raw file** để tải file.
2. Tạo một calendar riêng, ví dụ **OGK — Deadline 29/11/2026**.
3. Nhập file `.ics` vào calendar vừa tạo. Với Google Calendar trên web: **Settings → Import & export → Import**, chọn file và calendar đích.
4. Người quản lý calendar chia sẻ calendar đó với nhóm bằng email thành viên, hoặc gửi file `.ics` để từng người tự nhập. Repo riêng tư yêu cầu quyền truy cập; gửi file tải về nếu thành viên chưa có quyền repo.
5. Nếu cập nhật lịch sau này, thay các sự kiện trong calendar dự án riêng. File import là bản sao tĩnh, không tự đồng bộ theo GitHub; tránh nhập lại nhiều lần vào lịch cá nhân.

Định dạng iCalendar có thể nhập bằng Google Calendar hoặc Outlook. Chưa tạo lịch trực tiếp trên
tài khoản Calendar của người dùng vì chưa có kết nối Calendar được xác nhận.

## Mốc gửi nhóm

| Tuần | Khoảng ngày | Hạn nghiệm thu | Kết quả chính |
|---|---|---|---|
| 1 | 26/10–01/11 | 01/11 | Đặc tả, contracts, spike Windows/DNS; core/UI shell |
| 2 | 02/11–08/11 | 08/11 | Pairing/policy thật; engine/counter; bắt đầu service |
| 3 | 09/11–15/11 | 15/11 | Agent/Tray thật, offline/reconnect, request/grant/command API-agent |
| 4 | 16/11–22/11 | 22/11 | UI E2E chính, báo cáo thật, DNS proxy |
| 5 | 23/11–29/11 | 25/11; 28/11; **29/11** | DNS adapter/UI; VM sạch và bản nghiệm thu; demo/bàn giao |

Quỹ giữ **136 giờ/người**, trung bình **27,2 giờ/người/tuần**. Tuần 5 hoàn tất
MVP, kiểm thử và sửa lỗi. SafeSearch/WebSocket là bắt buộc theo PDF; extension còn lại gồm 2FA,
PDF/CSV export, template tuổi, proxy HTTP(S)/WFP và installer đẹp.

## Tạo lại file sau khi sửa kế hoạch

Chạy từ root repo, Python 3, không cần cài thêm thư viện:

```powershell
python scripts/export_calendar.py
```

Nguồn ngày của 32 task là bảng trong `docs/PHAN_CONG.md`. Các mốc chung được khai báo
trong `scripts/export_calendar.py`; khi thay deadline dự án phải cập nhật cả hai nguồn.
UID của sự kiện ổn định theo mã việc, file dùng UTF-8/CRLF, sự kiện cả ngày có ngày kết thúc
exclusive theo [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545).

Hướng dẫn chính thức: [Google Calendar — Import events](https://support.google.com/calendar/answer/37118),
[Outlook — Import calendars](https://support.microsoft.com/en-us/office/import-or-subscribe-to-a-calendar-in-outlook-com-or-outlook-on-the-web-cff1429c-5af6-41ec-a5b4-74f2c278e98c).
