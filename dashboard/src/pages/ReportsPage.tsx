import { useState } from 'react';
import type {
  AuditLogItem,
  ChildProfile,
  DeleteAllStatus,
  DeviceInfo,
  ReportSummary,
} from '../types/ogk';
import { formatDuration, formatTimeShort } from '../utils/validation';

interface ReportsPageProps {
  child: ChildProfile;
  device: DeviceInfo | null;
  report: ReportSummary | null;
  auditLogs: AuditLogItem[];
  deleteStatus: DeleteAllStatus;
  period: 'daily' | 'weekly';
  isChildView: boolean;
  isDemoMode: boolean;
  onPeriodChange: (period: 'daily' | 'weekly') => void;
  onRequestDeleteAll: (childId: string) => Promise<void>;
  onDemoCompleteAgentPurge?: (childId: string) => Promise<void>;
}

export function ReportsPage({
  child,
  device,
  report,
  auditLogs,
  deleteStatus,
  period,
  isChildView,
  isDemoMode,
  onPeriodChange,
  onRequestDeleteAll,
  onDemoCompleteAgentPurge,
}: ReportsPageProps) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  return (
    <div>
      <section className="card">
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <h2 className="card-title">
              {isChildView
                ? `Hôm nay em đã dùng gì & Nhật ký minh bạch — ${child.display_name}`
                : `Báo cáo hoạt động & Nhật ký kiểm toán — ${child.display_name}`}
            </h2>
            <p className="metric-sub" style={{ margin: 0 }}>
              {isChildView
                ? 'Em đang xem cùng số liệu và lịch sử thay đổi luật với phụ huynh (NT5).'
                : `Tổng hợp từ interval đã chống trùng (retention 90 ngày). Thời gian ứng dụng là tập con thời gian máy, không cộng đôi.`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              type="button"
              className={`btn btn-sm ${period === 'daily' ? 'btn-primary' : ''}`}
              onClick={() => onPeriodChange('daily')}
            >
              Theo ngày
            </button>
            <button
              type="button"
              className={`btn btn-sm ${period === 'weekly' ? 'btn-primary' : ''}`}
              onClick={() => onPeriodChange('weekly')}
            >
              Theo tuần
            </button>
          </div>
        </div>
      </section>

      {report && (
        <>
          {report.telemetry_gaps_count > 0 && (
            <div className="alert alert-warn" role="status">
              <strong>Phát hiện {report.telemetry_gaps_count} khoảng thiếu telemetry:</strong> Có{' '}
              {formatDuration(report.estimated_degraded_seconds)} được gắn nhãn ước lượng khi Tray
              mất kết nối, tách biệt hoàn toàn với thời gian đo được.
            </div>
          )}

          <div className="ogk-grid-3">
            <article className="card">
              <div className="metric-sub">Thời gian đo thật ({report.date_label})</div>
              <div className="metric-value">{formatDuration(report.measured_total_seconds)}</div>
            </article>
            <article className="card">
              <div className="metric-sub">Ước lượng khi degraded / Số lần bị chặn</div>
              <div className="metric-value" style={{ fontSize: '1.35rem' }}>
                {formatDuration(report.estimated_degraded_seconds)} · {report.blocked_attempts_count}{' '}
                lần chặn
              </div>
            </article>
            <article className="card">
              <div className="metric-sub">Tổng số yêu cầu đã ghi nhận</div>
              <div className="metric-value">{report.requests_count}</div>
            </article>
          </div>

          <div className="ogk-grid-2">
            <section className="card">
              <h3 className="card-title">Top 10 ứng dụng</h3>
              {report.top_apps.length === 0 ? (
                <p className="metric-sub">Chưa có dữ liệu ứng dụng (hoặc đã được xóa).</p>
              ) : (
                <table className="ogk-table">
                  <thead>
                    <tr>
                      <th>Ứng dụng</th>
                      <th>Nhóm</th>
                      <th>Thời lượng</th>
                      <th>Bị chặn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.top_apps.slice(0, 10).map((item) => (
                      <tr key={item.name}>
                        <td>
                          <code>{item.name}</code>
                        </td>
                        <td>{item.category}</td>
                        <td>{formatDuration(item.seconds)}</td>
                        <td>{item.blocked_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            <section className="card">
              <h3 className="card-title">Top 10 tên miền cấp hai</h3>
              {report.top_domains.length === 0 ? (
                <p className="metric-sub">Chưa có dữ liệu tên miền (hoặc đã được xóa).</p>
              ) : (
                <table className="ogk-table">
                  <thead>
                    <tr>
                      <th>Tên miền</th>
                      <th>Nhóm</th>
                      <th>Thời lượng/Ước lượng</th>
                      <th>Bị chặn</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.top_domains.slice(0, 10).map((item) => (
                      <tr key={item.name}>
                        <td>
                          <code>{item.name}</code>
                        </td>
                        <td>{item.category}</td>
                        <td>{item.seconds > 0 ? formatDuration(item.seconds) : '—'}</td>
                        <td>{item.blocked_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>
        </>
      )}

      <section className="card">
        <h3 className="card-title">Nhật ký kiểm toán thay đổi luật (Audit Log — NT5 / F4.3)</h3>
        <div className="ogk-table-wrap">
          <table className="ogk-table">
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Người thực hiện & IP</th>
                <th>Hành động</th>
                <th>Trước → Sau (đã lọc bí mật)</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((log) => (
                <tr key={log.id}>
                  <td>{formatTimeShort(log.created_at)}</td>
                  <td>
                    {log.actor_label}
                    <div className="metric-sub">
                      <code>{log.actor_ip}</code>
                    </div>
                  </td>
                  <td>
                    <code>{log.action}</code> ({log.resource_type})
                  </td>
                  <td>
                    {log.before_summary} → <strong>{log.after_summary}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {!isChildView && (
        <section className="card">
          <h3 className="card-title">Quyền riêng tư, lưu trữ 90 ngày & Xóa toàn bộ dữ liệu (F3.3 / T23)</h3>
          <p className="metric-sub">
            Dữ liệu sử dụng tự động xóa sau 90 ngày. Nút dưới đây xóa toàn bộ dữ liệu của{' '}
            <strong>{child.display_name}</strong> trên Server và gửi yêu cầu xóa cache/outbox cục
            bộ trên Agent ({device?.name ?? 'thiết bị'}).
          </p>

          <div
            className={`alert ${
              deleteStatus.status === 'completed'
                ? 'alert-info'
                : deleteStatus.status === 'server_deleted_pending_agent'
                  ? 'alert-warn'
                  : 'alert-info'
            }`}
          >
            <strong>Trạng thái xóa dữ liệu:</strong> {deleteStatus.message}
          </div>

          {!confirmingDelete ? (
            <button
              type="button"
              className="btn btn-danger"
              onClick={() => setConfirmingDelete(true)}
            >
              Xóa toàn bộ dữ liệu của con tôi
            </button>
          ) : (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <span>Xác nhận xóa vĩnh viễn trên cả Server và Agent cache?</span>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => {
                  setConfirmingDelete(false);
                  void onRequestDeleteAll(child.id);
                }}
              >
                Xác nhận xóa toàn bộ
              </button>
              <button type="button" className="btn" onClick={() => setConfirmingDelete(false)}>
                Hủy
              </button>
            </div>
          )}

          {isDemoMode &&
            deleteStatus.status === 'server_deleted_pending_agent' &&
            onDemoCompleteAgentPurge && (
              <div style={{ marginTop: 10 }}>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => void onDemoCompleteAgentPurge(child.id)}
                >
                  Mô phỏng Agent xác nhận đã xóa cache cục bộ
                </button>
              </div>
            )}
        </section>
      )}
    </div>
  );
}
