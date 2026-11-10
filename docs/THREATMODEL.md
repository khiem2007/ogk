# Threat model OpenGuard Kids

Trạng thái: **bản STRIDE ban đầu; cần cập nhật theo implementation và checklist ASVS trước release**.

Tài sản cần bảo vệ: danh tính gia đình/trẻ, device secret, policy, usage metadata, audit log, lệnh khẩn, DNS gốc và ranh giới quyền giữa parent/child/admin/LocalSystem.

| ID | STRIDE | Mối đe dọa | Tác nhân | Kiểm soát dự kiến | Bằng chứng cần có |
|---|---|---|---|---|---|
| TM01 | Spoofing | Client giả agent gửi event/poll command cho device khác | Người ngoài | Token 15 phút + refresh gắn device, pin certificate, revoke, ownership | API integration hai device |
| TM02 | Spoofing/EoP | Trẻ giả Tray/helper hoặc khai SID trong payload | Trẻ là attacker | Named Pipe DACL, xác minh token/SID/session phía server, bounds | VM client SID sai bị deny |
| TM03 | Tampering | Policy cache bị sửa để nới luật | Trẻ/local process | Version + HMAC/chữ ký, ACL ProgramData, atomic apply, giữ bản hợp lệ trước | Test policy sửa byte bị reject |
| TM04 | Tampering/Replay | Replay command/grant/event làm cộng giờ hoặc đếm đôi | Trẻ/mạng lỗi | UUID/idempotency, expiry, intent/result bền vững, ACK sau commit | Retry/crash/lost ACK test |
| TM05 | Repudiation | Parent/admin phủ nhận đã đổi luật | User hợp lệ | Audit actor/time/IP/before/after, redaction, append semantics | Query audit + child-view |
| TM06 | Information disclosure | IDOR xem dữ liệu trẻ của gia đình khác | Parent khác | Ownership ở query, role parent/child-view/admin, pagination | Hai gia đình test chéo |
| TM07 | Information disclosure | Thu thập quá mức biến sản phẩm thành stalkerware | Người vận hành/người lớn lạm dụng | Không chế độ ẩn; tray bắt buộc; schema tối thiểu; không title/URL/keylog/screenshot; quyền trẻ xem | Privacy schema review |
| TM08 | Denial of service | Kill Tray/agent hoặc làm đầy outbox | Trẻ là attacker/lỗi máy | SCM recovery, bounded queue/payload, backoff, degraded rõ ràng | M5 kill/recovery test |
| TM09 | EoP | Child Standard User sửa config/DNS/service | Trẻ là attacker | ProgramData ACL SYSTEM/Admin; service ACL; adapter preflight/rollback | VM ACL + uninstall test |
| TM10 | Spoofing/Tampering | MITM thay policy/lệnh hoặc lấy token | Mạng LAN/VPS | TLS 1.2+, certificate pinning, token rotation, không disable verify | Lab CA/pin mismatch test |
| TM11 | Bypass | DoH/DoT/VPN/IP trực tiếp/Safe Mode/USB/account khác | Trẻ là attacker | SafeSearch + endpoint list/browser policy khi phù hợp; phát hiện/nêu giới hạn; standard user/BIOS ngoài scope rõ ràng | M3 ít nhất 7 ca thực tế |
| TM12 | Safety | Rule chặn nhầm trường học/111/cứu hộ | Sai cấu hình/dataset | Protected allowlist ưu tiên cao, dataset giáo dục, 0 false positive trên 20 miền | DNS acceptance set |

## Checklist ASVS rút gọn

- [ ] Mọi API ghi có CSRF; cookie HttpOnly/Secure/SameSite=Lax, session 12 giờ và logout server-side.
- [ ] Password Argon2id/scrypt, ≥10 ký tự; 5 lần sai khóa 15 phút; rate limit theo IP.
- [ ] Mọi query theo `owner_id`/scope; không dựa vào việc ẩn nút UI.
- [ ] Secret không log/hardcode; trường nhạy cảm AES-GCM, key env/DPAPI.
- [ ] Payload/event/IPC có schema, allowlist, giới hạn kích thước và timestamp/replay guard.
- [ ] Policy integrity, TLS pinning và token revoke có negative test.
- [ ] Không chế độ ẩn; nếu không thể hiện tray icon thì agent tự dừng an toàn và ghi lỗi tối thiểu.
- [ ] Privacy/retention/delete-all được kiểm thử trên server và agent cache.
