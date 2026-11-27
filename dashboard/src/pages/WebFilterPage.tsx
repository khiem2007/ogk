import { useEffect, useMemo, useState } from 'react';
import {
  DOMAIN_CATALOG,
  PROTECTED_ALLOWLIST_ENTRIES,
  WEB_CATEGORY_META,
} from '../data/domainCatalog';
import type {
  DeviceInfo,
  PolicyDocument,
  PolicySnapshotResponse,
  RuleDecision,
  WebCategory,
} from '../types/ogk';
import { normalizeDomainInput } from '../utils/validation';

interface WebFilterPageProps {
  device: DeviceInfo | null;
  snapshot: PolicySnapshotResponse | null;
  isReadOnly: boolean;
  onSavePolicy: (expectedVersion: number, policy: PolicyDocument) => Promise<void>;
}

const PROTECTED_SET = new Set(PROTECTED_ALLOWLIST_ENTRIES.map((e) => e.domain));

export function WebFilterPage({
  device,
  snapshot,
  isReadOnly,
  onSavePolicy,
}: WebFilterPageProps) {
  const [draft, setDraft] = useState<PolicyDocument | null>(null);
  const [baseVersion, setBaseVersion] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | WebCategory>('all');
  const [newDomain, setNewDomain] = useState('');
  const [domainTargetList, setDomainTargetList] = useState<'hard_block' | 'explicit_allow'>(
    'hard_block',
  );
  const [message, setMessage] = useState<{ kind: 'info' | 'danger' | 'warn'; text: string } | null>(
    null,
  );

  useEffect(() => {
    if (snapshot) {
      setDraft(structuredClone(snapshot.policy));
      setBaseVersion(snapshot.policy_version);
      setMessage(null);
    }
  }, [snapshot]);

  const filteredCatalog = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return DOMAIN_CATALOG.filter((item) => {
      if (categoryFilter !== 'all' && item.category !== categoryFilter) {
        return false;
      }
      if (q && !item.domain.includes(q) && !item.sourceNote.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
  }, [searchQuery, categoryFilter]);

  if (!device || !snapshot || !draft) {
    return (
      <section className="card">
        <p className="metric-sub">Hãy chọn thiết bị để cấu hình lọc web.</p>
      </section>
    );
  }

  function setCategoryDecision(category: WebCategory, decision: RuleDecision) {
    if (!draft) return;
    const updatedRules = draft.domains.category_rules.map((rule) =>
      rule.category === category ? { ...rule, decision } : rule,
    );
    setDraft({
      ...draft,
      domains: {
        ...draft.domains,
        category_rules: updatedRules,
      },
    });
  }

  function handleAddCustomDomain() {
    if (!draft) return;
    const normalized = normalizeDomainInput(newDomain);
    if (!normalized) {
      setMessage({
        kind: 'danger',
        text: 'Tên miền không hợp lệ (chỉ nhập tên miền cấp hai/con như example.test, không nhập URL).',
      });
      return;
    }
    if (domainTargetList === 'hard_block' && PROTECTED_SET.has(normalized)) {
      setMessage({
        kind: 'danger',
        text: `Miền "${normalized}" nằm trong Protected Allowlist (NT6 — trường học/111/cứu hộ), tuyệt đối không thể đưa vào danh sách chặn.`,
      });
      return;
    }
    const current = draft.domains[domainTargetList];
    if (current.includes(normalized)) {
      setMessage({ kind: 'warn', text: `Miền "${normalized}" đã có trong danh sách.` });
      return;
    }
    setDraft({
      ...draft,
      domains: {
        ...draft.domains,
        [domainTargetList]: [...current, normalized],
      },
    });
    setNewDomain('');
    setMessage({ kind: 'info', text: `Đã thêm "${normalized}" vào ${domainTargetList}.` });
  }

  async function handleSave() {
    if (!draft) return;
    try {
      await onSavePolicy(baseVersion, draft);
      setMessage({ kind: 'info', text: 'Đã lưu cấu hình lọc web lên Server.' });
    } catch (err) {
      setMessage({
        kind: 'danger',
        text: err instanceof Error ? err.message : 'Lỗi khi lưu cấu hình lọc web.',
      });
    }
  }

  return (
    <div>
      <section className="card">
        <h2 className="card-title">Lọc web theo 6 nhóm & SafeSearch (DNS Proxy 127.0.0.1:53)</h2>
        <p className="metric-sub" style={{ margin: 0 }}>
          Chế độ lọc không giải mã HTTPS và không lưu lịch sử từng URL (NT2). Chế độ{' '}
          <strong>"Hạn chế"</strong> nghĩa là chỉ mở trong khung giờ cấu hình, DNS không đo được
          thời gian đọc từng trang web.
        </p>
      </section>

      {message && (
        <div
          className={`alert ${
            message.kind === 'danger'
              ? 'alert-danger'
              : message.kind === 'warn'
                ? 'alert-warn'
                : 'alert-info'
          }`}
          role="alert"
        >
          {message.text}
        </div>
      )}

      <div className="ogk-grid-2">
        <section className="card">
          <h3 className="card-title">1. Cấu hình 6 danh mục nội dung (PDF F2.3)</h3>
          <div style={{ marginBottom: 12 }}>
            <label className="ogk-field-inline">
              <span>Chế độ mặc định với miền chưa khai báo:</span>
              <select
                className="ogk-select"
                disabled={isReadOnly}
                value={draft.domains.mode}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    domains: {
                      ...draft.domains,
                      mode: e.target.value as 'blocklist' | 'allowlist',
                    },
                  })
                }
              >
                <option value="blocklist">Blocklist (cho phép trừ miền/nhóm chặn)</option>
                <option value="allowlist">Allowlist (chỉ mở danh sách cho phép)</option>
              </select>
            </label>
          </div>

          <div className="ogk-table-wrap">
            <table className="ogk-table">
              <thead>
                <tr>
                  <th>Nhóm nội dung</th>
                  <th>Quy tắc hiện tại</th>
                </tr>
              </thead>
              <tbody>
                {(Object.keys(WEB_CATEGORY_META) as WebCategory[]).map((cat) => {
                  const rule = draft.domains.category_rules.find((r) => r.category === cat);
                  const decision: RuleDecision =
                    rule?.decision ?? WEB_CATEGORY_META[cat].default6To11;
                  return (
                    <tr key={cat}>
                      <td>
                        <strong>{WEB_CATEGORY_META[cat].label}</strong>
                        <div className="metric-sub">{WEB_CATEGORY_META[cat].description}</div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 4 }}>
                          {(['block', 'restrict', 'allow'] as RuleDecision[]).map((choice) => (
                            <button
                              key={choice}
                              type="button"
                              disabled={isReadOnly}
                              className={`btn btn-sm ${
                                decision === choice
                                  ? choice === 'block'
                                    ? 'btn-danger'
                                    : choice === 'restrict'
                                      ? 'btn-warn'
                                      : 'btn-primary'
                                  : ''
                              }`}
                              onClick={() => setCategoryDecision(cat, choice)}
                            >
                              {choice === 'block'
                                ? 'Chặn'
                                : choice === 'restrict'
                                  ? 'Hạn chế'
                                  : 'Cho phép'}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card">
          <h3 className="card-title">2. SafeSearch DNS & Protected Allowlist (NT6)</h3>

          <div
            style={{
              padding: 12,
              border: '1px solid var(--border-soft)',
              borderRadius: 10,
              marginBottom: 14,
            }}
          >
            <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
              <span>
                <strong>Cưỡng chế SafeSearch qua DNS</strong>
                <div className="metric-sub">
                  Ánh xạ bản ghi DNS (vd: forcesafesearch.google.com). YouTube Restricted Mode là mở
                  rộng riêng.
                </div>
              </span>
              <input
                type="checkbox"
                disabled={isReadOnly}
                checked={draft.domains.safesearch_enabled}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    domains: {
                      ...draft.domains,
                      safesearch_enabled: e.target.checked,
                    },
                  })
                }
              />
            </label>
            <div style={{ marginTop: 8 }}>
              {draft.domains.safesearch_verified_by_dns ? (
                <span className="pill pill-online">
                  Đã xác nhận hoạt động qua nslookup & trình duyệt
                </span>
              ) : (
                <div className="alert alert-warn" style={{ marginBottom: 0 }}>
                  <strong>Chưa xác nhận thực tế:</strong> Công tắc mới lưu ý định cấu hình (C08).
                  Chỉ được báo "Đã bật" sau khi A10/B09 vượt qua kiểm tra <code>nslookup</code> và
                  trình duyệt trên Windows VM.
                </div>
              )}
            </div>
          </div>

          <h4 className="card-title" style={{ fontSize: '0.95rem' }}>
            Danh sách miễn chặn vĩnh viễn — Protected Allowlist (NT6)
          </h4>
          <p className="metric-sub" style={{ marginTop: 0 }}>
            Khóa cứng ở mức chính sách và UI: phụ huynh không thể xóa hoặc ghi đè cổng trường học,
            Tổng đài 111 và cứu hộ.
          </p>
          <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 14px' }}>
            {PROTECTED_ALLOWLIST_ENTRIES.map((entry) => (
              <li
                key={entry.domain}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '6px 10px',
                  background: 'var(--bg-soft)',
                  border: '1px solid var(--border-soft)',
                  borderRadius: 6,
                  marginBottom: 6,
                }}
              >
                <div>
                  <code>{entry.domain}</code>
                  <div className="metric-sub">{entry.sourceNote}</div>
                </div>
                <span className="pill pill-online">Khóa bảo vệ</span>
              </li>
            ))}
          </ul>

          {!isReadOnly && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
              <select
                className="ogk-select"
                value={domainTargetList}
                onChange={(e) =>
                  setDomainTargetList(e.target.value as 'hard_block' | 'explicit_allow')
                }
                aria-label="Danh sách đích"
              >
                <option value="hard_block">Chặn cứng (hard_block)</option>
                <option value="explicit_allow">Ngoại lệ cho phép (explicit_allow)</option>
              </select>
              <input
                className="ogk-input"
                style={{ flex: 1 }}
                placeholder="domain.example.test"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                aria-label="Tên miền tùy chỉnh"
              />
              <button type="button" className="btn btn-sm" onClick={handleAddCustomDomain}>
                Thêm miền
              </button>
            </div>
          )}

          <div className="metric-sub">
            <strong>Chặn cứng:</strong> {draft.domains.hard_block.join(', ') || 'Trống'}
            <br />
            <strong>Cho phép riêng:</strong> {draft.domains.explicit_allow.join(', ') || 'Trống'}
          </div>
        </section>
      </div>

      <section className="card">
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 10 }}>
          <div>
            <h3 className="card-title">
              3. Bảng phân loại tên miền ({DOMAIN_CATALOG.length} mục / 6 nhóm)
            </h3>
            <p className="metric-sub" style={{ marginTop: 0 }}>
              Đạt chuẩn ≥ 200 mục theo PDF; nhóm không phù hợp lứa tuổi chỉ dùng miền{' '}
              <code>.example.test</code> trung tính, không dùng miền người lớn thật.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              className="ogk-input"
              placeholder="Tìm tên miền hoặc nguồn..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Tìm kiếm trong bảng phân loại"
            />
            <select
              className="ogk-select"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value as 'all' | WebCategory)}
              aria-label="Lọc theo nhóm"
            >
              <option value="all">Tất cả 6 nhóm ({DOMAIN_CATALOG.length})</option>
              {(Object.keys(WEB_CATEGORY_META) as WebCategory[]).map((cat) => (
                <option key={cat} value={cat}>
                  {WEB_CATEGORY_META[cat].label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="ogk-table-wrap" style={{ maxHeight: 280, overflowY: 'auto', marginTop: 10 }}>
          <table className="ogk-table">
            <thead>
              <tr>
                <th>Tên miền</th>
                <th>Nhóm</th>
                <th>Mặc định 6–11 tuổi</th>
                <th>Nguồn / Ghi chú (Provenance)</th>
              </tr>
            </thead>
            <tbody>
              {filteredCatalog.slice(0, 60).map((entry) => (
                <tr key={entry.domain}>
                  <td>
                    <code>{entry.domain}</code>
                  </td>
                  <td>{WEB_CATEGORY_META[entry.category].label}</td>
                  <td>{entry.defaultDecision6To11}</td>
                  <td>{entry.sourceNote}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="metric-sub" style={{ marginTop: 8 }}>
          Đang hiển thị {Math.min(60, filteredCatalog.length)} / {filteredCatalog.length} kết quả
          khớp (tổng bộ dữ liệu: {DOMAIN_CATALOG.length} tên miền).
        </div>

        <div className="alert alert-info" style={{ marginTop: 12 }}>
          <strong>Giới hạn DNS / DoH / VPN (F2.5, M2–M3):</strong> DNS proxy chỉ lọc tên miền ở
          tầng phân giải <code>127.0.0.1:53</code>; nếu trình duyệt bật DoH (DNS-over-HTTPS), dùng
          VPN hoặc đổi DNS thủ công bằng quyền Administrator, bộ lọc có thể bị vượt qua. Nhóm kiểm
          chứng và ghi rõ giới hạn trong phụ lục M3.
        </div>

        {!isReadOnly && (
          <button type="button" className="btn btn-primary" onClick={() => void handleSave()}>
            Lưu cấu hình lọc web (v{baseVersion})
          </button>
        )}
      </section>
    </div>
  );
}
