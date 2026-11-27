import { useState } from 'react';
import { CommandStatusBadge, ConnectivityBadge } from '../components/StatusBadges';
import type { CommandItem, CommandStatus, CommandType, DeviceInfo } from '../types/ogk';
import { formatTimeShort } from '../utils/validation';

interface CommandsPageProps {
  device: DeviceInfo | null;
  commands: CommandItem[];
  isReadOnly: boolean;
  isDemoMode: boolean;
  onIssueCommand: (type: CommandType) => Promise<void>;
  onDemoTransitionCommand?: (commandId: string, target?: CommandStatus) => Promise<void>;
}

const COMMAND_CARDS: Array<{
  type: CommandType;
  title: string;
  desc: string;
  btnLabel: string;
  btnClass: string;
}> = [
  {
    type: 'TEMPORARY_TIME_EXEMPTION',
    title: 'Cho nghỉ 15 phút (Miễn giới hạn tạm thời)',
    desc: 'Bỏ kiểm tra lịch/quota thời gian trong 15 phút từ lúc agent áp dụng; không bỏ chặn app/web độc hại.',
    btnLabel: 'Gửi lệnh nghỉ 15p',
    btnClass: 'btn btn-primary',
  },
  {
    type: 'EXEMPT_UNTIL_LOCAL_DAY_END',
    title: 'Tạm dừng giới hạn hôm nay',
    desc: 'Bỏ giới hạn lịch/quota đến hết ngày hiện tại theo múi giờ thiết bị (ví dụ ngày nghỉ).',
    btnLabel: 'Gửi lệnh miễn hôm nay',
    btnClass: 'btn btn-warn',
  },
  {
    type: 'LOCK_SESSION',
    title: 'Khóa máy ngay (Manual Lock)',
    desc: 'Ghi trạng thái manual_lock bền vững và khóa phiên trẻ sau nhắc lưu bài. Cần hủy khóa để mở lại.',
    btnLabel: 'Khóa máy ngay',
    btnClass: 'btn btn-danger',
  },
  {
    type: 'CLEAR_MANUAL_LOCK',
    title: 'Hủy khóa thủ công',
    desc: 'Gỡ trạng thái manual_lock trước đó và ghi nhật ký kiểm toán.',
    btnLabel: 'Gửi lệnh hủy khóa',
    btnClass: 'btn',
  },
];

export function CommandsPage({
  device,
  commands,
  isReadOnly,
  isDemoMode,
  onIssueCommand,
  onDemoTransitionCommand,
}: CommandsPageProps) {
  const [notice, setNotice] = useState<{ kind: 'info' | 'danger' | 'warn'; text: string } | null>(
    null,
  );
  const [submittingType, setSubmittingType] = useState<CommandType | null>(null);

  if (!device) {
    return (
      <section className="card">
        <p className="metric-sub">Hãy chọn một thiết bị để điều khiển từ xa.</p>
      </section>
    );
  }

  async function handleSend(type: CommandType) {
    setSubmittingType(type);
    setNotice(null);
    try {
      await onIssueCommand(type);
      // C06 invariant: NEVER show a "success/executed" toast before agent ACK!
      setNotice({
        kind: 'warn',
        text: `Đã đưa lệnh ${type} vào hàng đợi (trạng thái: queued). Lệnh CHƯA thực thi trên máy trẻ cho tới khi Agent gửi ACK executed.`,
      });
    } catch (err) {
      setNotice({
        kind: 'danger',
        text: err instanceof Error ? err.message : 'Không thể tạo lệnh.',
      });
    } finally {
      setSubmittingType(null);
    }
  }

  return (
    <div>
      <section className="card">
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 10 }}>
          <div>
            <h2 className="card-title">Điều khiển từ xa — {device.name}</h2>
            <p className="metric-sub" style={{ margin: 0 }}>
              Mọi lệnh đi qua danh sách cho phép (allowlist), có thời hạn (<code>expires_at</code>),
              không chạy shell từ xa. <strong>delivered ≠ executed:</strong> giao diện chỉ xác nhận
              hoàn tất khi có ACK <code>executed</code>.
            </p>
          </div>
          <ConnectivityBadge state={device.connectivity} />
        </div>
      </section>

      {notice && (
        <div
          className={`alert ${
            notice.kind === 'danger'
              ? 'alert-danger'
              : notice.kind === 'warn'
                ? 'alert-warn'
                : 'alert-info'
          }`}
          role="status"
        >
          {notice.text}
        </div>
      )}

      {!isReadOnly && (
        <div className="ogk-grid-2">
          {COMMAND_CARDS.map((card) => (
            <article key={card.type} className="card">
              <h3 className="card-title">{card.title}</h3>
              <p className="metric-sub">{card.desc}</p>
              <button
                type="button"
                className={card.btnClass}
                disabled={submittingType === card.type}
                onClick={() => void handleSend(card.type)}
              >
                {submittingType === card.type ? 'Đang gửi...' : card.btnLabel}
              </button>
            </article>
          ))}
        </div>
      )}

      <section className="card">
        <h3 className="card-title">Lịch sử và trạng thái lệnh (queued → delivered → executed / failed / expired)</h3>
        {commands.length === 0 ? (
          <p className="metric-sub">Chưa có lệnh nào cho thiết bị này.</p>
        ) : (
          <div className="ogk-table-wrap">
            <table className="ogk-table">
              <thead>
                <tr>
                  <th>Lệnh</th>
                  <th>Trạng thái</th>
                  <th>Phát hành / Hết hạn</th>
                  <th>Kết quả ACK</th>
                  {isDemoMode && !isReadOnly && <th>Mô phỏng vòng đời (Demo)</th>}
                </tr>
              </thead>
              <tbody>
                {commands.map((cmd) => (
                  <tr key={cmd.command_id}>
                    <td>
                      <strong>{cmd.command_type}</strong>
                      <div className="metric-sub">
                        <code>{cmd.command_id.slice(0, 8)}</code>
                      </div>
                    </td>
                    <td>
                      <CommandStatusBadge status={cmd.status} />
                    </td>
                    <td>
                      Tạo: {formatTimeShort(cmd.issued_at)}
                      <br />
                      Hết hạn: {formatTimeShort(cmd.expires_at)}
                    </td>
                    <td>
                      {cmd.result_code ? <code>{cmd.result_code}</code> : 'Chưa có ACK'}
                      {cmd.observed_at && (
                        <div className="metric-sub">Lúc {formatTimeShort(cmd.observed_at)}</div>
                      )}
                    </td>
                    {isDemoMode && !isReadOnly && onDemoTransitionCommand && (
                      <td>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {cmd.status === 'queued' && (
                            <button
                              type="button"
                              className="btn btn-sm"
                              onClick={() =>
                                void onDemoTransitionCommand(cmd.command_id, 'delivered')
                              }
                            >
                              Agent nhận (delivered)
                            </button>
                          )}
                          {(cmd.status === 'queued' || cmd.status === 'delivered') && (
                            <>
                              <button
                                type="button"
                                className="btn btn-sm btn-primary"
                                onClick={() =>
                                  void onDemoTransitionCommand(cmd.command_id, 'executed')
                                }
                              >
                                ACK executed
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-warn"
                                onClick={() =>
                                  void onDemoTransitionCommand(cmd.command_id, 'expired')
                                }
                              >
                                Hết hạn
                              </button>
                              <button
                                type="button"
                                className="btn btn-sm btn-danger"
                                onClick={() =>
                                  void onDemoTransitionCommand(cmd.command_id, 'failed')
                                }
                              >
                                Thất bại
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    )}
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
