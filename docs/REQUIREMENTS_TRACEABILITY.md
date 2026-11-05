# Truy vết yêu cầu chính thức OpenGuard Kids

Nguồn yêu cầu chính thức: [DoAn_UD_QL_SD_PC_TreEm.pdf](DoAn_UD_QL_SD_PC_TreEm.pdf), 12 trang, xuất ngày 05/11/2026. Khi tài liệu kế hoạch cũ mâu thuẫn với PDF, yêu cầu bắt buộc trong PDF được ưu tiên; lịch 5 tuần 26/10–29/11/2026 vẫn là kế hoạch nội bộ đã được người dùng chốt để hoàn thành sớm hơn thời lượng môn học 6 tuần.

Trạng thái trong bảng là trạng thái truy vết, không phải tuyên bố tính năng đã chạy.

## Nguyên tắc bắt buộc và điều cấm

| Mã | Yêu cầu chính thức | Nơi hiện thực/kiểm chứng | Chủ trì | Trạng thái |
|---|---|---|---|---|
| NT1 | Tray luôn hiện khi agent chạy; thông báo khởi động; trang giải thích cho trẻ cấp 1 | `agent/tray`, C05, E2E | TV3 + TV2 | Chưa triển khai |
| NT2 | Chỉ tên app, tên miền cấp hai, thời lượng, timestamp; không URL/title/keylog/screenshot | `PRIVACY.md`, contracts, A01/A06/B05 | TV1 + TV2 | Đã chốt phạm vi; cần contract/test |
| NT3 | Xin thêm giờ và báo chặn nhầm, có phản hồi | A07/B07/C05–C06 | Cả nhóm | Chưa triển khai |
| NT4 | Mọi block phải hiện lý do và người đặt luật | Decision/reason code, Tray, C05 | TV2 + TV3 | Model lý do đã có; UI chưa có |
| NT5 | Trẻ xem cùng báo cáo và audit thay đổi luật | A09/C07 + child-view | TV1 + TV3 | Chưa triển khai |
| NT6 | Miễn chặn vĩnh viễn cổng trường, 111, cứu hộ; khóa không chặn chức năng khẩn cấp OS | policy protected allowlist, B03/A10/C08 | Cả nhóm | Chưa thiết kế contract |
| Cấm | Không đọc nội dung; không ẩn/rootkit/chống gỡ kiểu mã độc; không gửi bên thứ ba; không thử trên trẻ/máy người khác khi chưa đồng ý | `PRIVACY.md`, `THREATMODEL.md`, review release | Cả nhóm | Đã ghi quy tắc |

## Chức năng và bảo mật

| ID | Yêu cầu/tiêu chí chính | Task/test chịu trách nhiệm | Chênh lệch cần xử lý |
|---|---|---|---|
| F1.1 | Quota ngày thường/cuối tuần; quota 3 phút khóa đúng hạn | B03–B04, C04, test clock/VM | B03 cần model loại ngày |
| F1.2 | Lịch 7×48, độ phân giải 30 phút; khóa trong 5 giây | B03, C04, manual VM | Thêm acceptance chính thức |
| F1.3 | Không tính locked hoặc idle >5 phút; sai số ±30 giây/giờ | B04, M4 | Cần phép đo tối thiểu 30 mẫu khi áp dụng |
| F1.4 | Cảnh báo 10/5/1 phút và grace 60 giây | B03/C05 | Kế hoạch cũ chỉ có 5/1 phút |
| F1.5 | Lùi đồng hồ 3 giờ không tăng quota, có event | B04/B06, M6 | FakeClock có nền tảng; chưa có counter/event |
| F2.1 | Nhận diện app bằng process name + SHA-256; block có giải thích | B05/C05 | Bổ sung hash vào app contract |
| F2.2 | DNS proxy 127.0.0.1:53, domain + subdomain; ≥95%/50 miền, 0 false positive/20 miền giáo dục | A10/B09, T13–T15, M1 | Cần bộ dữ liệu an toàn và kết quả đo |
| F2.3 | 6 nhóm và bảng phân loại ≥200 mục, mặc định trẻ 6–11 tuổi | A10/C08 | Bắt buộc, không còn là fixture nhỏ |
| F2.4 | SafeSearch bằng DNS, kiểm bằng nslookup + browser | A10/B09/C08 | Bắt buộc, không còn là extension |
| F2.5 | DoH/DoT/VPN/DNS thủ công là bypass cần thử và nêu giới hạn | M3, A10/B09 | DoH và đổi DNS là “nên có”; M3 vẫn bắt buộc phân tích |
| F3.1 | Event privacy schema và allowlist type | A01/A06/B06 | Envelope kỹ thuật được phép, payload không mở rộng dữ liệu cá nhân |
| F3.2 | Báo cáo ngày/tuần, top 10 app/domain, block, request; trẻ xem cùng dữ liệu | A09/C07 | Cần role child-view và audit view |
| F3.3 | Retention 90 ngày, auto-delete, xóa toàn bộ server + agent cache | A09/B06/C07 | Kế hoạch cũ 30/90 ngày phải sửa thành 90 ngày dữ liệu trẻ |
| F4.1 | Enrollment 8 ký tự/10 phút; heartbeat 60 giây; policy trong 60 giây; lệnh khẩn dưới 5 giây qua WebSocket | A04/A06/A08/B06/B07 | WebSocket bắt buộc cho lệnh khẩn; polling chỉ fallback |
| F4.2 | Policy version + HMAC/chữ ký, agent từ chối bản sửa | A05/B06 | Chưa triển khai |
| F4.3 | Audit ai/lúc nào/IP/before/after; trẻ được xem | A08/A09/C07 | Chưa triển khai |
| F5.1 | Argon2id/scrypt, mật khẩu ≥10, khóa 15 phút sau 5 lỗi, rate limit IP | A03 | Cần test auth |
| F5.2 | Cookie HttpOnly/Secure/SameSite=Lax, 12 giờ, server logout, CSRF | A03 | Đã có trong kế hoạch, bổ sung ngưỡng |
| F5.3 | TLS 1.2+, certificate pinning; access token 15 phút + refresh/revoke | A04/A11/B06 | Chưa triển khai |
| F5.4 | AES-GCM cho trường nhạy cảm; khóa env/DPAPI; hash device secret | A02/A04/B06 | Chưa triển khai |
| F5.5 | Role parent/child-view/admin và ownership chống IDOR | A03/A09/C07 | Kế hoạch cũ thiếu child-view/admin rõ ràng |
| F5.6 | Child là Standard User; ProgramData chỉ SYSTEM/Admin được ghi | B01/B10 | Spike mới kiểm tra một phần; VM hai tài khoản chưa chạy |
| F5.7 | STRIDE ≥8 gồm child attacker và stalkerware; không chế độ ẩn, không có icon thì agent tự dừng | `THREATMODEL.md`, B05/C05/A12 | Đã tạo bản nháp threat model; cần review/test |

