# Phân tích UI/UX, Luồng sử dụng và Kế hoạch kiểm thử (TV3 — C01)

**Mã công việc:** TV3-C01  
**Nguồn chuẩn ưu tiên:** [DoAn_UD_QL_SD_PC_TreEm.pdf](DoAn_UD_QL_SD_PC_TreEm.pdf) (12 trang, 05/11/2026)  
**Tài liệu đối chiếu:** [PROJECT_BRIEF.md](PROJECT_BRIEF.md), [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md), [SRS.md](SRS.md), [API.md](API.md), [POLICY_RULES.md](POLICY_RULES.md), [9 ảnh prototype](reference/README.md).

---

## 1. Mục tiêu và nguyên tắc thiết kế UI/UX

OpenGuard Kids (OGK — *Người Bạn Đồng Hành*) được thiết kế theo triết lý **"Công cụ đồng hành, không phải phần mềm theo dõi lén"**. Mọi màn hình Dashboard và Tray UI bắt buộc thể hiện trực tiếp 6 nguyên tắc NT1–NT6:

1. **NT1 — Trẻ biết mình đang được hỗ trợ:** Tray icon luôn hiển thị khi agent chạy (nếu hệ thống không hiển thị được khay thì agent tự dừng); có thông báo khởi động; có màn hình *"Phần mềm này làm gì?"* / *"Ứng dụng này ghi nhận gì về em"* viết bằng ngôn ngữ học sinh cấp 1.
2. **NT2 — Tối thiểu dữ liệu:** UI/Tray không bao giờ thu thập hoặc hiển thị URL đầy đủ, tiêu đề cửa sổ, ảnh chụp màn hình hay nội dung gõ phím; Tray tuyệt đối không lưu `device_token`.
3. **NT3 — Trẻ có tiếng nói:** Trẻ có nút *"Xin thêm giờ"*, *"Xin mở ứng dụng"*, *"Em nghĩ trang này bị chặn nhầm"* kèm lý do; khi mất mạng vẫn cho tạo vào hàng đợi cục bộ và ghi nhãn rõ **"Chưa gửi (đang chờ mạng)"**.
4. **NT4 — Mọi hành động phải giải thích được:** Mọi thông báo chặn ứng dụng hoặc trang web phải nêu lý do cụ thể (`ReasonCode`) và người đặt luật (phụ huynh), không im lặng hay giả vờ lỗi mạng.
5. **NT5 — Minh bạch hai chiều:** Vai trò `child-view` cho phép trẻ xem **cùng bộ dữ liệu báo cáo** với phụ huynh (dưới giao diện thân thiện) và xem **nhật ký kiểm toán thay đổi luật** (`audit_logs`), nhưng không có quyền sửa chính sách.
6. **NT6 — An toàn có ưu tiên tuyệt đối:** Giao diện Lọc web khóa cố định danh sách miễn chặn vĩnh viễn (`protected allowlist`: cổng trường học, Tổng đài 111, cứu hộ khẩn cấp) để phụ huynh không vô tình chặn nhầm.

---

## 2. Đối chiếu 9 ảnh prototype và yêu cầu bắt buộc từ PDF

