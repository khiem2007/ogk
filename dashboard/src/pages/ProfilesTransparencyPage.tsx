import { useState } from 'react';
import type { ChildProfile, PolicyDocument, PolicySnapshotResponse } from '../types/ogk';
import { formatTimeShort } from '../utils/validation';

interface ProfilesTransparencyPageProps {
  child: ChildProfile;
  snapshot: PolicySnapshotResponse | null;
  isReadOnly: boolean;
  onApplyTemplate?: (expectedVersion: number, policy: PolicyDocument) => Promise<void>;
  onAcknowledgeConsent?: (childId: string) => Promise<void>;
}

const AGE_TEMPLATES: Array<{
  band: '6-8' | '9-11' | '12-14';
  title: string;
  subtitle: string;
  dailyMinutes: number;
  weekendMinutes: number;
  bullets: string[];
}> = [
  {
    band: '6-8',
    title: '6–8 tuổi · Chặt chẽ (Mẫu tham khảo)',
    subtitle: 'Ưu tiên học tập, hạn chế giải trí',
    dailyMinutes: 90,
    weekendMinutes: 120,
    bullets: [
      'Ưu tiên ứng dụng học tập và cổng trường học',
      'Không mở game trực tuyến tự do',
      'Gợi ý chế độ web Allowlist',
      'Hạn mức đề xuất: 90 phút/ngày thường',
    ],
  },
  {
    band: '9-11',
    title: '9–11 tuổi · Cân bằng (Mẫu tham khảo)',
    subtitle: 'Học tập + giải trí có kiểm soát',
    dailyMinutes: 120,
    weekendMinutes: 180,
    bullets: [
      'Học tập + giải trí có hạn mức riêng',
      'Game chỉ mở theo khung giờ cuối tuần',
      'Lọc web 6 nhóm (mặc định chặn mạng xã hội)',
      'Hạn mức đề xuất: 120 phút/ngày thường',
    ],
  },
  {
    band: '12-14',
    title: '12–14 tuổi · Nới dần (Mẫu tham khảo)',
    subtitle: 'Tăng tự quản và minh bạch thỏa thuận',
    dailyMinutes: 150,
    weekendMinutes: 210,
    bullets: [
      'Tự quản phần lớn ứng dụng lành mạnh',
      'Chỉ chặn nhóm không phù hợp lứa tuổi',
      'Cùng xem báo cáo và thỏa thuận khung giờ',
      'Hạn mức đề xuất: 150 phút/ngày thường',
    ],
  },
];

