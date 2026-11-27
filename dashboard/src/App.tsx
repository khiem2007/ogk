import { useCallback, useEffect, useMemo, useState } from 'react';
import { createOgkClient, type ApiMode, type OgkClient } from './api/client';
import { AppsSchedulePage } from './pages/AppsSchedulePage';
import { ChildrenDevicesPage } from './pages/ChildrenDevicesPage';
import { CommandsPage } from './pages/CommandsPage';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { ProfilesTransparencyPage } from './pages/ProfilesTransparencyPage';
import { ReportsPage } from './pages/ReportsPage';
import { RequestsPage } from './pages/RequestsPage';
import { WebFilterPage } from './pages/WebFilterPage';
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
  UserRole,
} from './types/ogk';

type NavTab =
  | 'overview'
  | 'children'
  | 'apps'
  | 'web'
  | 'reports'
  | 'requests'
  | 'commands'
  | 'profiles';

function getInitialApiMode(): ApiMode {
  const configured = import.meta.env.VITE_API_MODE;
  if (configured === 'api' || configured === 'demo') {
    return configured;
  }
  return 'demo';
}

export function App() {
  const [apiMode, setApiMode] = useState<ApiMode>(getInitialApiMode);
  const [client, setClient] = useState<OgkClient>(() => createOgkClient(getInitialApiMode()));

  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [childrenList, setChildrenList] = useState<ChildProfile[]>([]);
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [selectedChildId, setSelectedChildId] = useState<string>('');
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');

  const [policySnapshot, setPolicySnapshot] = useState<PolicySnapshotResponse | null>(null);
  const [requests, setRequests] = useState<ChildRequestItem[]>([]);
  const [commands, setCommands] = useState<CommandItem[]>([]);
  const [reportPeriod, setReportPeriod] = useState<'daily' | 'weekly'>('weekly');
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [deleteStatus, setDeleteStatus] = useState<DeleteAllStatus>({
    status: 'idle',
    requested_at: null,
    server_purged: false,
    agent_cache_purged: false,
    message: 'Chưa có yêu cầu xóa dữ liệu.',
  });
  const [demoNetworkError, setDemoNetworkError] = useState(false);

  const handleModeChange = (nextMode: ApiMode) => {
    setApiMode(nextMode);
    setClient(createOgkClient(nextMode));
    setUser(null);
    setAuthError(null);
    setGlobalError(null);
    setDemoNetworkError(false);
  };

  const loadDeviceScopedData = useCallback(
    async (activeClient: OgkClient, childId: string, deviceId: string, period: 'daily' | 'weekly') => {
      const [reqs, audits, del] = await Promise.all([
        activeClient.listRequests(),
        activeClient.listAuditLogs(),
        childId
          ? activeClient.getDeleteAllStatus(childId)
          : Promise.resolve({
              status: 'idle' as const,
              requested_at: null,
              server_purged: false,
              agent_cache_purged: false,
              message: 'Chưa chọn hồ sơ trẻ.',
            }),
      ]);
      setRequests(reqs);
      setAuditLogs(audits);
      setDeleteStatus(del);

      if (deviceId) {
        const [pol, cmds, rep] = await Promise.all([
          activeClient.getPolicy(deviceId),
          activeClient.listCommands(deviceId),
          activeClient.getReport(deviceId, period),
        ]);
        setPolicySnapshot(pol);
        setCommands(cmds);
        setReport(rep);
      } else {
        setPolicySnapshot(null);
        setCommands([]);
        setReport(null);
      }
    },
    [],
  );

  const refreshAll = useCallback(
    async (activeClient: OgkClient, preferredChildId?: string, preferredDeviceId?: string) => {
      setGlobalError(null);
      try {
        const [kids, devs] = await Promise.all([
          activeClient.listChildren(),
          activeClient.listDevices(),
        ]);
        setChildrenList(kids);
        setDevices(devs);

        const nextChildId =
          kids.find((k) => k.id === (preferredChildId ?? selectedChildId))?.id ?? kids[0]?.id ?? '';
        setSelectedChildId(nextChildId);

        const childDevices = devs.filter((d) => d.child_id === nextChildId);
        const nextDeviceId =
          childDevices.find((d) => d.id === (preferredDeviceId ?? selectedDeviceId))?.id ??
          childDevices[0]?.id ??
          '';
        setSelectedDeviceId(nextDeviceId);

        await loadDeviceScopedData(activeClient, nextChildId, nextDeviceId, reportPeriod);
      } catch (err) {
        setGlobalError(err instanceof Error ? err.message : 'Lỗi tải dữ liệu từ server.');
      }
    },
    [loadDeviceScopedData, reportPeriod, selectedChildId, selectedDeviceId],
  );

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const me = await client.getMe();
        if (!active) return;
        setUser(me);
        if (me) {
          await refreshAll(client);
        }
      } catch (err) {
        if (!active) return;
        setAuthError(err instanceof Error ? err.message : 'Không kiểm tra được phiên đăng nhập.');
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [client]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedChild = useMemo(
    () => childrenList.find((c) => c.id === selectedChildId) ?? null,
    [childrenList, selectedChildId],
  );
  const childDevices = useMemo(
    () => devices.filter((d) => d.child_id === selectedChildId),
    [devices, selectedChildId],
  );
  const selectedDevice = useMemo(
    () => childDevices.find((d) => d.id === selectedDeviceId) ?? childDevices[0] ?? null,
    [childDevices, selectedDeviceId],
  );

  const isChildView = user?.role === 'child-view';
  const pendingRequestsCount = requests.filter((r) => r.status === 'pending').length;

  async function handleSelectChild(nextChildId: string) {
    setSelectedChildId(nextChildId);
    const nextDev = devices.find((d) => d.child_id === nextChildId)?.id ?? '';
    setSelectedDeviceId(nextDev);
    setGlobalError(null);
    try {
      await loadDeviceScopedData(client, nextChildId, nextDev, reportPeriod);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Không tải được dữ liệu trẻ.');
    }
  }

  async function handleSelectDevice(nextDeviceId: string) {
    setSelectedDeviceId(nextDeviceId);
    setGlobalError(null);
    try {
      await loadDeviceScopedData(client, selectedChildId, nextDeviceId, reportPeriod);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Không tải được dữ liệu thiết bị.');
    }
  }

  async function handlePeriodChange(nextPeriod: 'daily' | 'weekly') {
    setReportPeriod(nextPeriod);
    if (!selectedDevice) return;
    try {
      const rep = await client.getReport(selectedDevice.id, nextPeriod);
      setReport(rep);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'Lỗi tải báo cáo.');
    }
  }

  async function handleLogin(email: string, password: string) {
    setAuthError(null);
    try {
      const loggedIn = await client.login(email, password);
      setUser(loggedIn);
      await refreshAll(client);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Đăng nhập thất bại.');
    }
  }

  async function handleDemoQuickSwitch(role: UserRole) {
    if (!client.switchDemoRole) return;
    setAuthError(null);
    const switched = await client.switchDemoRole(role);
    setUser(switched);
    if (role === 'child-view') {
      setActiveTab('reports');
    }
    await refreshAll(client);
  }

  async function handleLogout() {
    try {
      await client.logout();
    } finally {
      setUser(null);
    }
  }

  const navItems: Array<{ id: NavTab; label: string; badge?: number }> = [
    { id: 'overview', label: 'Tổng quan' },
    { id: 'children', label: 'Trẻ & Thiết bị' },
    { id: 'apps', label: 'Ứng dụng & Khung giờ' },
    { id: 'web', label: 'Lọc web' },
    { id: 'reports', label: isChildView ? 'Hôm nay em đã dùng gì' : 'Báo cáo & Audit' },
    { id: 'requests', label: 'Yêu cầu', badge: pendingRequestsCount },
    { id: 'commands', label: 'Điều khiển từ xa' },
    { id: 'profiles', label: 'Hồ sơ & Minh bạch' },
  ];

  return (
    <div>
      <header className="ogk-top-banner">
        <div>
          <div className="ogk-brand-title">
            Người Bạn Đồng Hành · OpenGuard Kids (OGK)
          </div>
          <div className="ogk-brand-sub">
            Công cụ đồng hành trên Windows — minh bạch, có thỏa thuận, không chạy ẩn
          </div>
        </div>
        <div className="ogk-banner-badges">
          <span className="pill pill-public">Đang chạy công khai</span>
          <span className={`pill ${apiMode === 'demo' ? 'pill-demo' : 'pill-api'}`}>
            {apiMode === 'demo'
              ? 'Chế độ Demo / Fixture (chưa kết nối API TV1)'
              : 'API Server (/api/v1)'}
          </span>
          {user && (
            <button
              type="button"
              className="btn btn-sm mobile-menu-toggle"
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((v) => !v)}
            >
              Menu
            </button>
          )}
        </div>
      </header>

      {loading ? (
        <main style={{ maxWidth: 480, margin: '40px auto', padding: 16 }}>
          <section className="card">Đang kiểm tra phiên đăng nhập...</section>
        </main>
      ) : !user ? (
        <LoginPage
          mode={apiMode}
          onModeChange={handleModeChange}
          onLogin={handleLogin}
          onDemoQuickSwitch={apiMode === 'demo' ? handleDemoQuickSwitch : undefined}
          errorMessage={authError}
        />
      ) : (
        <div className="ogk-shell">
          <aside className={`ogk-sidebar ${mobileMenuOpen ? 'open' : ''}`} aria-label="Điều hướng chính">
            <div className="ogk-user-box">
              <div className="ogk-avatar" aria-hidden="true">
                {isChildView ? 'TR' : 'PH'}
              </div>
              <div style={{ minWidth: 0 }}>
                <strong style={{ display: 'block', fontSize: '0.92rem' }}>
                  {user.display_name}
                </strong>
                <span className="metric-sub" style={{ fontSize: '0.78rem' }}>
                  Vai trò: <code>{user.role}</code>
                </span>
              </div>
            </div>

            <nav className="ogk-nav">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`ogk-nav-btn ${activeTab === item.id ? 'active' : ''}`}
                  onClick={() => {
                    setActiveTab(item.id);
                    setMobileMenuOpen(false);
                  }}
                >
                  <span>{item.label}</span>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="ogk-nav-badge">{item.badge}</span>
                  )}
                </button>
              ))}
            </nav>

            <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {apiMode === 'demo' && client.switchDemoRole && (
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() =>
                    void handleDemoQuickSwitch(isChildView ? 'parent' : 'child-view')
                  }
                >
                  {isChildView ? 'Đổi sang Phụ huynh (Demo)' : 'Xem thử góc nhìn Trẻ (child-view)'}
                </button>
              )}
              {apiMode === 'demo' && client.setDemoNetworkError && (
                <button
                  type="button"
                  className={`btn btn-sm ${demoNetworkError ? 'btn-danger' : ''}`}
                  onClick={() => {
                    const next = !demoNetworkError;
                    client.setDemoNetworkError?.(next);
                    setDemoNetworkError(next);
                    if (!next) {
                      void refreshAll(client);
                    } else {
                      setGlobalError(
                        'Mô phỏng lỗi mạng / Server không phản hồi (Demo Test Mode).',
                      );
                    }
                  }}
                >
                  {demoNetworkError ? 'Tắt mô phỏng lỗi mạng' : 'Mô phỏng lỗi mạng (Test)'}
                </button>
              )}
              <button type="button" className="btn btn-sm" onClick={() => void handleLogout()}>
                Đăng xuất
              </button>
            </div>
          </aside>

          <main className="ogk-main">
            <div className="ogk-toolbar">
              <div className="ogk-selector-group">
                <label className="ogk-field-inline">
                  <span>Hồ sơ trẻ:</span>
                  <select
                    value={selectedChildId}
                    onChange={(e) => void handleSelectChild(e.target.value)}
                    aria-label="Bộ chọn trẻ"
                  >
                    {childrenList.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.display_name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="ogk-field-inline">
                  <span>Thiết bị:</span>
                  <select
                    value={selectedDevice?.id ?? ''}
                    onChange={(e) => void handleSelectDevice(e.target.value)}
                    aria-label="Bộ chọn thiết bị"
                  >
                    {childDevices.length === 0 ? (
                      <option value="">Chưa có thiết bị</option>
                    ) : (
                      childDevices.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name} ({d.connectivity})
                        </option>
                      ))
                    )}
                  </select>
                </label>
              </div>

              <button
                type="button"
                className="btn btn-sm"
                onClick={() => void refreshAll(client)}
              >
                Làm mới dữ liệu
              </button>
            </div>

            {isChildView && (
              <div className="alert alert-info" role="status">
                <strong>Chế độ xem của trẻ (child-view — NT5):</strong> Em được xem minh bạch toàn
                bộ báo cáo và nhật ký sửa luật, nhưng không thể thay đổi chính sách hay tự duyệt yêu
                cầu.
              </div>
            )}

            {globalError && (
              <div className="alert alert-danger" role="alert">
                <strong>Lỗi kết nối / thao tác:</strong> {globalError}
              </div>
            )}

            {activeTab === 'overview' && selectedChild && (
              <OverviewPage
                child={selectedChild}
                device={selectedDevice}
                policySnapshot={policySnapshot}
                report={report}
                requests={requests}
                onGoToRequests={() => setActiveTab('requests')}
              />
            )}

            {activeTab === 'children' && (
              <ChildrenDevicesPage
                childrenList={childrenList}
                devices={devices}
                selectedChildId={selectedChildId}
                selectedDeviceId={selectedDevice?.id ?? ''}
                isReadOnly={isChildView}
                isDemoMode={apiMode === 'demo'}
                onSelectChild={(id) => void handleSelectChild(id)}
                onSelectDevice={(id) => void handleSelectDevice(id)}
                onCreateChild={async (input) => {
                  const created = await client.createChild(input);
                  await refreshAll(client, created.id, '');
                }}
                onCreateEnrollmentCode={(childId, devName) =>
                  client.createEnrollmentCode(childId, devName)
                }
                onRevokeDevice={async (devId) => {
                  await client.revokeDevice(devId);
                  await refreshAll(client);
                }}
                onDemoClaimCode={
                  client.claimDemoEnrollmentCode
                    ? async (code) => {
                        const dev = await client.claimDemoEnrollmentCode!(code);
                        await refreshAll(client, dev.child_id, dev.id);
                      }
                    : undefined
                }
                onDemoExpireCode={client.simulateDemoExpiryEnrollmentCode?.bind(client)}
              />
            )}

            {activeTab === 'apps' && (
              <AppsSchedulePage
                device={selectedDevice}
                snapshot={policySnapshot}
                isReadOnly={isChildView}
                isDemoMode={apiMode === 'demo'}
                onSavePolicy={async (expectedVersion: number, policy: PolicyDocument) => {
                  if (!selectedDevice) return;
                  await client.updatePolicy(selectedDevice.id, expectedVersion, policy);
                  await refreshAll(client, selectedChildId, selectedDevice.id);
                }}
                onDemoBumpServerVersion={
                  selectedDevice && client.simulateDemoServerVersionBump
                    ? () => {
                        client.simulateDemoServerVersionBump!(selectedDevice.id);
                        setDevices((prev) =>
                          prev.map((d) =>
                            d.id === selectedDevice.id
                              ? { ...d, server_policy_version: d.server_policy_version + 1 }
                              : d,
                          ),
                        );
                      }
                    : undefined
                }
              />
            )}

            {activeTab === 'web' && (
              <WebFilterPage
                device={selectedDevice}
                snapshot={policySnapshot}
                isReadOnly={isChildView}
                onSavePolicy={async (expectedVersion: number, policy: PolicyDocument) => {
                  if (!selectedDevice) return;
                  await client.updatePolicy(selectedDevice.id, expectedVersion, policy);
                  await refreshAll(client, selectedChildId, selectedDevice.id);
                }}
              />
            )}

            {activeTab === 'reports' && selectedChild && (
              <ReportsPage
                child={selectedChild}
                device={selectedDevice}
                report={report}
                auditLogs={auditLogs}
                deleteStatus={deleteStatus}
                period={reportPeriod}
                isChildView={isChildView}
                isDemoMode={apiMode === 'demo'}
                onPeriodChange={(p) => void handlePeriodChange(p)}
                onRequestDeleteAll={async (childId) => {
                  const st = await client.requestDeleteAllChildData(childId);
                  setDeleteStatus(st);
                  await refreshAll(client, childId, selectedDevice?.id);
                }}
                onDemoCompleteAgentPurge={
                  client.completeDemoAgentPurge
                    ? async (childId) => {
                        const st = await client.completeDemoAgentPurge!(childId);
                        setDeleteStatus(st);
                      }
                    : undefined
                }
              />
            )}

            {activeTab === 'requests' && (
              <RequestsPage
                requests={requests}
                isReadOnly={isChildView}
                onDecide={async (reqId, decision) => {
                  await client.decideRequest(reqId, decision);
                  await refreshAll(client);
                }}
              />
            )}

            {activeTab === 'commands' && (
              <CommandsPage
                device={selectedDevice}
                commands={commands}
                isReadOnly={isChildView}
                isDemoMode={apiMode === 'demo'}
                onIssueCommand={async (type: CommandType) => {
                  if (!selectedDevice) return;
                  await client.issueCommand(selectedDevice.id, type);
                  await refreshAll(client, selectedChildId, selectedDevice.id);
                }}
                onDemoTransitionCommand={
                  client.simulateDemoCommandTransition
                    ? async (commandId: string, target?: CommandStatus) => {
                        await client.simulateDemoCommandTransition!(commandId, target);
                        await refreshAll(client, selectedChildId, selectedDevice?.id);
                      }
                    : undefined
                }
              />
            )}

            {activeTab === 'profiles' && selectedChild && (
              <ProfilesTransparencyPage
                child={selectedChild}
                snapshot={policySnapshot}
                isReadOnly={isChildView}
                onApplyTemplate={async (expectedVersion, policy) => {
                  if (!selectedDevice) return;
                  await client.updatePolicy(selectedDevice.id, expectedVersion, policy);
                  await refreshAll(client, selectedChildId, selectedDevice.id);
                }}
                onAcknowledgeConsent={async (childId) => {
                  await client.updateChild(childId, {
                    consent_acknowledged_at: new Date().toISOString(),
                  });
                  await refreshAll(client, childId, selectedDevice?.id);
                }}
              />
            )}
          </main>
        </div>
      )}
    </div>
  );
}

export default App;
