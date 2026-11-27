import type {
  AuditLogItem,
  AuthUser,
  ChildProfile,
  ChildRequestItem,
  CommandItem,
  CommandStatus,
  CommandType,
  DeleteAllStatus,
  DeviceInfo,
  PolicyDocument,
  PolicySnapshotResponse,
  ReportSummary,
} from '../types/ogk';
import { PROTECTED_ALLOWLIST_ENTRIES } from './domainCatalog';

export interface DemoStoreState {
  currentUser: AuthUser | null;
  failedLoginAttempts: number;
  lockedUntilMs: number | null;
  simulateNetworkError: boolean;
  children: ChildProfile[];
  devices: DeviceInfo[];
  policies: Record<string, PolicySnapshotResponse>;
  requests: ChildRequestItem[];
  commands: CommandItem[];
  reports: Record<string, ReportSummary>;
  auditLogs: AuditLogItem[];
  deleteAllByChild: Record<string, DeleteAllStatus>;
  enrollmentCodes: Array<{
    code: string;
    child_id: string;
    device_name: string;
    expires_at: string;
    consumed: boolean;
  }>;
}

const DEMO_PARENT_USER: AuthUser = {
  id: '00000000-0000-4000-8000-000000000001',
  email: 'phuhuynh.demo@ogk.local',
  display_name: 'Phụ huynh (Demo)',
  role: 'parent',
  csrf_token: 'demo-csrf-token-ogk-v1',
};

export const DEMO_CHILD_VIEW_USER: AuthUser = {
  id: '00000000-0000-4000-8000-000000000002',
  email: 'tre.demo@ogk.local',
  display_name: 'Bé An (Chế độ trẻ xem)',
  role: 'child-view',
  csrf_token: 'demo-csrf-token-child-readonly',
};

const CHILD_AN_ID = '11111111-1111-4111-8111-111111111101';
const CHILD_MINH_ID = '11111111-1111-4111-8111-111111111102';
const DEVICE_AN_ID = 'a3e1f4d0-00f7-4e84-9dbe-13e9c77510a1';
const DEVICE_MINH_ID = 'b4f2e5e1-1108-4f95-8ecf-24fad88621b2';

function makeDefaultPolicy(timezone: string): PolicyDocument {
  return {
    timezone,
    idle_threshold_seconds: 300,
    manual_lock: false,
    schedule: [
      { day_of_week: 0, start: '08:00', end: '20:00' },
      { day_of_week: 1, start: '08:00', end: '20:00' },
      { day_of_week: 2, start: '08:00', end: '20:00' },
      { day_of_week: 3, start: '08:00', end: '20:00' },
      { day_of_week: 4, start: '08:00', end: '20:30' },
      { day_of_week: 5, start: '09:00', end: '21:00' },
      { day_of_week: 6, start: '09:00', end: '21:00' },
    ],
    quotas: {
      total_daily_seconds: 7200,
      weekend_daily_seconds: 10800,
      category_daily_seconds: {
        education: 7200,
        entertainment: 3600,
        games: 1800,
        other: 1800,
      },
    },
    apps: [
      {
        app_id: 'bf1042d1-1b86-42b4-888c-4bfc88185cb1',
        display_name: 'Game mẫu kiểm thử',
        executable_name: 'sample-game.exe',
        executable_sha256:
          'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        category: 'games',
        decision: 'block',
      },
      {
        app_id: 'cf2053e2-2c97-43c5-999d-5cfd99296dc2',
        display_name: 'Scratch Desktop',
        executable_name: 'scratch.exe',
        executable_sha256:
          '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
        category: 'education',
        decision: 'allow',
      },
      {
        app_id: 'df3064f3-3da8-44d6-aaae-6dfeaa3a7ed3',
        display_name: 'Trình duyệt Chrome',
        executable_name: 'chrome.exe',
        executable_sha256:
          '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae',
        category: 'other',
        decision: 'allow',
      },
    ],
    domains: {
      mode: 'blocklist',
      hard_block: ['blocked.example.test', 'restricted-sim-01.example.test'],
      explicit_allow: ['learning.example.test', 'khanacademy.org'],
      protected_allowlist: PROTECTED_ALLOWLIST_ENTRIES.map((e) => e.domain),
      restricted_schedule: [
        { day_of_week: 5, start: '19:00', end: '20:30' },
        { day_of_week: 6, start: '19:00', end: '20:30' },
      ],
      category_rules: [
        { category: 'education', decision: 'allow', domains: ['khanacademy.org', 'olm.vn'] },
        { category: 'entertainment', decision: 'restrict', domains: ['youtubekids.com'] },
        { category: 'social', decision: 'block', domains: ['tiktok.com', 'facebook.com'] },
        { category: 'games', decision: 'restrict', domains: ['games.example.test', 'roblox.com'] },
        {
          category: 'inappropriate',
          decision: 'block',
          domains: ['restricted-sim-01.example.test', 'restricted-sim-02.example.test'],
        },
        { category: 'uncategorized', decision: 'restrict', domains: ['unknown-site-01.test'] },
      ],
      safesearch_enabled: true,
      safesearch_verified_by_dns: false,
    },
  };
}

