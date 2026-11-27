import { useState, type FormEvent } from 'react';
import type { ApiMode } from '../api/client';
import type { UserRole } from '../types/ogk';

interface LoginPageProps {
  mode: ApiMode;
  onModeChange: (mode: ApiMode) => void;
  onLogin: (email: string, password: string) => Promise<void>;
  onDemoQuickSwitch?: (role: UserRole) => Promise<void>;
  errorMessage: string | null;
}

export function LoginPage({
  mode,
  onModeChange,
  onLogin,
  onDemoQuickSwitch,
  errorMessage,
}: LoginPageProps) {
  const [email, setEmail] = useState('phuhuynh.demo@ogk.local');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLocalError(null);
    if (!email.trim().includes('@')) {
      setLocalError('Vui lòng nhập email hợp lệ.');
      return;
    }
    if (password.length < 10) {
      setLocalError('Mật khẩu phải có ít nhất 10 ký tự theo tiêu chuẩn bảo mật F5.1.');
      return;
    }
    setSubmitting(true);
    try {
      await onLogin(email.trim(), password);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={{ maxWidth: 480, margin: '40px auto', padding: '0 16px' }}>
      <section className="card">
        <h1 className="card-title" style={{ fontSize: '1.35rem' }}>
          Đăng nhập OpenGuard Kids
        </h1>
        <p className="metric-sub" style={{ marginBottom: 14 }}>
          Công cụ đồng hành cùng con trên Windows — minh bạch, có thỏa thuận, không chạy ẩn.
        </p>

        <div className="alert alert-info">
          <strong>Nguồn dữ liệu:</strong>{' '}
          {mode === 'demo'
            ? 'Chế độ Demo / Fixture (dữ liệu mô phỏng trong trình duyệt; TV1 chưa mở API A03–A10).'
            : 'Chế độ API Server thật (/api/v1, cookie HttpOnly + CSRF).'}
          <div style={{ marginTop: 8 }}>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => onModeChange(mode === 'demo' ? 'api' : 'demo')}
            >
              Chuyển sang {mode === 'demo' ? 'API Server thật' : 'Chế độ Demo / Fixture'}
            </button>
          </div>
        </div>

        {(localError || errorMessage) && (
          <div className="alert alert-danger" role="alert">
            {localError ?? errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span>Email tài khoản</span>
            <input
              className="ogk-input"
              type="email"
              name="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span>Mật khẩu (tối thiểu 10 ký tự)</span>
            <input
              className="ogk-input"
              type="password"
              name="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="Nhập mật khẩu ≥ 10 ký tự"
              required
            />
          </label>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Đang xác thực...' : 'Đăng nhập'}
          </button>
        </form>

        {mode === 'demo' && onDemoQuickSwitch && (
          <div style={{ marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--border-soft)' }}>
            <div className="metric-sub" style={{ marginBottom: 8 }}>
              Đăng nhập nhanh (chỉ có trong Chế độ Demo):
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => void onDemoQuickSwitch('parent')}
              >
                Vào vai trò Phụ huynh (Demo)
              </button>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => void onDemoQuickSwitch('child-view')}
              >
                Vào vai trò Trẻ xem (child-view Demo)
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
