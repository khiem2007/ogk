# Quyền riêng tư và tối thiểu dữ liệu

Trạng thái: **bản thiết kế ban đầu; phải cập nhật theo schema thực tế trước khi nộp**.

OpenGuard Kids là công cụ đồng hành minh bạch, không phải phần mềm theo dõi lén. Không thu thập URL đầy đủ, tiêu đề cửa sổ, nội dung gõ phím, tin nhắn/email/tài liệu, ảnh chụp màn hình, webcam hoặc nội dung trang.

## Bảng dữ liệu

| Dữ liệu | Mục đích | Nơi lưu | Thời hạn | Người được xem |
|---|---|---|---|---|
| `device_id`, `child_id` | Gắn sự kiện/chính sách đúng thiết bị và hồ sơ | Server; cache agent | Khi thiết bị còn ghép; xóa khi phụ huynh xóa | Parent sở hữu, child-view của chính hồ sơ, admin có audit hợp pháp |
| Tên ứng dụng + SHA-256 executable | Nhận diện app, áp rule và tổng hợp thời lượng | Server + agent policy/cache | 90 ngày cho dữ liệu sử dụng; rule đến khi bị xóa | Parent, child-view cùng hồ sơ; agent đúng thiết bị |
| Tên miền cấp hai/category | Áp rule DNS và báo cáo tối thiểu | Server + agent | 90 ngày; không lưu URL/path/query history | Parent và child-view cùng hồ sơ |
| Thời lượng + timestamp UTC | Quota, báo cáo ngày/tuần, audit sai lệch | Server + checkpoint agent | 90 ngày; auto-delete | Parent và child-view cùng hồ sơ |
| Event type + `policy_id`/reason | Giải thích block, dedup và audit | Server + outbox agent | 90 ngày | Parent, child-view; admin theo quyền |
| Yêu cầu của trẻ và phản hồi | Xin thêm giờ/báo chặn nhầm | Server + queue agent | 90 ngày | Parent và child-view liên quan |
| Audit before/after đã redaction + actor/IP | Truy trách nhiệm thay đổi chính sách | Server | 90 ngày tối thiểu theo đề bài; thay đổi phải được tài liệu hóa | Parent và child-view liên quan; admin |
| Device token/refresh secret | Xác thực thiết bị | Hash/encrypted server; DPAPI/ACL agent | Đến revoke/gỡ thiết bị | Không hiển thị; chỉ thành phần xác thực |
| DNS gốc của adapter | Khôi phục DHCP/static khi lỗi/gỡ | Agent ProgramData | Đến khi gỡ/khôi phục xong | LocalSystem/Administrators |

Envelope kỹ thuật như UUID event, boot ID và sequence chỉ phục vụ chống trùng/khôi phục; không được dùng để thêm dữ liệu hành vi ngoài bảng trên.

## Quyền và xóa dữ liệu

- Parent chỉ truy cập trẻ/thiết bị thuộc sở hữu; kiểm tra ownership ở tầng query.
- Child-view xem cùng báo cáo và audit của chính mình, nhưng không sửa chính sách.
- Nút “Xóa toàn bộ dữ liệu của con tôi” phải xóa server và cache/outbox liên quan trên agent; kết quả có audit không chứa dữ liệu đã xóa.
- Tác vụ retention chạy tự động và có test bằng dữ liệu hết hạn.

## Phiên bản dành cho trẻ

Ứng dụng ghi lại em dùng ứng dụng hoặc nhóm trang web nào, vào lúc nào và trong bao lâu để tính thời gian và giải thích luật. Ứng dụng **không đọc** điều em gõ, tin nhắn, bài tập, URL đầy đủ và không chụp màn hình. Em được xem báo cáo giống phụ huynh, xem ai đã đổi luật và có thể xin thêm giờ hoặc báo trang bị chặn nhầm.
