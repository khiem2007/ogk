# OpenGuard Kids (OGK)

Đồ án quản lý thời gian và hoạt động sử dụng máy tính của trẻ trên Windows, có cấu hình từ xa và hoạt động khi mất mạng.

**Trạng thái: bộ khung repository và kế hoạch triển khai. Chưa có ứng dụng chạy được.**
Không coi việc có thư mục hay CI kiểm tra cấu trúc là đã hoàn thành tính năng.

## Tài liệu bắt đầu

- [Bảng phân công chi tiết, kiến thức cần học và lịch 8 tuần](docs/PHAN_CONG.md).
- [Kế hoạch và bộ prompt gốc](docs/PROJECT_BRIEF.md) — giữ nguyên tài liệu người dùng.
- [Mục lục 9 ảnh tham chiếu](docs/reference/README.md).
- [Kiến trúc](docs/ARCHITECTURE.md), [các điểm cần chốt](docs/DECISIONS.md), [hợp đồng tích hợp](contracts/README.md).
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
offline outbox, report/audit và DNS có restore. WebSocket, SafeSearch, 2FA, template tuổi và CSV là mở rộng.

Giả định nhóm 3 người, 8 tuần, 15–20 giờ/người/tuần; tên thành viên chưa được cung cấp nên dùng TV1–TV3.
Demo một máy, một phiên trẻ standard user; quota theo từng thiết bị.
Không thu screenshot/keylogger/tin nhắn, không shell từ xa; không hứa chặn tuyệt đối admin/DoH/VPN.
