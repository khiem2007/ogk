# Shared JSON Schemas — Contract v1

Dialect: JSON Schema Draft 2020-12. `schema_version` là integer `1`; `$id` dùng namespace reserved `ogk.example`. References tới common definitions dùng relative `$ref` trong cùng thư mục.

| Schema | Producer → consumer | Dùng cho |
|---|---|---|
| `common.schema.json` | Shared definitions | UUID, UTC date-time, local date, Windows SID, category, domain, reason. |
| `policy.schema.json` | Server → agent | Immutable, versioned device policy snapshot with Ed25519 signature metadata. |
| `event.schema.json` | Agent → server | Event envelope có event ID, boot ID, sequence; server gắn device theo token. |
| `command.schema.json` | Server → agent | Command allowlist có expiry; payload theo command type. |
| `command_ack.schema.json` | Agent → server | Result executed/failed/expired; không đồng nghĩa delivered. |
| `request.schema.json` | Tray/agent → server | Xin tăng quota hoặc ngoại lệ app; không chứa device authority. |
| `grant.schema.json` | Server → agent | Scope/time bounds và source request/command cố định. |
| `ipc_message.schema.json` | Helper ↔ service | Typed local message, session/SID metadata, payload bounded. |

Examples are in [fixtures](../fixtures/README.md). Runtime policy validation uses Draft 2020-12; Ed25519 verification is separate and must succeed before the agent applies a snapshot. Services still validate ownership, SID/session, freshness, expiry, quota and state transitions. Contract review by TV2/TV3 remains **pending**. Xem [API v1](../../docs/API.md), [SRS](../../docs/SRS.md) và [ERD](../../docs/ERD.md).
