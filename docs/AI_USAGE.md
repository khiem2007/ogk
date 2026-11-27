# Khai báo sử dụng công cụ AI

Trạng thái: **bản ghi đang cập nhật; cả nhóm phải bổ sung mọi lần sử dụng trước khi nộp**.

| Ngày | Công cụ | Phần việc có AI hỗ trợ | Người kiểm chứng | Cách kiểm chứng/kết quả |
|---|---|---|---|---|
| 2026-11-02 | OpenAI Codex | B01 spike Windows, B02 clock/models/tests và tài liệu TV2 | TV2 | pytest 15 pass; compile/import/structure pass; Windows host chỉ smoke-test read-only; VM acceptance còn mở |
| 2026-11-05 | OpenAI Codex | Đọc PDF đề bài, lập traceability, đồng bộ brief/phân công và tài liệu privacy/threat | TV2 | Đối chiếu text + render đủ 12 trang; review diff và liên kết Markdown |
| 2026-11-26 | Google Antigravity | TV3 C01–C10: UI/UX plan, React dashboard (8 trang), demo adapter, domainCatalog 200+ entries, PySide6 tray module, Playwright E2E 17 test cases, unit tests (14 tray + 9 JS = 23 tests) | TV3 | npm test: 9 pass; pytest tray: 14 pass; tsc --noEmit: clean; vite build: 282kB; check_structure.py: pass |

Quy tắc khai báo:

- Nêu rõ file/chức năng nào được gợi ý hoặc sinh bởi AI; không ghi chung chung “hỗ trợ code”.
- Người phụ trách phải đọc, chạy test và chịu trách nhiệm cho nội dung cuối.
- Ghi cả giới hạn/chưa kiểm chứng; không dùng kết quả AI làm bằng chứng Windows/network thực tế.
- Không gửi secret, token, dữ liệu trẻ em hoặc dữ liệu cá nhân thật vào công cụ AI.
