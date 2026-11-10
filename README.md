# OpenGuard Kids (OGK)

Đồ án quản lý thời gian và hoạt động sử dụng máy tính của trẻ trên Windows, có cấu hình từ xa và hoạt động khi mất mạng.

**Trạng thái: đã có B01 spike và B02 core/tests của TV2; ứng dụng end-to-end chưa chạy được.**
Không coi tài liệu, spike hay CI cấu trúc là đã hoàn thành các tính năng F1–F5.

## Tài liệu bắt đầu

- [Đề bài chính thức ngày 05/11/2026](docs/DoAn_UD_QL_SD_PC_TreEm.pdf) và [ma trận truy vết yêu cầu](docs/REQUIREMENTS_TRACEABILITY.md).
- [Bảng phân công chi tiết, kiến thức cần học và lịch 5 tuần](docs/PHAN_CONG.md).
- [Nội dung cốt lõi tuần 1 dành cho Thành viên 2](docs/TV2_TUAN_1_COT_LOI.md) — kiến thức, bài thực hành và checklist B01–B02.
- [Kế hoạch và bộ prompt hiện hành](docs/PROJECT_BRIEF.md); [bản nguồn ban đầu](docs/reference/Ke-hoach-va-prompt-OGK.original.md).
- [Lịch Calendar để gửi nhóm](docs/calendar/README.md) — 26/10–29/11/2026, file `.ics` toàn nhóm và từng thành viên.
- [Mục lục 9 ảnh tham chiếu](docs/reference/README.md).
- [SRS](docs/SRS.md), [ERD](docs/ERD.md), [API v1](docs/API.md), [kiến trúc](docs/ARCHITECTURE.md), [các điểm cần chốt](docs/DECISIONS.md), [hợp đồng tích hợp](contracts/README.md).
- [Quyền riêng tư](docs/PRIVACY.md), [threat model](docs/THREATMODEL.md), [khai báo AI](docs/AI_USAGE.md), [khung báo cáo kỹ thuật mạng](docs/BaoCaoKyThuatMang.md).
- [Quy trình làm việc nhóm](CONTRIBUTING.md), [tiến độ thực tế](docs/PROGRESS.md), [checklist Windows](tests/manual/WINDOWS_CHECKLIST.md).

## Cấu trúc

```text
ogk/
  server/                 # app/{api,auth,models,schemas,services,db}, migrations
  dashboard/              # src/{api,components,pages,styles}, public
  agent/
    core/                 # policy, counter, clock, sync, outbox
    windows/              # service, helper, IPC, process, adapter DNS
    tray/                 # PySide6
    dns/                  # resolver và rules
  contracts/              # schemas và fixtures dùng chung
  tests/                  # unit, integration, e2e, manual
  scripts/                # bootstrap/seed/install/uninstall/backup; spikes
  deploy/                 # kế hoạch compose/reverse proxy; env example
  docs/                   # brief, phân công, kiến trúc, ADR, ảnh, evidence
  .github/                # mẫu issue/PR và kiểm tra cấu trúc
```

## Kiểm tra bộ khung

Chạy từ thư mục gốc repo, với Python 3:

```powershell
python scripts/check_structure.py
```

Lệnh chỉ kiểm tra tài liệu và cấu trúc; không cài service, không thay DNS, không chạy app.
Khi bắt đầu milestone triển khai, chủ module phải chọn và kiểm tra phiên bản dependency,
commit lockfile, thêm lệnh setup/run/test/build vào README module. Hiện chưa có dependency runtime.

## Phạm vi triển khai

FastAPI + SQLAlchemy + Alembic, SQLite WAL; React/TypeScript/Vite; agent Python + pywin32/psutil;
Tray PySide6; DNS loopback UDP/TCP. Agent chủ động kết nối HTTPS ra server.
MVP gồm auth/pairing, policy/quota, foreground usage, app block, request/grant, command,
offline outbox, report/audit, DNS có restore, SafeSearch qua DNS và WebSocket cho lệnh khẩn dưới 5 giây.
2FA, template tuổi, CSV và proxy HTTP(S)/WFP là mở rộng.

Kế hoạch nhóm 3 người, **5 tuần từ 26/10 đến hết 29/11/2026**, trung bình **27,2 giờ/người/tuần** (136 giờ/người); tên thành viên chưa được cung cấp nên dùng TV1–TV3.
Demo một máy, một phiên trẻ standard user; quota theo từng thiết bị.
Không thu URL đầy đủ, tiêu đề cửa sổ, screenshot/keylogger/tin nhắn; không có chế độ ẩn hoặc shell từ xa; không hứa chặn tuyệt đối admin/DoH/VPN.