## Phụ lục kỹ thuật mạng bắt buộc

| Mục | Bằng chứng cần có | Chủ trì |
|---|---|---|
| M1 | Sơ đồ browser → stub resolver → DNS proxy → rule → response; Wireshark/tcpdump | TV1 + TV2 |
| M2 | So sánh hosts/DNS proxy/HTTP(S)/WFP theo 5 tiêu chí | TV1, TV2 review |
| M3 | Ít nhất 7 bypass, kết quả thử thực tế và đối phó/rủi ro chấp nhận | TV2, cả nhóm review |
| M4 | CPU/RAM, DNS p50/p95 có/không agent, policy latency; mỗi phép đo ≥30 mẫu | TV2 + TV1 |
| M5 | Mất mạng, server down, agent bị kill: expected/actual/recovery time | TV2 |
| M6 | Monotonic, đối chiếu server mỗi heartbeat, ngưỡng cảnh báo clock skew | TV2 + TV1 |

Khung soạn thảo nằm tại [BaoCaoKyThuatMang.md](BaoCaoKyThuatMang.md). Bản nộp cuối phải xuất thành `docs/BaoCaoKyThuatMang.pdf`.

## Sản phẩm phải nộp

| Đầu ra | Điều kiện |
|---|---|
| `/agent`, `/server`, `/dashboard` | Chạy trên máy sạch; README cài trong 15 phút; dashboard dùng được trên mobile |
| `/tests` | Tối thiểu 15 unit test + 5 kịch bản integration, kèm ảnh kết quả |
| `docs/BaoCao.docx` | 20–30 trang, phân công và % đóng góp |
| `docs/BaoCaoKyThuatMang.pdf` | Đủ M1–M6 |
| `docs/PRIVACY.md` | Bảng dữ liệu/mục đích/retention/người xem + bản cho trẻ |
| `docs/THREATMODEL.md` | STRIDE + ASVS, tối thiểu 8 mối đe dọa |
| `docs/AI_USAGE.md` | Công cụ, phần việc, cách kiểm chứng |
| `demo/video.mp4` | 5–7 phút, phụ đề hoặc thuyết minh tiếng Việt |

## Bộ dữ liệu an toàn

Tối thiểu theo phụ lục PDF: 20 giáo dục, 10 giải trí phù hợp tuổi, 8 mạng xã hội, 7 trò chơi, 5 endpoint DoH, 10 miền mô phỏng cần chặn. Đây là bộ nghiệm thu con; bảng phân loại sản phẩm vẫn phải đạt tối thiểu 200 mục. Không dùng hoặc truy cập nội dung người lớn thật.
