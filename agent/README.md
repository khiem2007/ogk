# agent

Phụ trách: **TV2**.

Agent Python: core thuần Python, Windows adapter, Tray và DNS. Chưa cài service hoặc thay DNS host.

## Cấu trúc dự kiến

- `agent/dns/`: rule engine và proxy loopback UDP/TCP; không giải mã HTTPS.
- Các adapter Windows sẽ được bổ sung trong `agent/windows/` khi có code.

Trạng thái: đã tạo cấu trúc; chưa triển khai chức năng. Xem [bảng phân công](../docs/PHAN_CONG.md).