| Ảnh tham chiếu | Màn hình/Nội dung trong ảnh | Ánh xạ vào sản phẩm thực tế | Điểm giữ / điều chỉnh so với PDF chính thức |
|---|---|---|---|
| `6ec7ff71-...jpg`, `ae963af9-...jpg`, `a0426d49-...jpg` | Kiến trúc Service / Tray / Server / Dashboard | Kiến trúc 3 phần | Giữ tách biệt Service (LocalSystem) ↔ Tray (Session user) ↔ Server; không suy diễn phần chữ mờ |
| `9eeed60b-...jpg` | Tổng quan Bé An: 3 card chỉ số, bar chart tuần | `OverviewPage` (`C02`/`C07`) | Giữ bảng màu sáng xanh lá nhạt, sidebar trái, card bo góc; **chỉ seed Bé An trong chế độ Demo có nhãn**, không hard-code vào production |
| `3a51098e-...jpg` | Tổng quan + biểu đồ tuần + khung giờ hôm nay | `OverviewPage` + `AppsSchedulePage` (`C04`) | Phần dưới ảnh bị che → thiết kế ma trận lịch `7×48` slot 30 phút `[start, end)` theo `POLICY_RULES.md`, cấm khung giờ qua nửa đêm |
| `c12c5434-...jpg` | Lọc web theo danh mục, công tắc SafeSearch & YouTube | `WebFilterPage` (`C08`) | PDF nâng **6 nhóm + bảng ≥ 200 mục + SafeSearch DNS** thành bắt buộc; SafeSearch **chỉ báo "Đã bật"** khi có xác nhận `nslookup`/browser pass; YouTube Restricted là mở rộng |
| `0449ccea-...jpg` | Yêu cầu từ con: xin thêm 20 phút, xin mở app | `RequestsPage` (`C06`) | Hiển thị rõ `scope`, `expires_at`, trạng thái atomic `pending → approved \| rejected \| expired` |
| `12bd39b5-...jpg` | Điều khiển từ xa: nghỉ 15p, tạm dừng hôm nay, khóa ngay | `CommandsPage` (`C06`) | Tách bạch `queued → delivered → executed \| failed \| expired`; **không toast "thành công" trước ACK `executed`** |
| `34ee30b4-...jpg` | Hồ sơ & Quy tắc theo độ tuổi + Đồng thuận đã ghi nhận | `ProfilesTransparencyPage` (`C03`/`C10`) | Bổ sung **Xem trước (preview)** trước khi áp dụng template; **không gắn nhãn "Đã bật 2FA"** như ảnh mờ vì 2FA là phần mở rộng chưa làm |

---

## 3. Luồng người dùng chính (User Flows)

### 3.1. Luồng Phụ huynh trên Dashboard (`dashboard/`)
1. **Đăng nhập & xác thực:** `Login` (email + mật khẩu ≥ 10 ký tự; lỗi khóa 15 phút sau 5 lần sai; session cookie + CSRF token cho mọi thao tác ghi; hỗ trợ chuyển sang `child-view` ở chế độ xem cho trẻ/demo).
2. **Thiết lập hồ sơ trẻ & ghép thiết bị:** Tạo/chọn trẻ → chọn hoặc thêm thiết bị → tạo mã ghép 8 ký tự (hết hạn sau 10 phút) → xem trạng thái kết nối (`online` / `offline` / `degraded`), `last_seen_at`, `server_version` vs `applied_policy_version` → hoặc thu hồi (`revoke`) thiết bị.
3. **Cấu hình lịch & ứng dụng:** Chọn thứ/slot 30 phút trên ma trận `7×48` → kiểm tra client-side không trùng, không rỗng, không qua nửa đêm → đặt hạn mức ngày thường/cuối tuần và ngân sách nhóm app → xem preview → gửi `PUT /devices/{id}/policy` kèm `expected_version`. Nếu gặp `409 VERSION_CONFLICT`, giữ bản hiện tại và yêu cầu tải lại thay vì ghi đè mù.
4. **Cấu hình lọc web:** Chọn chế độ `blocklist` / `allowlist`, cấu hình 6 nhóm nội dung, tìm kiếm/gán trong bảng phân loại ≥ 200 mục, quản lý `hard_block` / `explicit_allow`, giữ nguyên `protected allowlist`, kiểm tra trạng thái xác minh SafeSearch và đọc giải thích giới hạn DNS/DoH.
5. **Duyệt yêu cầu & gửi lệnh khẩn:** Xem yêu cầu chờ duyệt → kiểm tra phạm vi (`scope`) và thời hạn (`expiry`) → bấm **Duyệt** hoặc **Từ chối** một lần. Gửi lệnh (`Khóa ngay`, `Hủy khóa`, `Miễn 15 phút`, `Miễn hết hôm nay`) → theo dõi trạng thái chuyển từ `queued` → `delivered` → `executed` / `failed` / `expired`.
6. **Theo dõi báo cáo, Audit & Xóa dữ liệu:** Xem thời lượng ngày/tuần (có phân biệt `measured` vs `estimated/degraded`), Top 10 app/domain, số lần chặn, bảng Audit log (ai/lúc nào/IP/before/after đã lọc bí mật), hoặc kích hoạt **"Xóa toàn bộ dữ liệu của con tôi"** và theo dõi trạng thái đồng bộ xóa server + agent cache.

