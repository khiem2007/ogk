import { useState, type FormEvent } from 'react';
import { ConnectivityBadge } from '../components/StatusBadges';
import type { ChildProfile, DeviceInfo, EnrollmentCodeResponse } from '../types/ogk';
import { formatTimeShort } from '../utils/validation';

interface ChildrenDevicesPageProps {
  childrenList: ChildProfile[];
  devices: DeviceInfo[];
  selectedChildId: string;
  selectedDeviceId: string;
  isReadOnly: boolean;
  isDemoMode: boolean;
  onSelectChild: (childId: string) => void;
  onSelectDevice: (deviceId: string) => void;
  onCreateChild: (input: {
    display_name: string;
    age_band: '6-8' | '9-11' | '12-14';
    timezone: string;
  }) => Promise<void>;
  onCreateEnrollmentCode: (childId: string, deviceName: string) => Promise<EnrollmentCodeResponse>;
  onRevokeDevice: (deviceId: string) => Promise<void>;
  onDemoClaimCode?: (code: string) => Promise<void>;
  onDemoExpireCode?: (code: string) => void;
}

export function ChildrenDevicesPage({
  childrenList,
  devices,
  selectedChildId,
  selectedDeviceId,
  isReadOnly,
  isDemoMode,
  onSelectChild,
  onSelectDevice,
  onCreateChild,
  onCreateEnrollmentCode,
  onRevokeDevice,
  onDemoClaimCode,
  onDemoExpireCode,
}: ChildrenDevicesPageProps) {
  const [childName, setChildName] = useState('');
  const [ageBand, setAgeBand] = useState<'6-8' | '9-11' | '12-14'>('9-11');
  const [timezone, setTimezone] = useState('Asia/Ho_Chi_Minh');
  const [deviceName, setDeviceName] = useState('PC-Phòng-học-2');
  const [generatedCode, setGeneratedCode] = useState<EnrollmentCodeResponse | null>(null);
  const [codeTestInput, setCodeTestInput] = useState('');
  const [feedback, setFeedback] = useState<{ kind: 'info' | 'danger'; text: string } | null>(null);

  async function handleAddChild(e: FormEvent) {
    e.preventDefault();
    if (!childName.trim()) {
      setFeedback({ kind: 'danger', text: 'Tên hiển thị của trẻ không được để trống.' });
      return;
    }
    try {
      await onCreateChild({ display_name: childName.trim(), age_band: ageBand, timezone });
      setChildName('');
      setFeedback({ kind: 'info', text: 'Đã tạo hồ sơ trẻ mới.' });
    } catch (err) {
      setFeedback({
        kind: 'danger',
        text: err instanceof Error ? err.message : 'Không thể tạo hồ sơ trẻ.',
      });
    }
  }

  async function handleGenerateCode(e: FormEvent) {
    e.preventDefault();
    try {
      const res = await onCreateEnrollmentCode(selectedChildId, deviceName);
      setGeneratedCode(res);
      setCodeTestInput(res.code);
      setFeedback({
        kind: 'info',
        text: `Đã tạo mã ghép 8 ký tự "${res.code}" (hiệu lực 10 phút, dùng một lần).`,
      });
    } catch (err) {
      setFeedback({
        kind: 'danger',
        text: err instanceof Error ? err.message : 'Không thể tạo mã ghép.',
      });
    }
  }

  async function handleTestClaim() {
    if (!onDemoClaimCode) return;
    try {
      await onDemoClaimCode(codeTestInput);
      setFeedback({ kind: 'info', text: `Ghép thiết bị thành công với mã "${codeTestInput}".` });
    } catch (err) {
      setFeedback({
        kind: 'danger',
        text: err instanceof Error ? err.message : 'Mã ghép bị từ chối.',
      });
    }
  }

  const childDevices = devices.filter((d) => d.child_id === selectedChildId);

  return (
    <div>
      {feedback && (
        <div
          className={`alert ${feedback.kind === 'danger' ? 'alert-danger' : 'alert-info'}`}
          role="alert"
        >
          {feedback.text}
        </div>
      )}

      <div className="ogk-grid-2">
        <section className="card">
          <h2 className="card-title">Hồ sơ trẻ trong gia đình</h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 14px' }}>
            {childrenList.map((c) => (
              <li
                key={c.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 10px',
                  border: '1px solid var(--border-soft)',
                  borderRadius: 8,
                  marginBottom: 8,
                  background: c.id === selectedChildId ? 'var(--accent-soft)' : '#fff',
                }}
              >
                <div>
                  <strong>{c.display_name}</strong>
                  <div className="metric-sub">
                    Nhóm tuổi {c.age_band} · {c.timezone}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onSelectChild(c.id)}
                >
                  {c.id === selectedChildId ? 'Đang chọn' : 'Chọn'}
                </button>
              </li>
            ))}
          </ul>

          {!isReadOnly && (
            <form
              onSubmit={handleAddChild}
              style={{ display: 'flex', flexDirection: 'column', gap: 10 }}
            >
              <h3 className="card-title" style={{ fontSize: '0.95rem' }}>
                Thêm hồ sơ trẻ
              </h3>
              <input
                className="ogk-input"
                placeholder="Tên trẻ (ví dụ: Bé Hoa)"
                value={childName}
                onChange={(e) => setChildName(e.target.value)}
                aria-label="Tên hồ sơ trẻ mới"
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <select
                  className="ogk-select"
                  value={ageBand}
                  onChange={(e) => setAgeBand(e.target.value as '6-8' | '9-11' | '12-14')}
                  aria-label="Nhóm tuổi"
                >
                  <option value="6-8">6–8 tuổi</option>
                  <option value="9-11">9–11 tuổi</option>
                  <option value="12-14">12–14 tuổi</option>
                </select>
                <input
                  className="ogk-input"
                  style={{ flex: 1 }}
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  aria-label="Múi giờ IANA"
                />
              </div>
              <button type="submit" className="btn btn-primary">
                Tạo hồ sơ trẻ
              </button>
            </form>
          )}
        </section>

        <section className="card">
          <h2 className="card-title">Ghép thiết bị Windows (Enrollment 8 ký tự / 10 phút)</h2>
          <p className="metric-sub">
            Mã chỉ hiển thị một lần tại thời điểm tạo; agent dùng mã này để nhận token riêng thiết bị
            (đây là điểm ghi nhận sự đồng ý của phụ huynh theo Nghị định 13/2023).
          </p>

          {!isReadOnly && (
            <form onSubmit={handleGenerateCode} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <input
                className="ogk-input"
                style={{ flex: 1 }}
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                placeholder="Tên máy tính (vd: PC-Phong-hoc)"
                aria-label="Tên thiết bị cần ghép"
              />
              <button type="submit" className="btn btn-primary">
                Tạo mã ghép
              </button>
            </form>
          )}

          {generatedCode && (
            <div className="alert alert-info">
              <div>
                <strong>Mã ghép:</strong>{' '}
                <code style={{ fontSize: '1.15rem', letterSpacing: 2 }}>{generatedCode.code}</code>
              </div>
              <div className="metric-sub">
                Thiết bị dự kiến: {generatedCode.device_name} · Hết hạn lúc:{' '}
                {formatTimeShort(generatedCode.expires_at)}
              </div>
            </div>
          )}

          {isDemoMode && !isReadOnly && (
            <div
              style={{
                borderTop: '1px dashed var(--border-soft)',
                paddingTop: 12,
                marginTop: 12,
              }}
            >
              <div className="metric-sub" style={{ marginBottom: 6 }}>
                Kiểm thử luồng ghép thiết bị (Demo / T02):
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input
                  className="ogk-input"
                  value={codeTestInput}
                  onChange={(e) => setCodeTestInput(e.target.value)}
                  placeholder="Nhập mã 8 ký tự"
                  aria-label="Mã ghép thử nghiệm"
                />
                <button type="button" className="btn btn-sm" onClick={() => void handleTestClaim()}>
                  Mô phỏng Agent ghép bằng mã
                </button>
                {generatedCode && onDemoExpireCode && (
                  <button
                    type="button"
                    className="btn btn-sm btn-warn"
                    onClick={() => {
                      onDemoExpireCode(generatedCode.code);
                      setFeedback({
                        kind: 'info',
                        text: `Đã đánh dấu mã ${generatedCode.code} hết hạn để thử T02.`,
                      });
                    }}
                  >
                    Đánh dấu mã hết hạn
                  </button>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="card">
        <h2 className="card-title">Thiết bị của trẻ đang chọn</h2>
        {childDevices.length === 0 ? (
          <p className="metric-sub">Trẻ này chưa có thiết bị nào được ghép.</p>
        ) : (
          <div className="ogk-table-wrap">
            <table className="ogk-table">
              <thead>
                <tr>
                  <th>Tên thiết bị</th>
                  <th>Windows SID</th>
                  <th>Trạng thái</th>
                  <th>Policy (Server / Thiết bị)</th>
                  <th>Lần cuối đồng bộ</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {childDevices.map((dev) => (
                  <tr key={dev.id}>
                    <td>
                      <strong>{dev.name}</strong>
                      {dev.id === selectedDeviceId && (
                        <span className="pill pill-api" style={{ marginLeft: 8 }}>
                          Đang xem
                        </span>
                      )}
                    </td>
                    <td>
                      <code>{dev.windows_sid ?? 'Chưa báo cáo'}</code>
                    </td>
                    <td>
                      {dev.revoked_at ? (
                        <span className="pill pill-offline">Đã thu hồi</span>
                      ) : (
                        <ConnectivityBadge state={dev.connectivity} />
                      )}
                    </td>
                    <td>
                      Server v{dev.server_policy_version} / Applied v
                      {dev.applied_policy_version ?? '—'} ({dev.policy_integrity_status})
                    </td>
                    <td>{formatTimeShort(dev.last_seen_at)}</td>
                    <td style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="btn btn-sm"
                        onClick={() => onSelectDevice(dev.id)}
                      >
                        Chọn máy
                      </button>
                      {!isReadOnly && !dev.revoked_at && (
                        <button
                          type="button"
                          className="btn btn-sm btn-danger"
                          onClick={() => void onRevokeDevice(dev.id)}
                        >
                          Thu hồi quyền
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
