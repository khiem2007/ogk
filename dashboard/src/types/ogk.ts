export type UserRole = 'parent' | 'child-view' | 'admin';

export type AppCategory = 'education' | 'entertainment' | 'games' | 'other';

export type WebCategory =
  | 'education'
  | 'entertainment'
  | 'social'
  | 'games'
  | 'inappropriate'
  | 'uncategorized';

export type RuleDecision = 'allow' | 'restrict' | 'block';

export type ConnectivityState = 'online' | 'offline' | 'degraded';

export type RequestStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export type CommandType =
  | 'LOCK_SESSION'
  | 'CLEAR_MANUAL_LOCK'
  | 'TEMPORARY_TIME_EXEMPTION'
  | 'EXEMPT_UNTIL_LOCAL_DAY_END';

export type CommandStatus =
  | 'queued'
  | 'delivered'
  | 'executed'
  | 'failed'
  | 'expired';

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  csrf_token: string;
}

export interface ChildProfile {
  id: string;
  display_name: string;
  age_band: '6-8' | '9-11' | '12-14';
  timezone: string;
  consent_acknowledged_at: string | null;
  explanation_version: string;
}

export interface DeviceInfo {
  id: string;
  child_id: string;
  name: string;
  windows_sid: string | null;
  connectivity: ConnectivityState;
  last_seen_at: string;
  server_policy_version: number;
  applied_policy_version: number | null;
  policy_integrity_status: 'verified' | 'mismatch' | 'pending';
  revoked_at: string | null;
  remaining_seconds_today: number;
  manual_lock: boolean;
  clock_suspect: boolean;
}

export interface EnrollmentCodeResponse {
  code: string;
  expires_at: string;
  child_id: string;
  device_name: string;
}

export interface ScheduleSlot {
  day_of_week: number; // 0=Monday .. 6=Sunday
  start: string; // HH:MM
  end: string; // HH:MM
}

export interface AppRuleItem {
  app_id: string;
  display_name: string;
  executable_name: string;
  executable_sha256: string;
  category: AppCategory;
  decision: 'allow' | 'block';
}

export interface WebCategoryRule {
  category: WebCategory;
  decision: RuleDecision;
  domains: string[];
}

export interface PolicyDocument {
  timezone: string;
  idle_threshold_seconds: number;
  manual_lock: boolean;
  schedule: ScheduleSlot[];
  quotas: {
    total_daily_seconds: number;
    weekend_daily_seconds: number;
    category_daily_seconds: Record<AppCategory, number>;
  };
  apps: AppRuleItem[];
  domains: {
    mode: 'blocklist' | 'allowlist';
    hard_block: string[];
    explicit_allow: string[];
    protected_allowlist: string[];
    restricted_schedule: ScheduleSlot[];
    category_rules: WebCategoryRule[];
    safesearch_enabled: boolean;
    safesearch_verified_by_dns: boolean;
  };
}

export interface PolicySnapshotResponse {
  schema_version: 1;
  device_id: string;
  policy_version: number;
  issued_at: string;
  integrity_tag: string;
  policy: PolicyDocument;
}

export interface ChildRequestItem {
  request_id: string;
  device_id: string;
  child_name: string;
  request_type: 'time_extension' | 'app_exception' | 'false_positive';
  created_at: string;
  reason: string;
  status: RequestStatus;
  decided_by: string | null;
  decided_at: string | null;
  payload: {
    amount_seconds?: number;
    local_date?: string;
    app_id?: string;
    app_name?: string;
    duration_seconds?: number;
    domain?: string;
  };
  grant_preview?: {
    scope: string;
    valid_until: string;
  };
}

export interface CommandItem {
  command_id: string;
  device_id: string;
  command_type: CommandType;
  issued_at: string;
  expires_at: string;
  observed_at: string | null;
  status: CommandStatus;
  result_code: string | null;
  payload: Record<string, unknown>;
}

export interface DailyBarPoint {
  label: string;
  date: string;
  measured_seconds: number;
  estimated_degraded_seconds: number;
}

export interface TopUsageItem {
  name: string;
  category: string;
  seconds: number;
  blocked_count: number;
}

export interface ReportSummary {
  device_id: string;
  period: 'daily' | 'weekly';
  date_label: string;
  measured_total_seconds: number;
  estimated_degraded_seconds: number;
  telemetry_gaps_count: number;
  blocked_attempts_count: number;
  requests_count: number;
  weekly_bars: DailyBarPoint[];
  top_apps: TopUsageItem[];
  top_domains: TopUsageItem[];
}

export interface AuditLogItem {
  id: string;
  actor_label: string;
  actor_ip: string;
  action: string;
  resource_type: string;
  before_summary: string;
  after_summary: string;
  created_at: string;
}

export interface DeleteAllStatus {
  status: 'idle' | 'server_deleted_pending_agent' | 'completed';
  requested_at: string | null;
  server_purged: boolean;
  agent_cache_purged: boolean;
  message: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Array<{ field: string; reason: string }>;
  };
}
