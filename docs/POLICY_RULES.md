# Quy tắc policy — OpenGuard Kids (OGK)

**Trạng thái:** quy tắc nghiệp vụ đề xuất theo PROJECT_BRIEF; chưa có policy engine/validator. Các rule domain schedule cần được phản ánh vào schema policy trước khi triển khai.

## 1. Thời gian và interval

- Lưu timestamp UTC; diễn giải lịch/ngày quota theo timezone IANA của thiết bị, mặc định `Asia/Ho_Chi_Minh`.
- Schedule dùng khoảng nửa mở `[start,end)`: tại `start` rule bắt đầu, tại `end` rule không còn áp dụng.
- `day_of_week`: `0=Monday` đến `6=Sunday`, cùng quy ước schema v1.
- MVP không nhận khung giờ qua nửa đêm; phụ huynh phải tách thành hai khung. Từ chối khung rỗng, sai thứ tự hoặc overlap.
- Tách usage interval tại local midnight và policy transition. Dùng monotonic clock trong một boot; không bù gap mù do sleep, crash hay thiếu telemetry.

## 2. Điều kiện tính usage

| Điều kiện | Cộng machine usage? | Gán app usage? |
|---|---:|---|
| Đúng child SID, session active, unlocked, không sleep, idle dưới ngưỡng và telemetry mới | Có | Có, tối đa một foreground executable trong interval. |
| Idle bằng/vượt ngưỡng | Không | Không. |
| Session disconnected, locked hoặc sleeping | Không | Không. |
| Helper mất/stale, SID/session không xác thực hoặc trạng thái không rõ | Không khẳng định là measured; ghi telemetry gap/degraded | Không gán app. |
| Parent/admin session hoặc SID khác trẻ | Không | Không. |

App usage là tập con machine usage; không cộng tiến trình chạy nền. Degraded estimate chỉ được dùng nếu có nguồn độc lập được kiểm chứng và phải gắn nhãn riêng, không trộn với measured usage.

## 3. Precedence cho thời gian và app

| Ưu tiên | Điều kiện | Quyết định |
|---:|---|---|
| 1 | Manual lock đang hiệu lực | Deny `MANUAL_LOCK`; chỉ command hợp lệ của phụ huynh clear được. |
| 2 | App bị block tường minh, không có exception còn hạn đúng app/device | Deny `APP_BLOCKED`. |
| 3 | App block có exception còn hạn, đúng app/device | Bỏ qua riêng app block đó; vẫn đánh giá quota tổng và các gate khác. |
| 4 | Ngoài schedule, không có time exemption hợp lệ | Deny `OUTSIDE_SCHEDULE`. |
| 5 | Total daily quota hết, không có exemption hợp lệ | Deny `DAILY_QUOTA_EXCEEDED`. |
| 6 | Category quota hết, không có exemption hợp lệ | Deny `CATEGORY_QUOTA_EXCEEDED`. |
| 7 | Không vướng gate nào | Allow `ALLOWED`. |

### Scope ngoại lệ

| Grant | Hiệu lực | Không được phép |
|---|---|---|
| Xin thêm thời gian | Tăng total quota cho đúng device và local date. | Không tự mở schedule ngoài giờ; không gỡ app/domain block; category quota vẫn áp dụng. |
| Xin mở app | Bypass đúng app block được duyệt đến `expires_at`. | Không vượt manual lock hoặc total quota; không mở app khác. |
| Miễn giới hạn 15 phút | Bỏ schedule/time quota trong 900 giây tính từ lúc agent áp dụng. | Không bỏ manual lock, app block hoặc domain block; retry không kéo dài expiry. |
| Miễn đến hết hôm nay | Bỏ schedule/time quota đến local midnight kế tiếp theo device timezone. | Không bỏ manual lock, app block hoặc domain block; không hàm ý trẻ phải nghỉ. |

Mỗi grant gắn ID cố định, device, scope và thời hạn. Lệnh quá hạn không thực thi muộn. Parent approve/reject một request chỉ được chuyển trạng thái pending một lần.

## 4. Domain filtering truth table

Chuẩn hóa domain bằng IDNA ASCII, lowercase và bỏ dấu chấm cuối. Rule `example.test` khớp đúng domain và subdomain có ranh giới label; không khớp `badexample.test`.

| Hard block match | Explicit allow match | Category result | Mode | Kết quả |
|---|---|---|---|---|
| Có | Bất kỳ | Bất kỳ | Bất kỳ | Block; hard block luôn thắng. |
| Không | Có | Bất kỳ | Blocklist | Allow, trừ giới hạn schedule được cấu hình riêng. |
| Không | Không | Category block | Blocklist | Block. |
| Không | Không | Category allow | Allow. |
| Không | Không | Không match | Blocklist | Allow theo mặc định. |
| Không | Có | Bất kỳ | Allowlist | Allow trong schedule được cấu hình. |
| Không | Không | Category allow | Allowlist | Allow trong schedule được cấu hình. |
| Không | Không | Category block/không match | Allowlist | Block theo mặc định. |

Nếu một category/domain được đánh dấu “Hạn chế”, chỉ phân giải trong web schedule tương ứng; DNS không đo thời gian người dùng ở trên trang. DoH, VPN, cache DNS và connection đã mở có thể vượt/trì hoãn rule. Không giải mã HTTPS, không lưu full URL/query history. Khi chưa enrollment/policy, không tự đổi DNS hoặc bật chặn.

## 5. Decision contract

Policy engine trả một kết quả thống nhất gồm `allowed`, `reason_code`, `rule_id`, `remaining_seconds` và `next_transition_at`. Reason code ổn định tối thiểu: `MANUAL_LOCK`, `APP_BLOCKED`, `DOMAIN_BLOCKED`, `OUTSIDE_SCHEDULE`, `DAILY_QUOTA_EXCEEDED`, `CATEGORY_QUOTA_EXCEEDED`, `ALLOWED`, `DEGRADED_TELEMETRY`, `NO_POLICY`.

`remaining_seconds` là giá trị do engine tính theo cùng policy/counter snapshot; dashboard và Tray không tự tính lại theo công thức riêng. Event phải được persist vào outbox trước khi sync; server dedup theo `(device_id,event_id)` và chỉ ACK sau commit.

## 6. Các điểm cần review trước khi triển khai

- TV2 xác nhận precedence, category quota, timezone/day boundary, grant expiry và cách biểu diễn Decision trong core.
- TV1 xác nhận policy/event schema, semantics domain schedule, ownership và event dedup.
- TV3 xác nhận reason/status đủ để trình bày rõ trạng thái cho phụ huynh và trẻ.
- Đây là tài liệu đặc tả; chưa phải bằng chứng policy engine, DNS proxy, Windows enforcement hoặc các test tương ứng đã tồn tại.