export function ProfilesTransparencyPage({
  child,
  snapshot,
  isReadOnly,
  onApplyTemplate,
  onAcknowledgeConsent,
}: ProfilesTransparencyPageProps) {
  const [previewBand, setPreviewBand] = useState<'6-8' | '9-11' | '12-14' | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const selectedTemplate = AGE_TEMPLATES.find((t) => t.band === previewBand) ?? null;

  async function handleConfirmTemplate() {
    if (!selectedTemplate || !snapshot || !onApplyTemplate) return;
    const nextPolicy: PolicyDocument = structuredClone(snapshot.policy);
    nextPolicy.quotas.total_daily_seconds = selectedTemplate.dailyMinutes * 60;
    nextPolicy.quotas.weekend_daily_seconds = selectedTemplate.weekendMinutes * 60;
    if (selectedTemplate.band === '6-8') {
      nextPolicy.domains.mode = 'allowlist';
    } else {
      nextPolicy.domains.mode = 'blocklist';
    }
    await onApplyTemplate(snapshot.policy_version, nextPolicy);
    setPreviewBand(null);
    setFeedback(`Đã áp dụng mẫu tham khảo "${selectedTemplate.title}" lên Server.`);
  }

  return (
    <div>
      <section className="card">
        <h2 className="card-title">Hồ sơ, Quy tắc theo độ tuổi & Minh bạch với trẻ</h2>
        <p className="metric-sub" style={{ margin: 0 }}>
          Phần mềm là “giàn giáo tạm thời”, hướng tới việc con tự điều chỉnh. Ghi chú trung thực:
          xác thực hai yếu tố (2FA) là phần mở rộng sau MVP và <strong>chưa bật</strong> trong bản
          hiện tại.
        </p>
      </section>

      {feedback && (
        <div className="alert alert-info" role="status">
          {feedback}
        </div>
      )}

      <div className="ogk-grid-3">
        {AGE_TEMPLATES.map((tpl) => (
          <article
            key={tpl.band}
            className="card"
            style={{
              borderColor:
                child.age_band === tpl.band ? 'var(--accent-primary)' : 'var(--border-soft)',
              borderWidth: child.age_band === tpl.band ? 2 : 1,
            }}
          >
            <h3 className="card-title">{tpl.title}</h3>
            <p className="metric-sub">{tpl.subtitle}</p>
            <ul style={{ paddingLeft: 18, margin: '8px 0 12px', fontSize: '0.9rem' }}>
              {tpl.bullets.map((b) => (
                <li key={b} style={{ marginBottom: 4 }}>
                  {b}
                </li>
              ))}
            </ul>
            {!isReadOnly && snapshot && (
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => setPreviewBand(tpl.band)}
              >
                Xem trước khi áp dụng
              </button>
            )}
          </article>
        ))}
      </div>

      {selectedTemplate && snapshot && !isReadOnly && (
        <section className="card" style={{ borderColor: 'var(--accent-primary)' }}>
          <h3 className="card-title">Xem trước thay đổi mẫu: {selectedTemplate.title}</h3>
          <p className="metric-sub">
            Hạn mức ngày thường sẽ đổi từ{' '}
            <strong>{Math.round(snapshot.policy.quotas.total_daily_seconds / 60)} phút</strong> →{' '}
            <strong>{selectedTemplate.dailyMinutes} phút</strong>; cuối tuần →{' '}
            <strong>{selectedTemplate.weekendMinutes} phút</strong>; chế độ lọc web →{' '}
            <strong>{selectedTemplate.band === '6-8' ? 'allowlist' : 'blocklist'}</strong>.
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void handleConfirmTemplate()}
            >
              Xác nhận áp dụng mẫu này
            </button>
            <button type="button" className="btn" onClick={() => setPreviewBand(null)}>
              Đóng xem trước
            </button>
          </div>
        </section>
      )}

      <section className="card">
        <h3 className="card-title">Trang minh bạch: “Phần mềm này làm gì?” (NT1 / NT2 / NT5)</h3>
        <div className="ogk-grid-2">
          <div className="alert alert-info" style={{ marginBottom: 0 }}>
            <strong>Phiên bản dành cho trẻ (ngôn ngữ cấp 1):</strong>
            <p style={{ margin: '6px 0' }}>
              “Chào em! OpenGuard Kids giống như đồng hồ hẹn giờ cùng ba mẹ đặt ra để nhắc em nghỉ
              mắt và học tập đúng giờ. Ứng dụng chỉ ghi nhận tên phần mềm đang mở, tên nhóm trang
              web và số phút em sử dụng.”
            </p>
            <p style={{ margin: 0 }}>
              “Ứng dụng <strong>KHÔNG đọc</strong> tin nhắn, bài tập, mật khẩu, tiêu đề cửa sổ,
              địa chỉ web chi tiết và <strong>KHÔNG chụp màn hình</strong>. Em luôn thấy biểu tượng
              ở khay góc màn hình, có thể bấm <em>Xin thêm giờ</em> hoặc xem lại cùng báo cáo với
              ba mẹ.”
            </p>
          </div>
          <div>
            <strong>Đồng thuận đã ghi nhận:</strong>
            <p className="metric-sub">
              Hồ sơ: <strong>{child.display_name}</strong> · Phiên bản giải thích:{' '}
              <code>v{child.explanation_version}</code>
              <br />
              Trạng thái:{' '}
              {child.consent_acknowledged_at
                ? `Đã giải thích & ghi nhận lúc ${formatTimeShort(child.consent_acknowledged_at)}`
                : 'Chưa đánh dấu đã giải thích cho trẻ.'}
            </p>
            {!isReadOnly && onAcknowledgeConsent && (
              <button
                type="button"
                className="btn btn-sm btn-primary"
                onClick={() => void onAcknowledgeConsent(child.id)}
              >
                Ghi nhận đã giải thích cho trẻ
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
