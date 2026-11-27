import { ConnectivityBadge } from '../components/StatusBadges';
import type {
  ChildProfile,
  ChildRequestItem,
  DeviceInfo,
  PolicySnapshotResponse,
  ReportSummary,
} from '../types/ogk';
import { DAY_LABELS, formatDuration, formatTimeShort } from '../utils/validation';

interface OverviewPageProps {
  child: ChildProfile;
  device: DeviceInfo | null;
  policySnapshot: PolicySnapshotResponse | null;
  report: ReportSummary | null;
  requests: ChildRequestItem[];
  onGoToRequests: () => void;
}

export function OverviewPage({
  child,
  device,
  policySnapshot,
  report,
  requests,
  onGoToRequests,
}: OverviewPageProps) {
  const pendingCount = requests.filter((r) => r.status === 'pending').length;
  const totalQuota = policySnapshot?.policy.quotas.total_daily_seconds ?? 7200;
  const entQuota = policySnapshot?.policy.quotas.category_daily_seconds.entertainment ?? 3600;
  const todayMeasured = report?.weekly_bars[3]?.measured_seconds ?? report?.measured_total_seconds ?? 0;
  const entRemaining = Math.max(0, Math.min(entQuota, device?.remaining_seconds_today ?? 0));
  const usedPercent = totalQuota > 0 ? Math.min(100, Math.round((todayMeasured / totalQuota) * 100)) : 0;
  const entPercent = entQuota > 0 ? Math.min(100, Math.round((entRemaining / entQuota) * 100)) : 0;

  const maxWeekly = Math.max(
    3600,
    ...(report?.weekly_bars.map((b) => b.measured_seconds + b.estimated_degraded_seconds) ?? [3600]),
  );

  // JS getDay(): 0=Sun..6=Sat -> convert to Python weekday 0=Mon..6=Sun
  const jsDay = new Date().getDay();
  const todayWeekday = jsDay === 0 ? 6 : jsDay - 1;
  const todaySlots =
    policySnapshot?.policy.schedule.filter((s) => s.day_of_week === todayWeekday) ?? [];

  return (
    <div>
      <section className="card">
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <h2 className="card-title" style={{ fontSize: '1.3rem' }}>
              Tổng quan — {child.display_name}
            </h2>
            <p className="metric-sub" style={{ margin: 0 }}>
              Nhóm tuổi {child.age_band} · múi giờ {child.timezone}
              {device ? ` · máy "${device.name}"` : ' · chưa ghép thiết bị'} · Phần mềm chạy công khai trên máy của con.
            </p>
          </div>
          {device && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
              <ConnectivityBadge state={device.connectivity} />
              <span className="metric-sub">
                Đồng bộ cuối: {formatTimeShort(device.last_seen_at)} · Server v
                {device.server_policy_version} / Thiết bị đã áp v
                {device.applied_policy_version ?? '—'}
              </span>
            </div>
          )}
        </div>
      </section>

      {device?.connectivity === 'degraded' && (
        <div className="alert alert-warn" role="status">
          <strong>Cảnh báo Degraded (ADR-0001):</strong> Tray/Helper trong phiên trẻ tạm mất kết nối
          IPC. Bộ đếm không bịa thời gian ứng dụng; khoảng thiếu telemetry được ghi tách riêng khỏi
          thời gian đo thật.
        </div>
      )}

      {device?.manual_lock && (
        <div className="alert alert-danger" role="status">
          <strong>Thiết bị đang ở trạng thái Khóa thủ công (`MANUAL_LOCK`):</strong> Phiên trẻ sẽ bị
          khóa cho tới khi phụ huynh gửi lệnh hủy khóa (`CLEAR_MANUAL_LOCK`).
        </div>
      )}

      {device?.clock_suspect && (
        <div className="alert alert-warn" role="status">
          <strong>Cảnh báo đồng hồ (`clock_suspect`):</strong> Agent phát hiện sai lệch giờ hệ thống
          so với monotonic clock; hạn mức ngày không bị đặt lại.
        </div>
      )}

      <div className="ogk-grid-3">
        <article className="card">
          <div className="metric-sub">Thời gian dùng máy hôm nay (đo được)</div>
          <div className="metric-value">
            {formatDuration(todayMeasured)}{' '}
            <span style={{ fontSize: '0.95rem', fontWeight: 500, color: 'var(--text-muted)' }}>
              / {formatDuration(totalQuota)}
            </span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${usedPercent}%` }} />
          </div>
        </article>

        <article className="card">
          <div className="metric-sub">Ngân sách giải trí còn lại hôm nay</div>
          <div className="metric-value" style={{ color: '#b45309' }}>
            {formatDuration(entRemaining)}{' '}
            <span style={{ fontSize: '0.95rem', fontWeight: 500, color: 'var(--text-muted)' }}>
              / {formatDuration(entQuota)}
            </span>
          </div>
          <div className="progress-track">
            <div className="progress-fill warn" style={{ width: `${entPercent}%` }} />
          </div>
        </article>

        <article className="card">
          <div className="metric-sub">Yêu cầu đang chờ duyệt</div>
          <div className="metric-value">{pendingCount}</div>
          <button type="button" className="btn btn-sm" onClick={onGoToRequests}>
            Xem yêu cầu →
          </button>
        </article>
      </div>

      <div className="ogk-grid-2">
        <section className="card">
          <h3 className="card-title">THỜI GIAN DÙNG MÁY TRONG TUẦN</h3>
          <p className="metric-sub" style={{ marginTop: 0 }}>
            Tách biệt thời gian đo thật (xanh) và thời gian ước lượng khi degraded (cam).
          </p>
          <div className="bar-chart" aria-label="Biểu đồ thời gian dùng máy trong tuần">
            {(report?.weekly_bars ?? []).map((bar) => {
              const measuredPct = Math.round((bar.measured_seconds / maxWeekly) * 100);
              const estPct = Math.round((bar.estimated_degraded_seconds / maxWeekly) * 100);
              const totalMin = Math.round(
                (bar.measured_seconds + bar.estimated_degraded_seconds) / 60,
              );
              return (
                <div key={bar.label} className="bar-col">
                  <span className="metric-sub" style={{ fontSize: '0.75rem' }}>
                    {totalMin}p
                  </span>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: 42,
                      height: '120px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'flex-end',
                    }}
                  >
                    {estPct > 0 && (
                      <div
                        className="bar-rect degraded"
                        style={{ height: `${Math.max(4, estPct)}%` }}
                        title={`Ước lượng degraded: ${Math.round(bar.estimated_degraded_seconds / 60)}p`}
                      />
                    )}
                    <div
                      className="bar-rect"
                      style={{ height: `${Math.max(3, measuredPct)}%` }}
                      title={`Đo được: ${Math.round(bar.measured_seconds / 60)}p`}
                    />
                  </div>
                  <strong style={{ fontSize: '0.82rem' }}>{bar.label}</strong>
                </div>
              );
            })}
          </div>
        </section>

        <section className="card">
          <h3 className="card-title">
            KHUNG GIỜ ĐƯỢC PHÉP HÔM NAY ({DAY_LABELS[todayWeekday]})
          </h3>
          {todaySlots.length === 0 ? (
            <p className="metric-sub">Hôm nay chưa cấu hình khung giờ cho phép nào.</p>
          ) : (
            <ul style={{ margin: '8px 0', paddingLeft: 18 }}>
              {todaySlots.map((slot, idx) => (
                <li key={`${slot.start}-${idx}`} style={{ marginBottom: 6 }}>
                  <strong>
                    {slot.start} – {slot.end}
                  </strong>{' '}
                  <span className="metric-sub">(nửa mở [start, end))</span>
                </li>
              ))}
            </ul>
          )}
          <div className="alert alert-info" style={{ marginTop: 14, marginBottom: 0 }}>
            <strong>Ghi chú minh bạch (NT2):</strong> Phần mềm chỉ ghi tên ứng dụng đang dùng và
            tổng thời lượng; không ghi tiêu đề cửa sổ, nội dung gõ hay ảnh màn hình.
          </div>
        </section>
      </div>
    </div>
  );
}
