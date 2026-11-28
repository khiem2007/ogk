# deploy

Phụ trách: **TV1**.

Compose backend/reverse proxy, HTTPS, một worker cho SQLite lab; chỉ thêm cấu hình chạy khi có app thật.

Policy snapshots dùng Ed25519. Cấu hình `OGK_POLICY_SIGNING_KEY_ID` và `OGK_POLICY_SIGNING_PRIVATE_KEY` ở server; private key là base64 của seed 32 byte và không được commit hoặc ghi log. Agent cấu hình `OGK_POLICY_VERIFY_PUBLIC_KEYS` thành JSON map key ID → base64 raw public key; giữ key cũ trong map trong giai đoạn xoay key, rồi loại bỏ sau khi thiết bị đã nhận key mới. Không dùng key từ fixture/test trong deployment.

Trạng thái: TLS/reverse proxy và key provisioning cần hoàn thiện trong deploy task. Xem [bảng phân công](../docs/PHAN_CONG.md).
