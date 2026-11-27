import { useState } from 'react';
import { RequestStatusBadge } from '../components/StatusBadges';
import type { ChildRequestItem } from '../types/ogk';
import { formatTimeShort } from '../utils/validation';

interface RequestsPageProps {
  requests: ChildRequestItem[];
  isReadOnly: boolean;
  onDecide: (requestId: string, decision: 'approved' | 'rejected') => Promise<void>;
}

export function RequestsPage({ requests, isReadOnly, onDecide }: RequestsPageProps) {
  const [feedback, setFeedback] = useState<{ kind: 'info' | 'danger'; text: string } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function handleAction(requestId: string, decision: 'approved' | 'rejected') {
    setBusyId(requestId);
    setFeedback(null);
    try {
      await onDecide(requestId, decision);
      setFeedback({
        kind: 'info',
        text:
          decision === 'approved'
            ? 'Đã duyệt yêu cầu (tạo grant một lần). Agent sẽ áp dụng khi nhận cập nhật.'
            : 'Đã từ chối yêu cầu và lưu phản hồi minh bạch cho trẻ.',
      });
    } catch (err) {
      setFeedback({
        kind: 'danger',
        text: err instanceof Error ? err.message : 'Không thể xử lý yêu cầu.',
      });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <section className="card">
        <h2 className="card-title">Yêu cầu từ con (NT3 — Đối thoại thay vì cấm đoán)</h2>
        <p className="metric-sub" style={{ margin: 0 }}>
          Mỗi yêu cầu chỉ chuyển trạng thái <code>pending → approved | rejected | expired</code>{' '}
          đúng một lần qua transaction (T09). Duyệt xin thêm giờ không tự mở lịch ngoài giờ; duyệt
          mở app không vượt khóa thủ công hoặc hạn mức tổng.
        </p>
      </section>

      {feedback && (
        <div
          className={`alert ${feedback.kind === 'danger' ? 'alert-danger' : 'alert-info'}`}
          role="alert"
        >
          {feedback.text}
        </div>
      )}

      {requests.length === 0 ? (
        <section className="card">
          <p className="metric-sub">Hiện chưa có yêu cầu nào từ trẻ.</p>
        </section>
      ) : (
        requests.map((req) => {
          const title =
            req.request_type === 'time_extension'
              ? `Xin thêm ${Math.round((req.payload.amount_seconds ?? 0) / 60)} phút`
              : req.request_type === 'app_exception'
                ? `Xin mở ứng dụng "${req.payload.app_name ?? req.payload.app_id}"`
                : `Báo trang bị chặn nhầm (${req.payload.domain ?? 'domain'})`;
          return (
            <article key={req.request_id} className="card">
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: 12,
                }}
              >
                <div style={{ flex: 1, minWidth: 240 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <strong style={{ fontSize: '1.05rem' }}>{title}</strong>
                    <RequestStatusBadge status={req.status} />
                  </div>
                  <p style={{ margin: '0 0 6px' }}>“{req.reason}”</p>
                  <div className="metric-sub">
                    {req.child_name} · Gửi lúc {formatTimeShort(req.created_at)}
                    {req.decided_by && ` · Người quyết định: ${req.decided_by}`}
                  </div>
                  {req.grant_preview && (
                    <div className="alert alert-info" style={{ marginTop: 10, marginBottom: 0 }}>
                      <strong>Phạm vi & thời hạn nếu duyệt:</strong> {req.grant_preview.scope} ·
                      Hết hạn: {formatTimeShort(req.grant_preview.valid_until)}
                    </div>
                  )}
                </div>

                {!isReadOnly && req.status === 'pending' && (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={busyId === req.request_id}
                      onClick={() => void handleAction(req.request_id, 'approved')}
                    >
                      Duyệt
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger"
                      disabled={busyId === req.request_id}
                      onClick={() => void handleAction(req.request_id, 'rejected')}
                    >
                      Từ chối
                    </button>
                  </div>
                )}
              </div>
            </article>
          );
        })
      )}
    </div>
  );
}
