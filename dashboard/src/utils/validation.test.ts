import { describe, expect, it } from 'vitest';
import { DemoOgkClient, OgkApiError } from '../api/client';
import { DOMAIN_CATALOG, PROTECTED_ALLOWLIST_ENTRIES, WEB_CATEGORY_META } from '../data/domainCatalog';
import { normalizeDomainInput, validateScheduleSlots } from './validation';

describe('Schedule 7x48 validation (C04 / POLICY_RULES)', () => {
  it('accepts non-overlapping half-hour intervals', () => {
    const res = validateScheduleSlots([
      { day_of_week: 0, start: '08:00', end: '11:30' },
      { day_of_week: 0, start: '14:00', end: '20:00' },
      { day_of_week: 6, start: '09:00', end: '21:00' },
    ]);
    expect(res.valid).toBe(true);
    expect(res.errors).toHaveLength(0);
  });

  it('rejects cross-midnight schedules', () => {
    const res = validateScheduleSlots([{ day_of_week: 1, start: '22:00', end: '06:00' }]);
    expect(res.valid).toBe(false);
    expect(res.errors[0]).toContain('qua nửa đêm');
  });

  it('rejects overlapping intervals on the same day', () => {
    const res = validateScheduleSlots([
      { day_of_week: 2, start: '08:00', end: '12:00' },
      { day_of_week: 2, start: '11:30', end: '14:00' },
    ]);
    expect(res.valid).toBe(false);
    expect(res.errors[0]).toContain('bị trùng');
  });

  it('rejects empty intervals', () => {
    const res = validateScheduleSlots([{ day_of_week: 3, start: '10:00', end: '10:00' }]);
    expect(res.valid).toBe(false);
    expect(res.errors[0]).toContain('rỗng');
  });
});

describe('Domain catalog & normalization (C08 / F2.3 / NT6)', () => {
  it('contains at least 200 unique safe entries across all 6 PDF categories', () => {
    expect(DOMAIN_CATALOG.length).toBeGreaterThanOrEqual(200);
    const uniqueDomains = new Set(DOMAIN_CATALOG.map((d) => d.domain));
    expect(uniqueDomains.size).toBe(DOMAIN_CATALOG.length);

    const categoriesPresent = new Set(DOMAIN_CATALOG.map((d) => d.category));
    for (const key of Object.keys(WEB_CATEGORY_META)) {
      expect(categoriesPresent.has(key as keyof typeof WEB_CATEGORY_META)).toBe(true);
    }
  });

  it('includes NT6 protected allowlist domains', () => {
    const domains = new Set(DOMAIN_CATALOG.map((d) => d.domain));
    for (const p of PROTECTED_ALLOWLIST_ENTRIES) {
      expect(domains.has(p.domain)).toBe(true);
    }
    expect(domains.has('tongdai111.vn')).toBe(true);
  });

  it('normalizes domain input and rejects URLs with paths', () => {
    expect(normalizeDomainInput('  Example.Test. ')).toBe('example.test');
    expect(normalizeDomainInput('https://example.test/path')).toBeNull();
  });
});

describe('DemoOgkClient contract invariants (C03–C07)', () => {
  it('rejects stale policy updates with 409 VERSION_CONFLICT', async () => {
    const client = new DemoOgkClient();
    const devs = await client.listDevices();
    const snap = await client.getPolicy(devs[0].id);

    client.simulateDemoServerVersionBump(devs[0].id);

    await expect(
      client.updatePolicy(devs[0].id, snap.policy_version, snap.policy),
    ).rejects.toMatchObject({
      status: 409,
      code: 'VERSION_CONFLICT',
    });
  });

  it('enforces one-time request decision and blocks child-view mutations', async () => {
    const client = new DemoOgkClient();
    const pending = (await client.listRequests()).find((r) => r.status === 'pending')!;
    const approved = await client.decideRequest(pending.request_id, 'approved');
    expect(approved.status).toBe('approved');

    await expect(client.decideRequest(pending.request_id, 'rejected')).rejects.toBeInstanceOf(
      OgkApiError,
    );

    await client.switchDemoRole('child-view');
    await expect(client.issueCommand(pending.device_id, 'LOCK_SESSION')).rejects.toMatchObject({
      status: 403,
      code: 'FORBIDDEN_CHILD_VIEW',
    });
  });
});
