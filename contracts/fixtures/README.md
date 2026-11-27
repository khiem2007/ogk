# Shared fixtures — Contract v1

Fixture dùng ID ngẫu nhiên cố định cho test, domain `.example.test`, không có thông tin trẻ/gia đình thật. Các file `*.valid.json` minh họa shape hợp lệ và được dùng bởi test contract; không phải dữ liệu seed production.

| Fixture | Schema | Ý nghĩa |
|---|---|---|
| `policy.valid.json` | `policy.schema.json` | Snapshot v3 có chữ ký Ed25519 từ test-only key `test-fixture`; tuyệt đối không dùng private test key trong production. |
| `event.usage.valid.json` | `event.schema.json` | Foreground usage measured 30 giây; ID ổn định để minh họa dedup. |
| `command.lock.valid.json` | `command.schema.json` | LOCK_SESSION có expiry; fixture không thực thi lệnh. |
| `command_ack.valid.json` | `command_ack.schema.json` | Result ACK cho cùng command ID; executed không được suy ra từ delivery. |
| `request.time-extension.valid.json` | `request.schema.json` | Request 600 giây gắn local date cụ thể. |
| `grant.time-extension.valid.json` | `grant.schema.json` | Grant source request, cùng local date và bounded amount. |
| `ipc.telemetry.valid.json` | `ipc_message.schema.json` | Helper telemetry mẫu với child SID/session ID giả. |
| `event.invalid-missing-id.json` | `event.schema.json` | Cố ý thiếu `event_id`, phải bị reject. |
| `request.invalid-over-limit.json` | `request.schema.json` | Cố ý xin 86400 giây, vượt maximum, phải bị reject. |

TV2 review schedule/day-of-week, quota/grant, event sequencing và IPC semantics. TV3 review request fields, error/status implications và fixture đủ để dựng UI states. Trạng thái hai review: **chờ xác nhận**, chưa ghi pass. Xem [schema index](../schemas/README.md).
