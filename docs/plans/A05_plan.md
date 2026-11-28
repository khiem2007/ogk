# A05 — Versioned, Integrity-Protected Policy Snapshots

## Problem and proposed approach

Implement TV1 task A05 from `docs/PHAN_CONG.md`: parents can publish immutable, versioned policy snapshots; concurrent stale updates are rejected without changing the last valid snapshot; agents can verify snapshot integrity and reject modified or invalid payloads.

The repository already defines the policy payload in `contracts/schemas/policy.schema.json`, stores policy documents in the `policies` table, and documents `If-Match`/`expected_version` with `409 VERSION_CONFLICT` in `docs/API.md`. There is not yet a policy endpoint, service, or snapshot-integrity implementation. Reuse these contracts and existing FastAPI/SQLAlchemy patterns rather than duplicating them.

## Todos

1. **Use Ed25519 for snapshot signatures** — server signs snapshots with a protected private key; agents verify with a public key.
2. **Implement policy snapshot publishing and retrieval** — validate payloads, create immutable incremented versions atomically, enforce optimistic concurrency, and expose parent and agent policy endpoints.
3. **Implement agent integrity verification** — canonicalize the snapshot representation, verify authenticity and schema before accepting it, and keep the last valid snapshot on any failure.
4. **Add tests and update contract documentation** — cover integrity tampering, malformed snapshots, stale concurrent updates, and persistence of the previous valid version.

## Implementation outline

- Add a policy service and API routes, following the existing auth, ownership, database-session, and audit patterns.
- Validate the policy payload against the shared Draft 2020-12 JSON Schema before storing or returning it. Preserve immutable version history in `Policy`; do not overwrite prior versions.
- Within one write transaction, compare the caller's expected version to the current version and insert exactly the next version. Return the documented conflict response for stale versions and leave stored state unchanged.
- Define deterministic canonical serialization for the exact snapshot envelope that is authenticated, including its schema and policy versions. The signature itself must not be part of the authenticated bytes.
- Keep the Ed25519 private key server-side and out of logs; configure the agent with the corresponding public verification key and document how key rotation is handled.
- On the agent side, validate the schema and integrity before conversion/application; invalid, altered, or stale data must not replace the currently applied valid snapshot.
- Update the relevant schema/fixture, API and contract documentation, and add focused server integration and agent unit tests. Add a migration only if the selected key/version metadata requires a persisted schema change.

## Acceptance criteria

- A one-byte change to an authenticated snapshot causes agent verification to fail.
- A stale `If-Match`/`expected_version` is reported as `409 VERSION_CONFLICT`; the prior valid snapshot remains current and retrievable.
- Successful policy changes create monotonically increasing immutable versions, with validation and version changes committed atomically.
- Invalid schema or invalid integrity never becomes the agent's accepted/applied policy.
- Parent access is restricted to owned devices; agent access is restricted to the device bound to its bearer credential.

## Notes and decision

- **Signing choice:** Ed25519 asymmetric signatures selected. The server signs; agents only need the public verification key.
- Key storage, provisioning, rotation, and failure handling must be documented; do not log private key material.
- A05 depends on A01 and A04. The contract and device-auth groundwork exist in this repository; this plan does not assume that parent/agent policy endpoints already exist.
- No repository code changes are included in this planning task.