export function createInitialDemoState(): DemoStoreState {
  const nowIso = '2026-11-26T16:10:00Z';
  const anPolicy = makeDefaultPolicy('Asia/Ho_Chi_Minh');
  const minhPolicy = makeDefaultPolicy('Asia/Ho_Chi_Minh');
  minhPolicy.quotas.total_daily_seconds = 5400;

  return {
    currentUser: DEMO_PARENT_USER,
    failedLoginAttempts: 0,
    lockedUntilMs: null,
    simulateNetworkError: false,
    children: [
      {
        id: CHILD_AN_ID,
        display_name: 'Bé An (Demo)',
        age_band: '9-11',
        timezone: 'Asia/Ho_Chi_Minh',
        consent_acknowledged_at: '2026-11-02T09:00:00Z',
        explanation_version: '1.0',
      },
      {
        id: CHILD_MINH_ID,
        display_name: 'Bé Minh (Demo)',
        age_band: '6-8',
        timezone: 'Asia/Ho_Chi_Minh',
        consent_acknowledged_at: '2026-11-10T08:30:00Z',
        explanation_version: '1.0',
      },
    ],
    devices: [
      {
        id: DEVICE_AN_ID,
        child_id: CHILD_AN_ID,
        name: 'PC-Phòng-học',
        windows_sid: 'S-1-5-21-111-222-333-1001',
        connectivity: 'online',
        last_seen_at: nowIso,
        server_policy_version: 3,
        applied_policy_version: 3,
        policy_integrity_status: 'verified',
        revoked_at: null,
        remaining_seconds_today: 900,
        manual_lock: false,
        clock_suspect: false,
      },
      {
        id: DEVICE_MINH_ID,
        child_id: CHILD_MINH_ID,
        name: 'Laptop-Học-tập',
        windows_sid: 'S-1-5-21-111-222-333-1002',
        connectivity: 'degraded',
        last_seen_at: '2026-11-26T15:52:00Z',
        server_policy_version: 2,
        applied_policy_version: 1,
        policy_integrity_status: 'pending',
        revoked_at: null,
        remaining_seconds_today: 1800,
        manual_lock: false,
        clock_suspect: false,
      },
    ],
    policies: {
      [DEVICE_AN_ID]: {
        schema_version: 1,
        device_id: DEVICE_AN_ID,
        policy_version: 3,
        issued_at: '2026-11-26T15:00:00Z',
        integrity_tag: 'hmac-sha256:demo-verified-v3-a3e1f4d0',
        policy: anPolicy,
      },
      [DEVICE_MINH_ID]: {
        schema_version: 1,
        device_id: DEVICE_MINH_ID,
        policy_version: 2,
        issued_at: '2026-11-26T14:20:00Z',
        integrity_tag: 'hmac-sha256:demo-pending-v2-b4f2e5e1',
        policy: minhPolicy,
      },
    },
    requests: [
      {
        request_id: '7b8d36bb-9b56-4f8d-b8c7-74c1f0a3b36c',
        device_id: DEVICE_AN_ID,
        child_name: 'Bé An (Demo)',
        request_type: 'time_extension',
        created_at: '2026-11-26T16:00:00Z',
        reason: 'Con cần thêm 20 phút hoàn thành bài thuyết trình nhóm môn Khoa học.',
        status: 'pending',
        decided_by: null,
        decided_at: null,
        payload: {
          amount_seconds: 1200,
          local_date: '2026-11-26',
        },
        grant_preview: {
          scope: 'Tăng tổng hạn mức ngày 2026-11-26 thêm 20 phút (không tự mở lịch ngoài giờ)',
          valid_until: '2026-11-26T16:59:59Z',
        },
      },
      {
        request_id: '8c9e47cc-ac67-409e-c9d8-85d201b4c47d',
        device_id: DEVICE_AN_ID,
        child_name: 'Bé An (Demo)',
        request_type: 'app_exception',
        created_at: '2026-11-25T13:15:00Z',
        reason: 'Con đã làm xong bài tập rồi ạ.',
        status: 'approved',
        decided_by: 'Phụ huynh (Demo)',
        decided_at: '2026-11-25T13:20:00Z',
        payload: {
          app_id: 'bf1042d1-1b86-42b4-888c-4bfc88185cb1',
          app_name: 'Game xếp hình mẫu',
          duration_seconds: 1800,
        },
        grant_preview: {
          scope: 'Mở riêng app đã chọn trong 30 phút (không vượt khóa thủ công hoặc tổng quota)',
          valid_until: '2026-11-25T13:50:00Z',
        },
      },
      {
        request_id: '9d0f58dd-bd78-41af-d0e9-96e312c5d58e',
        device_id: DEVICE_MINH_ID,
        child_name: 'Bé Minh (Demo)',
        request_type: 'false_positive',
        created_at: '2026-11-26T14:45:00Z',
        reason: 'Em nghĩ trang library.example.test là thư viện trường, bị chặn nhầm ạ.',
        status: 'pending',
        decided_by: null,
        decided_at: null,
        payload: {
          domain: 'library.example.test',
        },
        grant_preview: {
          scope: 'Xem xét thêm domain vào danh sách cho phép hoặc giữ nguyên chặn',
          valid_until: '2026-11-26T16:59:59Z',
        },
      },
    ],
    commands: [
      {
        command_id: 'dc7fe46a-4f37-4b2d-90b2-a2a0f4f4cbaa',
        device_id: DEVICE_AN_ID,
        command_type: 'LOCK_SESSION',
        issued_at: '2026-11-25T14:02:00Z',
        expires_at: '2026-11-25T14:05:00Z',
        observed_at: '2026-11-25T14:02:04Z',
        status: 'executed',
        result_code: 'SESSION_STATE_CONFIRMED',
        payload: {},
      },
      {
        command_id: 'ed80f57b-5048-4c3e-a1c3-b3b10505dcbb',
        device_id: DEVICE_MINH_ID,
        command_type: 'TEMPORARY_TIME_EXEMPTION',
        issued_at: '2026-11-26T15:00:00Z',
        expires_at: '2026-11-26T15:05:00Z',
        observed_at: '2026-11-26T15:06:00Z',
        status: 'expired',
        result_code: 'EXPIRED_BEFORE_DELIVERY',
        payload: { duration_seconds: 900, scope: 'time_limits' },
      },
    ],
    reports: {
      [DEVICE_AN_ID]: {
        device_id: DEVICE_AN_ID,
        period: 'weekly',
        date_label: 'Tuần 23/11 – 29/11/2026 (Dữ liệu Demo)',
        measured_total_seconds: 6300,
        estimated_degraded_seconds: 0,
        telemetry_gaps_count: 0,
        blocked_attempts_count: 4,
        requests_count: 2,
        weekly_bars: [
          { label: 'T2', date: '2026-11-23', measured_seconds: 5700, estimated_degraded_seconds: 0 },
          { label: 'T3', date: '2026-11-24', measured_seconds: 4800, estimated_degraded_seconds: 0 },
          { label: 'T4', date: '2026-11-25', measured_seconds: 6600, estimated_degraded_seconds: 0 },
          { label: 'T5', date: '2026-11-26', measured_seconds: 6300, estimated_degraded_seconds: 0 },
          { label: 'T6', date: '2026-11-27', measured_seconds: 0, estimated_degraded_seconds: 0 },
          { label: 'T7', date: '2026-11-28', measured_seconds: 0, estimated_degraded_seconds: 0 },
          { label: 'CN', date: '2026-11-29', measured_seconds: 0, estimated_degraded_seconds: 0 },
        ],
        top_apps: [
          { name: 'chrome.exe', category: 'other', seconds: 3600, blocked_count: 0 },
          { name: 'scratch.exe', category: 'education', seconds: 2700, blocked_count: 0 },
          { name: 'sample-game.exe', category: 'games', seconds: 0, blocked_count: 2 },
        ],
        top_domains: [
          { name: 'khanacademy.org', category: 'education', seconds: 1800, blocked_count: 0 },
          { name: 'youtubekids.com', category: 'entertainment', seconds: 900, blocked_count: 0 },
          { name: 'games.example.test', category: 'games', seconds: 0, blocked_count: 2 },
        ],
      },
      [DEVICE_MINH_ID]: {
        device_id: DEVICE_MINH_ID,
        period: 'weekly',
        date_label: 'Tuần 23/11 – 29/11/2026 (Dữ liệu Demo)',
        measured_total_seconds: 3000,
        estimated_degraded_seconds: 600,
        telemetry_gaps_count: 1,
        blocked_attempts_count: 3,
        requests_count: 1,
        weekly_bars: [
          { label: 'T2', date: '2026-11-23', measured_seconds: 3600, estimated_degraded_seconds: 0 },
          { label: 'T3', date: '2026-11-24', measured_seconds: 3300, estimated_degraded_seconds: 300 },
          { label: 'T4', date: '2026-11-25', measured_seconds: 2400, estimated_degraded_seconds: 0 },
          { label: 'T5', date: '2026-11-26', measured_seconds: 3000, estimated_degraded_seconds: 600 },
          { label: 'T6', date: '2026-11-27', measured_seconds: 0, estimated_degraded_seconds: 0 },
          { label: 'T7', date: '2026-11-28', measured_seconds: 0, estimated_degraded_seconds: 0 },
          { label: 'CN', date: '2026-11-29', measured_seconds: 0, estimated_degraded_seconds: 0 },
        ],
        top_apps: [
          { name: 'scratch.exe', category: 'education', seconds: 2100, blocked_count: 0 },
          { name: 'chrome.exe', category: 'other', seconds: 900, blocked_count: 0 },
        ],
        top_domains: [
          { name: 'olm.vn', category: 'education', seconds: 1500, blocked_count: 0 },
          { name: 'blocked.example.test', category: 'inappropriate', seconds: 0, blocked_count: 3 },
        ],
      },
    },
    auditLogs: [
      {
        id: 'aud-001',
        actor_label: 'Phụ huynh (Demo)',
        actor_ip: '127.0.0.1',
        action: 'POLICY_UPDATED',
        resource_type: 'policy',
        before_summary: 'version=2, total_daily_seconds=5400',
        after_summary: 'version=3, total_daily_seconds=7200',
        created_at: '2026-11-26T15:00:00Z',
      },
      {
        id: 'aud-002',
        actor_label: 'Phụ huynh (Demo)',
        actor_ip: '127.0.0.1',
        action: 'COMMAND_ISSUED',
        resource_type: 'command',
        before_summary: 'manual_lock=false',
        after_summary: 'LOCK_SESSION -> status=executed (SESSION_STATE_CONFIRMED)',
        created_at: '2026-11-25T14:02:04Z',
      },
      {
        id: 'aud-003',
        actor_label: 'Phụ huynh (Demo)',
        actor_ip: '127.0.0.1',
        action: 'REQUEST_APPROVED',
        resource_type: 'request',
        before_summary: 'status=pending (Game xếp hình mẫu)',
        after_summary: 'status=approved, grant_duration=1800s',
        created_at: '2026-11-25T13:20:00Z',
      },
    ],
    deleteAllByChild: {
      [CHILD_AN_ID]: {
        status: 'idle',
        requested_at: null,
        server_purged: false,
        agent_cache_purged: false,
        message: 'Chưa có yêu cầu xóa dữ liệu.',
      },
      [CHILD_MINH_ID]: {
        status: 'idle',
        requested_at: null,
        server_purged: false,
        agent_cache_purged: false,
        message: 'Chưa có yêu cầu xóa dữ liệu.',
      },
    },
    enrollmentCodes: [],
  };
}

export function computeNextCommandStatus(
  type: CommandType,
  current: CommandStatus,
): { status: CommandStatus; result_code: string } {
  if (current === 'queued') {
    return { status: 'delivered', result_code: 'DELIVERED_TO_AGENT' };
  }
  if (current === 'delivered') {
    if (type === 'LOCK_SESSION') {
      return { status: 'executed', result_code: 'SESSION_STATE_CONFIRMED' };
    }
    return { status: 'executed', result_code: 'COMMAND_APPLIED' };
  }
  return { status: current, result_code: 'NO_CHANGE' };
}
