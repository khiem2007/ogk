# Shared JSON Schemas — Contract v1

Dialect: JSON Schema Draft 2020-12. `schema_version` là integer `1`; `$id` dùng namespace reserved `ogk.example`. References tới common definitions dùng relative `$ref` trong cùng thư mục.

| Schema | Producer → consumer | Dùng cho |
|---|---|---|
| `common.schema.json` | Shared definitions | UUID, UTC date-time, local date, Windows SID, category, domain, reason. |
| `policy.schema.json` | Server → agent | Immutable, versioned device policy snapshot. |
| `event.schema.json` | Agent → server | Event envelope có event ID, boot ID, sequence; server gắn device theo token. |
| `command.schema.json` | Server → agent | Command allowlist có expiry; payload theo command type. |
| `command_ack.schema.json` | Agent → server | Result executed/failed/expired; không đồng nghĩa delivered. |
| `request.schema.json` | Tray/agent → server | Xin tăng quota hoặc ngoại lệ app; không chứa device authority. |
| `grant.schema.json` | Server → agent | Scope/time bounds và source request/command cố định. |
| `ipc_message.schema.json` | Helper ↔ service | Typed local message, session/SID metadata, payload bounded. |

Examples are in [fixtures](../fixtures/README.md). JSON Schema kiểm tra shape; service vẫn phải validate ownership, SID/session, freshness, `start < end`, expiry, quota và state transition trong code. Contract hiện **chờ TV2/TV3 review**; chưa có runtime validator hoặc OpenAPI sinh từ server. Xem [API v1](../../docs/API.md), [SRS](../../docs/SRS.md) và [ERD](../../docs/ERD.md).
