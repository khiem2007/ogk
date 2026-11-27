import type { CommandStatus, ConnectivityState, RequestStatus } from '../types/ogk';

export function ConnectivityBadge({ state }: { state: ConnectivityState }) {
  const map: Record<ConnectivityState, { label: string; cls: string }> = {
    online: { label: 'Đang online', cls: 'pill pill-online' },
    offline: { label: 'Mất liên lạc (>180s)', cls: 'pill pill-offline' },
    degraded: { label: 'Degraded (thiếu Tray/Helper)', cls: 'pill pill-degraded' },
  };
  const info = map[state];
  return <span className={info.cls}>{info.label}</span>;
}

export function RequestStatusBadge({ status }: { status: RequestStatus }) {
  const map: Record<RequestStatus, { label: string; cls: string }> = {
    pending: { label: 'Chờ duyệt', cls: 'pill pill-degraded' },
    approved: { label: 'Đã duyệt', cls: 'pill pill-online' },
    rejected: { label: 'Từ chối', cls: 'pill pill-offline' },
    expired: { label: 'Hết hạn', cls: 'pill pill-offline' },
  };
  const info = map[status];
  return <span className={info.cls}>{info.label}</span>;
}

export function CommandStatusBadge({ status }: { status: CommandStatus }) {
  const map: Record<CommandStatus, { label: string; cls: string }> = {
    queued: { label: 'queued (chờ gửi)', cls: 'pill pill-demo' },
    delivered: { label: 'delivered (agent đã nhận — chưa xong)', cls: 'pill pill-degraded' },
    executed: { label: 'executed (đã xác nhận thực thi)', cls: 'pill pill-online' },
    failed: { label: 'failed (thất bại)', cls: 'pill pill-offline' },
    expired: { label: 'expired (hết hạn)', cls: 'pill pill-offline' },
  };
  const info = map[status];
  return <span className={info.cls}>{info.label}</span>;
}
