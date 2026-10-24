# Làm việc nhóm

1. Chọn một mã việc trong docs/PHAN_CONG.md. Ghi tên thật/GitHub handle khi nhóm chốt danh sách.
2. Tạo nhánh `feat/TV1-A03-auth` hoặc `fix/TV2-B05-ipc`; một PR giải quyết một đầu việc.
3. Chốt schema/fixture trước nếu thay contract. Người dùng contract phải review thay đổi.
4. Commit code cùng test có ý nghĩa và tài liệu. Không commit DB, secret, token hoặc log chứa dữ liệu thật.
5. PR nêu vấn đề, hành vi sau sửa, mã công việc, kiểm thử đã chạy và giới hạn. Một người khác review trước merge.
6. Cập nhật docs/PROGRESS.md, liên kết evidence đến commit và ca thử. Không đổi “chưa chạy” thành “pass”.

Review mặc định: TV1 → TV2 → TV3 → TV1; riêng IPC cả TV2 và TV3, contract cả ba cùng xem.
Branch protection và collaborator chưa được cấu hình; quy trình review hiện là thỏa thuận nhóm.
Không thử kill process, khóa phiên hay đổi DNS trên máy đang làm việc; dùng Windows VM của nhóm.
Các script cài/gỡ và spike mặc định dry-run, thay đổi thật phải có rollback.
