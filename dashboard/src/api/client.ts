import type {
  ApiErrorEnvelope,
  AuditLogItem,
  AuthUser,
  ChildProfile,
  ChildRequestItem,
  CommandItem,
  CommandStatus,
  CommandType,
  DeleteAllStatus,
  DeviceInfo,
  EnrollmentCodeResponse,
  PolicyDocument,
  PolicySnapshotResponse,
  ReportSummary,
  UserRole,
} from '../types/ogk';
import {
  computeNextCommandStatus,
  createInitialDemoState,
  DEMO_CHILD_VIEW_USER,
  type DemoStoreState,
} from '../data/demoFixtures';

export type ApiMode = 'demo' | 'api';

export class OgkApiError extends Error {
  status: number;
  code: string;
  requestId: string;

  constructor(status: number, code: string, message: string, requestId = 'local') {
    super(message);
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

function makeUuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function makePairingCode(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let result = '';
  for (let i = 0; i < 8; i += 1) {
    result += chars[Math.floor(Math.random() * chars.length)];
  }
  return result;
}

export interface OgkClient {
  mode: ApiMode;
  setCsrfToken(token: string | null): void;
  getMe(): Promise<AuthUser | null>;
  login(email: string, password: string): Promise<AuthUser>;
  logout(): Promise<void>;
  switchDemoRole?(role: UserRole): Promise<AuthUser>;
  setDemoNetworkError?(enabled: boolean): void;
  getDemoNetworkError?(): boolean;
  simulateDemoCommandTransition?(
    commandId: string,
    targetStatus?: CommandStatus,
  ): Promise<CommandItem>;
  simulateDemoExpiryEnrollmentCode?(code: string): void;
  simulateDemoServerVersionBump?(deviceId: string): void;
  listChildren(): Promise<ChildProfile[]>;
  createChild(input: {
    display_name: string;
    age_band: '6-8' | '9-11' | '12-14';
    timezone: string;
  }): Promise<ChildProfile>;
  updateChild(
    childId: string,
    patch: Partial<Pick<ChildProfile, 'display_name' | 'age_band' | 'timezone' | 'consent_acknowledged_at'>>,
  ): Promise<ChildProfile>;
  listDevices(): Promise<DeviceInfo[]>;
  createEnrollmentCode(childId: string, deviceName: string): Promise<EnrollmentCodeResponse>;
  claimDemoEnrollmentCode?(code: string): Promise<DeviceInfo>;
  revokeDevice(deviceId: string): Promise<void>;
  getPolicy(deviceId: string): Promise<PolicySnapshotResponse>;
  updatePolicy(
    deviceId: string,
    expectedVersion: number,
    policy: PolicyDocument,
  ): Promise<PolicySnapshotResponse>;
  listRequests(): Promise<ChildRequestItem[]>;
  decideRequest(
    requestId: string,
    decision: 'approved' | 'rejected',
  ): Promise<ChildRequestItem>;
  listCommands(deviceId: string): Promise<CommandItem[]>;
  issueCommand(deviceId: string, commandType: CommandType): Promise<CommandItem>;
  getReport(deviceId: string, period: 'daily' | 'weekly'): Promise<ReportSummary>;
  listAuditLogs(): Promise<AuditLogItem[]>;
  getDeleteAllStatus(childId: string): Promise<DeleteAllStatus>;
  requestDeleteAllChildData(childId: string): Promise<DeleteAllStatus>;
  completeDemoAgentPurge?(childId: string): Promise<DeleteAllStatus>;
}

/**
 * Real HTTP client targeting TV1's FastAPI endpoints under /api/v1 (same-origin).
 * Sends cookies via credentials: 'include' and attaches X-CSRF-Token on mutations.
 */
export class HttpOgkClient implements OgkClient {
  readonly mode: ApiMode = 'api';
  private csrfToken: string | null = null;

  setCsrfToken(token: string | null): void {
    this.csrfToken = token;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const method = (init.method ?? 'GET').toUpperCase();
    const headers = new Headers(init.headers);
    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }
    if (init.body && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && this.csrfToken) {
      headers.set('X-CSRF-Token', this.csrfToken);
    }

    let response: Response;
    try {
      response = await fetch(`/api/v1${path}`, {
        ...init,
        method,
        headers,
        credentials: 'include',
      });
    } catch {
      throw new OgkApiError(
        0,
        'NETWORK_ERROR',
        'Không kết nối được tới OGK-Server (/api/v1). Kiểm tra mạng hoặc backend TV1.',
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const text = await response.text();
    let parsed: unknown = null;
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch {
      parsed = null;
    }

    if (!response.ok) {
      const envelope = parsed as Partial<ApiErrorEnvelope> | null;
      if (envelope?.error) {
        throw new OgkApiError(
          response.status,
          envelope.error.code,
          envelope.error.message,
          envelope.error.request_id,
        );
      }
      throw new OgkApiError(
        response.status,
        `HTTP_${response.status}`,
        `Server trả lỗi HTTP ${response.status} tại ${path} (TV1 backend chưa triển khai endpoint này hoặc đang lỗi).`,
      );
    }

    return parsed as T;
  }

  async getMe(): Promise<AuthUser | null> {
    try {
      const user = await this.request<AuthUser>('/auth/me');
      this.setCsrfToken(user.csrf_token);
      return user;
    } catch (err) {
      if (err instanceof OgkApiError && err.status === 401) {
        return null;
      }
      throw err;
    }
  }

  async login(email: string, password: string): Promise<AuthUser> {
    const user = await this.request<AuthUser>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setCsrfToken(user.csrf_token);
    return user;
  }

  async logout(): Promise<void> {
    await this.request<void>('/auth/logout', { method: 'POST' });
    this.setCsrfToken(null);
  }

  listChildren(): Promise<ChildProfile[]> {
    return this.request<ChildProfile[]>('/children');
  }

  createChild(input: {
    display_name: string;
    age_band: '6-8' | '9-11' | '12-14';
    timezone: string;
  }): Promise<ChildProfile> {
    return this.request<ChildProfile>('/children', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  updateChild(
    childId: string,
    patch: Partial<Pick<ChildProfile, 'display_name' | 'age_band' | 'timezone' | 'consent_acknowledged_at'>>,
  ): Promise<ChildProfile> {
    return this.request<ChildProfile>(`/children/${childId}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    });
  }

  listDevices(): Promise<DeviceInfo[]> {
    return this.request<DeviceInfo[]>('/devices');
  }

  createEnrollmentCode(childId: string, deviceName: string): Promise<EnrollmentCodeResponse> {
    return this.request<EnrollmentCodeResponse>('/enrollment-codes', {
      method: 'POST',
      body: JSON.stringify({ child_id: childId, device_name: deviceName }),
    });
  }

  revokeDevice(deviceId: string): Promise<void> {
    return this.request<void>(`/devices/${deviceId}/revoke`, { method: 'POST' });
  }

  getPolicy(deviceId: string): Promise<PolicySnapshotResponse> {
    return this.request<PolicySnapshotResponse>(`/devices/${deviceId}/policy`);
  }

  updatePolicy(
    deviceId: string,
    expectedVersion: number,
    policy: PolicyDocument,
  ): Promise<PolicySnapshotResponse> {
    return this.request<PolicySnapshotResponse>(`/devices/${deviceId}/policy`, {
      method: 'PUT',
      headers: { 'If-Match': `"${expectedVersion}"` },
      body: JSON.stringify({ expected_version: expectedVersion, policy }),
    });
  }

  listRequests(): Promise<ChildRequestItem[]> {
    return this.request<ChildRequestItem[]>('/requests');
  }

  decideRequest(
    requestId: string,
    decision: 'approved' | 'rejected',
  ): Promise<ChildRequestItem> {
    return this.request<ChildRequestItem>(`/requests/${requestId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    });
  }

  listCommands(deviceId: string): Promise<CommandItem[]> {
    return this.request<CommandItem[]>(`/devices/${deviceId}/commands`);
  }

  issueCommand(deviceId: string, commandType: CommandType): Promise<CommandItem> {
    return this.request<CommandItem>(`/devices/${deviceId}/commands`, {
      method: 'POST',
      body: JSON.stringify({ command_type: commandType }),
    });
  }

  getReport(deviceId: string, period: 'daily' | 'weekly'): Promise<ReportSummary> {
    return this.request<ReportSummary>(`/reports/${period}?device_id=${encodeURIComponent(deviceId)}`);
  }

  listAuditLogs(): Promise<AuditLogItem[]> {
    return this.request<AuditLogItem[]>('/audit');
  }

  getDeleteAllStatus(childId: string): Promise<DeleteAllStatus> {
    return this.request<DeleteAllStatus>(`/children/${childId}/data-deletion`);
  }

  requestDeleteAllChildData(childId: string): Promise<DeleteAllStatus> {
    return this.request<DeleteAllStatus>(`/children/${childId}/data-deletion`, {
      method: 'POST',
    });
  }
}

/**
 * Isolated Demo / Fixture Adapter per PHAN_CONG.md:
 * Explicitly labeled on UI, enforces ownership/versioning/atomic transitions/expiry locally
 * while awaiting TV1 backend A03–A10.
 */
export class DemoOgkClient implements OgkClient {
  readonly mode: ApiMode = 'demo';
  private state: DemoStoreState = createInitialDemoState();

  setCsrfToken(_token: string | null): void {
    // Managed internally in demo store.
  }

  private guardNetwork(): void {
    if (this.state.simulateNetworkError) {
      throw new OgkApiError(
        503,
        'NETWORK_UNAVAILABLE',
        'Mô phỏng lỗi mạng / Server không phản hồi (Demo Test Mode).',
      );
    }
  }

  private requireParentMutation(): AuthUser {
    if (!this.state.currentUser) {
      throw new OgkApiError(401, 'UNAUTHORIZED', 'Phiên đăng nhập đã hết hạn.');
    }
    if (this.state.currentUser.role === 'child-view') {
      throw new OgkApiError(
        403,
        'FORBIDDEN_CHILD_VIEW',
        'Tài khoản child-view chỉ được xem minh bạch, không có quyền thay đổi cấu hình.',
      );
    }
    return this.state.currentUser;
  }

  private recordAudit(
    actor: AuthUser,
    action: string,
    resourceType: string,
    beforeSummary: string,
    afterSummary: string,
  ): void {
    this.state.auditLogs.unshift({
      id: `aud-${makeUuid().slice(0, 8)}`,
      actor_label: actor.display_name,
      actor_ip: '127.0.0.1',
      action,
      resource_type: resourceType,
      before_summary: beforeSummary,
      after_summary: afterSummary,
      created_at: new Date().toISOString(),
    });
  }

  setDemoNetworkError(enabled: boolean): void {
    this.state.simulateNetworkError = enabled;
  }

  getDemoNetworkError(): boolean {
    return this.state.simulateNetworkError;
  }

  async getMe(): Promise<AuthUser | null> {
    this.guardNetwork();
    return this.state.currentUser ? { ...this.state.currentUser } : null;
  }

  async login(email: string, password: string): Promise<AuthUser> {
    this.guardNetwork();
    if (this.state.lockedUntilMs && Date.now() < this.state.lockedUntilMs) {
      throw new OgkApiError(
        429,
        'ACCOUNT_LOCKED',
        'Tài khoản tạm khóa 15 phút do nhập sai mật khẩu 5 lần (F5.1).',
      );
    }
    if (!email.includes('@') || password.length < 10) {
      this.state.failedLoginAttempts += 1;
      if (this.state.failedLoginAttempts >= 5) {
        this.state.lockedUntilMs = Date.now() + 15 * 60 * 1000;
      }
      throw new OgkApiError(
        401,
        'INVALID_CREDENTIALS',
        'Email hoặc mật khẩu không hợp lệ (mật khẩu yêu cầu tối thiểu 10 ký tự).',
      );
    }
    this.state.failedLoginAttempts = 0;
    this.state.lockedUntilMs = null;
    const isChild = email.toLowerCase().includes('tre') || email.toLowerCase().includes('child');
    this.state.currentUser = isChild
      ? { ...DEMO_CHILD_VIEW_USER }
      : {
          id: '00000000-0000-4000-8000-000000000001',
          email,
          display_name: 'Phụ huynh (Demo)',
          role: 'parent',
          csrf_token: 'demo-csrf-token-ogk-v1',
        };
    return { ...this.state.currentUser };
  }

  async logout(): Promise<void> {
    this.guardNetwork();
    this.state.currentUser = null;
  }

  async switchDemoRole(role: UserRole): Promise<AuthUser> {
    this.guardNetwork();
    if (role === 'child-view') {
      this.state.currentUser = { ...DEMO_CHILD_VIEW_USER };
    } else {
      this.state.currentUser = {
        id: '00000000-0000-4000-8000-000000000001',
        email: 'phuhuynh.demo@ogk.local',
        display_name: role === 'admin' ? 'Quản trị gia đình (Demo)' : 'Phụ huynh (Demo)',
        role,
        csrf_token: 'demo-csrf-token-ogk-v1',
      };
    }
    return { ...this.state.currentUser };
  }

  async listChildren(): Promise<ChildProfile[]> {
    this.guardNetwork();
    return structuredClone(this.state.children);
  }

  async createChild(input: {
    display_name: string;
    age_band: '6-8' | '9-11' | '12-14';
    timezone: string;
  }): Promise<ChildProfile> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const created: ChildProfile = {
      id: makeUuid(),
      display_name: input.display_name.trim(),
      age_band: input.age_band,
      timezone: input.timezone,
      consent_acknowledged_at: null,
      explanation_version: '1.0',
    };
    this.state.children.push(created);
    this.state.deleteAllByChild[created.id] = {
      status: 'idle',
      requested_at: null,
      server_purged: false,
      agent_cache_purged: false,
      message: 'Chưa có yêu cầu xóa dữ liệu.',
    };
    this.recordAudit(actor, 'CHILD_CREATED', 'child', 'none', created.display_name);
    return structuredClone(created);
  }

  async updateChild(
    childId: string,
    patch: Partial<Pick<ChildProfile, 'display_name' | 'age_band' | 'timezone' | 'consent_acknowledged_at'>>,
  ): Promise<ChildProfile> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const target = this.state.children.find((c) => c.id === childId);
    if (!target) {
      throw new OgkApiError(404, 'CHILD_NOT_FOUND', 'Không tìm thấy hồ sơ trẻ.');
    }
    const before = `${target.display_name}, band=${target.age_band}`;
    Object.assign(target, patch);
    const after = `${target.display_name}, band=${target.age_band}`;
    this.recordAudit(actor, 'CHILD_UPDATED', 'child', before, after);
    return structuredClone(target);
  }

  async listDevices(): Promise<DeviceInfo[]> {
    this.guardNetwork();
    return structuredClone(this.state.devices);
  }

  async createEnrollmentCode(childId: string, deviceName: string): Promise<EnrollmentCodeResponse> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();
    const code = makePairingCode();
    this.state.enrollmentCodes.unshift({
      code,
      child_id: childId,
      device_name: deviceName.trim() || 'PC-Trẻ-mới',
      expires_at: expiresAt,
      consumed: false,
    });
    this.recordAudit(actor, 'ENROLLMENT_CODE_CREATED', 'enrollment_code', '—', `device=${deviceName}`);
    return { code, expires_at: expiresAt, child_id: childId, device_name: deviceName };
  }

  simulateDemoExpiryEnrollmentCode(code: string): void {
    const entry = this.state.enrollmentCodes.find((c) => c.code === code);
    if (entry) {
      entry.expires_at = new Date(Date.now() - 60 * 1000).toISOString();
    }
  }

  async claimDemoEnrollmentCode(code: string): Promise<DeviceInfo> {
    this.guardNetwork();
    const entry = this.state.enrollmentCodes.find((c) => c.code === code.trim().toUpperCase());
    if (!entry) {
      throw new OgkApiError(404, 'ENROLLMENT_INVALID', 'Mã ghép không tồn tại.');
    }
    if (entry.consumed) {
      throw new OgkApiError(409, 'ENROLLMENT_CONSUMED', 'Mã ghép chỉ dùng một lần và đã được sử dụng (T02).');
    }
    if (new Date(entry.expires_at).getTime() <= Date.now()) {
      throw new OgkApiError(410, 'ENROLLMENT_EXPIRED', 'Mã ghép đã quá hạn 10 phút và bị từ chối (T02).');
    }
    entry.consumed = true;
    const deviceId = makeUuid();
    const nowIso = new Date().toISOString();
    const newDevice: DeviceInfo = {
      id: deviceId,
      child_id: entry.child_id,
      name: entry.device_name,
      windows_sid: 'S-1-5-21-111-222-333-1099',
      connectivity: 'online',
      last_seen_at: nowIso,
      server_policy_version: 1,
      applied_policy_version: 1,
      policy_integrity_status: 'verified',
      revoked_at: null,
      remaining_seconds_today: 7200,
      manual_lock: false,
      clock_suspect: false,
    };
    this.state.devices.push(newDevice);
    const basePolicy = structuredClone(this.state.policies[Object.keys(this.state.policies)[0]]);
    basePolicy.device_id = deviceId;
    basePolicy.policy_version = 1;
    basePolicy.issued_at = nowIso;
    basePolicy.integrity_tag = `hmac-sha256:demo-v1-${deviceId.slice(0, 8)}`;
    this.state.policies[deviceId] = basePolicy;
    this.state.reports[deviceId] = {
      device_id: deviceId,
      period: 'weekly',
      date_label: 'Tuần hiện tại (Thiết bị mới)',
      measured_total_seconds: 0,
      estimated_degraded_seconds: 0,
      telemetry_gaps_count: 0,
      blocked_attempts_count: 0,
      requests_count: 0,
      weekly_bars: [
        { label: 'T2', date: '2026-11-23', measured_seconds: 0, estimated_degraded_seconds: 0 },
        { label: 'T3', date: '2026-11-24', measured_seconds: 0, estimated_degraded_seconds: 0 },
        { label: 'T4', date: '2026-11-25', measured_seconds: 0, estimated_degraded_seconds: 0 },
        { label: 'T5', date: '2026-11-26', measured_seconds: 0, estimated_degraded_seconds: 0 },
        { label: 'T6', date: '2026-11-27', measured_seconds: 0, estimated_degraded_seconds: 0 },
        { label: 'T7', date: '2026-11-28', measured_seconds: 0, estimated_degraded_seconds: 0 },
        { label: 'CN', date: '2026-11-29', measured_seconds: 0, estimated_degraded_seconds: 0 },
      ],
      top_apps: [],
      top_domains: [],
    };
    return structuredClone(newDevice);
  }

  async revokeDevice(deviceId: string): Promise<void> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const device = this.state.devices.find((d) => d.id === deviceId);
    if (!device) {
      throw new OgkApiError(404, 'DEVICE_NOT_FOUND', 'Không tìm thấy thiết bị.');
    }
    device.revoked_at = new Date().toISOString();
    device.connectivity = 'offline';
    this.recordAudit(actor, 'DEVICE_REVOKED', 'device', `name=${device.name}, active`, 'revoked=true');
  }

  async getPolicy(deviceId: string): Promise<PolicySnapshotResponse> {
    this.guardNetwork();
    const snap = this.state.policies[deviceId];
    if (!snap) {
      throw new OgkApiError(404, 'POLICY_NOT_FOUND', 'Không tìm thấy policy thiết bị.');
    }
    return structuredClone(snap);
  }

  simulateDemoServerVersionBump(deviceId: string): void {
    const snap = this.state.policies[deviceId];
    if (snap) {
      snap.policy_version += 1;
      snap.issued_at = new Date().toISOString();
      snap.integrity_tag = `hmac-sha256:demo-v${snap.policy_version}-${deviceId.slice(0, 8)}`;
      const dev = this.state.devices.find((d) => d.id === deviceId);
      if (dev) {
        dev.server_policy_version = snap.policy_version;
      }
    }
  }

  async updatePolicy(
    deviceId: string,
    expectedVersion: number,
    policy: PolicyDocument,
  ): Promise<PolicySnapshotResponse> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const current = this.state.policies[deviceId];
    if (!current) {
      throw new OgkApiError(404, 'POLICY_NOT_FOUND', 'Không tìm thấy policy thiết bị.');
    }
    if (current.policy_version !== expectedVersion) {
      throw new OgkApiError(
        409,
        'VERSION_CONFLICT',
        `Phiên bản chính sách trên máy chủ đã tăng lên v${current.policy_version} (bản bạn đang sửa là v${expectedVersion}). Hãy tải lại bản mới nhất trước khi lưu.`,
      );
    }

    const nextVersion = current.policy_version + 1;
    const nextSnapshot: PolicySnapshotResponse = {
      schema_version: 1,
      device_id: deviceId,
      policy_version: nextVersion,
      issued_at: new Date().toISOString(),
      integrity_tag: `hmac-sha256:demo-v${nextVersion}-${deviceId.slice(0, 8)}`,
      policy: structuredClone(policy),
    };

    const beforeTotal = current.policy.quotas.total_daily_seconds;
    this.state.policies[deviceId] = nextSnapshot;
    const dev = this.state.devices.find((d) => d.id === deviceId);
    if (dev) {
      dev.server_policy_version = nextVersion;
      if (dev.connectivity === 'online') {
        dev.applied_policy_version = nextVersion;
        dev.policy_integrity_status = 'verified';
      } else {
        dev.policy_integrity_status = 'pending';
      }
    }
    this.recordAudit(
      actor,
      'POLICY_UPDATED',
      'policy',
      `v${expectedVersion}, quota=${beforeTotal}s`,
      `v${nextVersion}, quota=${policy.quotas.total_daily_seconds}s`,
    );
    return structuredClone(nextSnapshot);
  }