### 3.2. Luồng Trẻ trên Tray UI (`agent/tray/`) & Child-view (`dashboard/`)
1. **Khởi động & minh bạch:** Khi phiên trẻ đăng nhập, Service bật Tray UI trong phiên user; Tray kiểm tra hệ thống hỗ trợ khay hệ thống (nếu không hiện được icon → phát tín hiệu dừng agent thay vì chạy ẩn), hiện thông báo khởi động công khai.
2. **Theo dõi thời gian & cảnh báo:** Hiển thị đồng hồ đếm ngược, tổng đã dùng/quota hôm nay, khung giờ tiếp theo, trạng thái kết nối. Phát cảnh báo lần lượt ở **10 phút**, **5 phút**, **1 phút** cuối và thông báo **grace 60 giây** lưu bài trước khi khóa phiên.
3. **Giải thích chặn & gửi yêu cầu:** Khi app/web bị chặn, hiển thị hộp thoại giải thích `ReasonCode` + tên người đặt luật. Trẻ bấm *"Xin thêm giờ"*, *"Xin mở ứng dụng"* hoặc *"Báo chặn nhầm"* → gửi qua IPC tới Service. Nếu đang mất mạng, hiển thị trong danh sách yêu cầu cục bộ với trạng thái **"Chưa gửi (đang chờ mạng)"**.
4. **Xem minh bạch & báo cáo chung:** Trẻ mở tab *"Phần mềm này làm gì?"* (ngôn ngữ cấp 1) hoặc tab *"Hôm nay em đã dùng gì"* / đăng nhập `child-view` trên web để xem cùng số liệu và nhật ký sửa luật với phụ huynh.

---

## 4. Ma trận truy vết TV3: Chức năng (F1–F5, NT1–NT6) & Kịch bản kiểm thử (T01–T23)

| Mã yêu cầu / Test ID | Trách nhiệm của TV3 (UI / Tray / E2E / Docs) | Cách kiểm chứng |
|---|---|---|
| **NT1** | Tray icon luôn hiện (tự dừng nếu không hiện icon), thông báo khởi động, trang *"Phần mềm này làm gì?"* cho trẻ cấp 1 | Unit test `test_tray_state.py` + PySide6 offscreen test + E2E tab Minh bạch |
| **NT2** | UI/Tray không nhận/gửi `window_title`, full URL, screenshot, keylog, hay `device_token` | Unit test IPC payload guard (`test_tray_state.py`) + review schema |
| **NT3** | Nút *"Xin thêm giờ"*, *"Mở app"*, *"Báo chặn nhầm"* trong Tray; màn hình duyệt + phản hồi ở Dashboard; nhãn *"Chưa gửi"* khi offline | `test_tray_state.py` + Playwright E2E luồng request → approve |
| **NT4** | Tray hiển thị lý do chặn theo `ReasonCode` tiếng Việt + người đặt luật | `test_tray_state.py` + `test_tray_ui.py` |
| **NT5** | Role `child-view` xem cùng báo cáo và audit thay đổi luật, ẩn/vô hiệu hóa thao tác sửa | Playwright E2E test `child-view` |
| **NT6** | Khóa cố định `protected allowlist` (trường học, 111, cứu hộ) trên màn hình Lọc web | Unit/E2E test không cho xóa hoặc override mục bảo vệ |
| **F1.1–F1.5** | UI ma trận `7×48`, chặn overlap/qua nửa đêm, quota ngày thường/cuối tuần, cảnh báo 10/5/1 phút & grace 60s trên Tray, hiển thị nhãn `clock_suspect` nếu có | Unit test validator + Playwright E2E + Tray state tests |
| **F2.1–F2.5** | Hiển thị `executable_name` + SHA-256 trên UI app, UI 6 nhóm + bảng phân loại ≥ 200 mục, công tắc SafeSearch chỉ báo bật sau xác nhận DNS, giải thích giới hạn DoH | Unit test `domainCatalog` + Playwright E2E `WebFilterPage` |
| **F3.1–F3.3** | Báo cáo ngày/tuần, Top 10 app/domain, số block, màn hình *"Hôm nay em đã dùng gì"*, nút *"Xóa toàn bộ dữ liệu"* có trạng thái đồng bộ | Playwright E2E `ReportsPage` + Tray summary tab |
| **F4.1–F4.3** | Pairing 8 ký tự/10 phút, phân biệt `server_version` vs `applied_version`, `queued/delivered/executed/failed/expired` không toast giả, bảng Audit chi tiết | Playwright E2E Pairing / Policy / Commands / Audit |
| **F5.1–F5.7** | Form Login (≥ 10 ký tự, thông báo lockout/rate limit), CSRF header ở API client, phân quyền `parent/child-view/admin` ở UI, chống XSS qua React escaping, checklist ASVS & STRIDE trong `THREATMODEL.md` | Unit test API client + Playwright E2E + Review `THREATMODEL.md` |
| **T01–T02** (phối hợp) | UI hiển thị lỗi rõ ràng khi mã pairing hết hạn/dùng lại hoặc không có quyền truy cập | Playwright E2E pairing error state |
| **T08–T11** (phối hợp) | UI phân biệt `queued`/`delivered`/`executed`/`expired`, không cho duyệt trùng grant, hiển thị trạng thái `offline`/`degraded` | Playwright E2E Commands & Requests |
| **T23** (phối hợp) | UI nút *"Xóa toàn bộ dữ liệu"* hiển thị tiến trình chờ/xác nhận xóa cả server & agent cache | Playwright E2E Delete-all flow |

