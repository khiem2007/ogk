# contracts

Phụ trách: **TV1 điều phối, TV2/TV3 review**.

Schema policy/event/command/request/grant/IPC và fixture dùng chung. Chốt hợp đồng trước khi code ba thành phần.

## Contract v1 — TV1-A01

Schema Draft 2020-12, schema version `1`; fixtures dùng ID/domain giả, không chứa thông tin gia đình thật.

- [API v1](../docs/API.md) — routes, auth, ownership, errors, state lifecycle và event flow.
- [SRS](../docs/SRS.md) — FR/AC và traceability 9 ảnh.
- [ERD](../docs/ERD.md) — logical data model và transaction invariants.
- Schemas: `common.schema.json`, `policy.schema.json`, `event.schema.json`, `command.schema.json`, `command_ack.schema.json`, `request.schema.json`, `grant.schema.json`, `ipc_message.schema.json`.
- Fixtures hợp lệ: policy, usage event, command, command ACK, request, grant và IPC telemetry trong `fixtures/`.

Các schema/fixture là bản đề xuất cần TV2/TV3 review; chưa có runtime validator/API implementation. Xem [bảng phân công](../docs/PHAN_CONG.md).