  async listRequests(): Promise<ChildRequestItem[]> {
    this.guardNetwork();
    return structuredClone(this.state.requests);
  }

  async decideRequest(
    requestId: string,
    decision: 'approved' | 'rejected',
  ): Promise<ChildRequestItem> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const target = this.state.requests.find((r) => r.request_id === requestId);
    if (!target) {
      throw new OgkApiError(404, 'REQUEST_NOT_FOUND', 'Không tìm thấy yêu cầu.');
    }
    if (target.status !== 'pending') {
      throw new OgkApiError(
        409,
        'REQUEST_ALREADY_DECIDED',
        `Yêu cầu đã ở trạng thái "${target.status}", không thể duyệt lại (T09 atomic transition).`,
      );
    }
    target.status = decision;
    target.decided_by = actor.display_name;
    target.decided_at = new Date().toISOString();

    if (decision === 'approved' && target.request_type === 'time_extension' && target.payload.amount_seconds) {
      const dev = this.state.devices.find((d) => d.id === target.device_id);
      if (dev) {
        dev.remaining_seconds_today += target.payload.amount_seconds;
      }
    }

    this.recordAudit(
      actor,
      decision === 'approved' ? 'REQUEST_APPROVED' : 'REQUEST_REJECTED',
      'request',
      'status=pending',
      `status=${decision} (${target.request_id.slice(0, 8)})`,
    );
    return structuredClone(target);
  }

  async listCommands(deviceId: string): Promise<CommandItem[]> {
    this.guardNetwork();
    return structuredClone(this.state.commands.filter((c) => c.device_id === deviceId));
  }

  async issueCommand(deviceId: string, commandType: CommandType): Promise<CommandItem> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const now = new Date();
    const expires = new Date(now.getTime() + 3 * 60 * 1000);
    const cmd: CommandItem = {
      command_id: makeUuid(),
      device_id: deviceId,
      command_type: commandType,
      issued_at: now.toISOString(),
      expires_at: expires.toISOString(),
      observed_at: null,
      status: 'queued',
      result_code: null,
      payload:
        commandType === 'TEMPORARY_TIME_EXEMPTION'
          ? { grant_id: makeUuid(), duration_seconds: 900, scope: 'time_limits' }
          : commandType === 'EXEMPT_UNTIL_LOCAL_DAY_END'
            ? { grant_id: makeUuid(), scope: 'time_limits' }
            : {},
    };
    this.state.commands.unshift(cmd);
    this.recordAudit(actor, 'COMMAND_ISSUED', 'command', '—', `${commandType} -> queued`);
    return structuredClone(cmd);
  }

  async simulateDemoCommandTransition(
    commandId: string,
    targetStatus?: CommandStatus,
  ): Promise<CommandItem> {
    this.guardNetwork();
    const cmd = this.state.commands.find((c) => c.command_id === commandId);
    if (!cmd) {
      throw new OgkApiError(404, 'COMMAND_NOT_FOUND', 'Không tìm thấy lệnh.');
    }
    const nowIso = new Date().toISOString();
    if (targetStatus) {
      cmd.status = targetStatus;
      cmd.observed_at = nowIso;
      cmd.result_code =
        targetStatus === 'executed'
          ? cmd.command_type === 'LOCK_SESSION'
            ? 'SESSION_STATE_CONFIRMED'
            : 'COMMAND_APPLIED'
          : targetStatus === 'expired'
            ? 'EXPIRED_ON_AGENT'
            : targetStatus === 'failed'
              ? 'IPC_UNAVAILABLE'
              : 'DELIVERED_TO_AGENT';
    } else {
      const next = computeNextCommandStatus(cmd.command_type, cmd.status);
      cmd.status = next.status;
      cmd.observed_at = nowIso;
      cmd.result_code = next.result_code;
    }

    if (cmd.status === 'executed') {
      const dev = this.state.devices.find((d) => d.id === cmd.device_id);
      if (dev) {
        if (cmd.command_type === 'LOCK_SESSION') {
          dev.manual_lock = true;
        } else if (cmd.command_type === 'CLEAR_MANUAL_LOCK') {
          dev.manual_lock = false;
        }
      }
    }
    return structuredClone(cmd);
  }

  async getReport(deviceId: string, period: 'daily' | 'weekly'): Promise<ReportSummary> {
    this.guardNetwork();
    const base = this.state.reports[deviceId];
    if (!base) {
      throw new OgkApiError(404, 'REPORT_NOT_FOUND', 'Không có báo cáo cho thiết bị.');
    }
    const copy = structuredClone(base);
    copy.period = period;
    if (period === 'daily') {
      const latest = copy.weekly_bars[3] ?? copy.weekly_bars[0];
      copy.date_label = `Hôm nay (${latest.date})`;
      copy.measured_total_seconds = latest.measured_seconds;
      copy.estimated_degraded_seconds = latest.estimated_degraded_seconds;
    }
    return copy;
  }

  async listAuditLogs(): Promise<AuditLogItem[]> {
    this.guardNetwork();
    return structuredClone(this.state.auditLogs);
  }

  async getDeleteAllStatus(childId: string): Promise<DeleteAllStatus> {
    this.guardNetwork();
    return structuredClone(
      this.state.deleteAllByChild[childId] ?? {
        status: 'idle',
        requested_at: null,
        server_purged: false,
        agent_cache_purged: false,
        message: 'Chưa có yêu cầu xóa dữ liệu.',
      },
    );
  }

  async requestDeleteAllChildData(childId: string): Promise<DeleteAllStatus> {
    this.guardNetwork();
    const actor = this.requireParentMutation();
    const nowIso = new Date().toISOString();
    const nextStatus: DeleteAllStatus = {
      status: 'server_deleted_pending_agent',
      requested_at: nowIso,
      server_purged: true,
      agent_cache_purged: false,
      message: 'Đã xóa lịch sử trên Server; đang chờ Agent xác nhận xóa cache/outbox cục bộ.',
    };
    this.state.deleteAllByChild[childId] = nextStatus;

    for (const dev of this.state.devices.filter((d) => d.child_id === childId)) {
      const rep = this.state.reports[dev.id];
      if (rep) {
        rep.measured_total_seconds = 0;
        rep.estimated_degraded_seconds = 0;
        rep.blocked_attempts_count = 0;
        rep.top_apps = [];
        rep.top_domains = [];
        rep.weekly_bars = rep.weekly_bars.map((b) => ({
          ...b,
          measured_seconds: 0,
          estimated_degraded_seconds: 0,
        }));
      }
    }

    this.recordAudit(
      actor,
      'CHILD_DATA_PURGE_REQUESTED',
      'child_data',
      'retained_90d=active',
      'server_purged=true, agent_cache=pending (không lưu chi tiết dữ liệu đã xóa)',
    );
    return structuredClone(nextStatus);
  }

  async completeDemoAgentPurge(childId: string): Promise<DeleteAllStatus> {
    this.guardNetwork();
    const existing = this.state.deleteAllByChild[childId];
    const completed: DeleteAllStatus = {
      status: 'completed',
      requested_at: existing?.requested_at ?? new Date().toISOString(),
      server_purged: true,
      agent_cache_purged: true,
      message: 'Hoàn tất: đã xóa đồng thời dữ liệu trên Server và cache/outbox của Agent (F3.3 / T23).',
    };
    this.state.deleteAllByChild[childId] = completed;
    return structuredClone(completed);
  }
}

export function createOgkClient(mode: ApiMode): OgkClient {
  return mode === 'api' ? new HttpOgkClient() : new DemoOgkClient();
}