---

## 5. Kế hoạch kiểm thử chi tiết của TV3

1. **Unit test Frontend (`dashboard/`):** Kiểm tra validator lịch `7×48` (empty, overlap, qua nửa đêm), tính toàn vẹn bảng phân loại ≥ 200 domain và đủ 6 nhóm, `protected allowlist` bất biến, xử lý error envelope chuẩn API v1.
2. **Unit test Tray & IPC (`tests/unit/test_tray_*.py`):**
   - Kiểm tra `ipc_message.schema.json` validation (đúng schema cho `telemetry.sample`, `request.submit`, `status.get`, `command.lock`, `command.result`).
   - Kiểm tra bất biến `tray_icon_available=False` → phát yêu cầu dừng an toàn (không chạy ẩn).
   - Kiểm tra queue yêu cầu khi offline gắn nhãn *"Chưa gửi"* và flush khi online.
   - Kiểm tra cảnh báo 10/5/1 phút và grace 60 giây.
   - Kiểm tra giao diện PySide6 thật dưới `QT_QPA_PLATFORM=offscreen`.
3. **E2E Web (`tests/e2e/` — Playwright):**
   - Luồng 1: Đăng nhập & kiểm tra validation mật khẩu < 10 ký tự.
   - Luồng 2: Chuyển đổi Trẻ / Thiết bị & tạo mã ghép nối + kiểm tra trạng thái mã hết hạn.
   - Luồng 3: Tạo lịch `7×48`, kiểm tra báo lỗi overlap & qua nửa đêm, lưu policy (`server_version` tăng), xử lý xung đột `409 VERSION_CONFLICT`.
   - Luồng 4: Duyệt yêu cầu của trẻ (`pending → approved`), kiểm tra không duyệt trùng.
   - Luồng 5: Điều khiển từ xa — xác minh không hiện thông báo *"thành công"* khi lệnh mới ở `queued` hoặc `delivered`; chỉ xác nhận hoàn tất khi nhận ACK `executed`; kiểm tra hiển thị `expired` / `failed`.
   - Luồng 6: Lọc web — tìm kiếm trong ≥ 200 mục / 6 nhóm, thử ghi đè `protected allowlist` bị khóa, kiểm tra cảnh báo SafeSearch chưa xác minh.
   - Luồng 7: Báo cáo + Audit + chuyển sang `child-view` (kiểm tra ẩn nút sửa) + nút xóa toàn bộ dữ liệu + banner lỗi mạng + kiểm tra giao diện mobile (`390×844`) và điều hướng bàn phím (`Tab`).

> **Giới hạn trung thực:** Toàn bộ test UI/E2E trong giai đoạn chờ backend A03–A10 của TV1 chạy với **Chế độ Demo / Fixture Adapter có nhãn công khai trên giao diện**; đây không phải bằng chứng nghiệm thu API server thật hoặc Windows VM của TV2.
