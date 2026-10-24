# Tiến độ thực tế

## 2026-10-24 — Khởi tạo bộ khung

- Đã đọc kế hoạch và xem 9 ảnh; giữ bản sao nguồn trong docs.
- Đã tạo cây thư mục theo đề xuất, README từng module, phân công 32 task cho 3 người/8 tuần.
- Đã thêm quy trình PR, issue template, CI chỉ kiểm tra cấu trúc và script kiểm tra không có dependency.
- Chưa triển khai backend/dashboard/agent/DNS, chưa có dependency runtime hay migration chạy được.
- Chưa cài Windows service, đổi DNS, kiểm thử tính năng hoặc đo mục tiêu lab.
- Kiểm tra: `python scripts/check_structure.py` — PASS: 17 thư mục bắt buộc, 9 ảnh và toàn bộ liên kết Markdown nội bộ. Chỉ xác minh bộ khung, chưa kiểm thử sản phẩm.
- Bước tiếp: điền tên thật; làm A01/B01/C01; chốt D03/D04 bằng spike và ADR.
