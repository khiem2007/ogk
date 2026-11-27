import { useEffect, useState } from 'react';
import type {
  AppCategory,
  AppRuleItem,
  DeviceInfo,
  PolicyDocument,
  PolicySnapshotResponse,
  ScheduleSlot,
} from '../types/ogk';
import {
  DAY_LABELS,
  minutesToTime,
  timeToMinutes,
  validateScheduleSlots,
} from '../utils/validation';

interface AppsSchedulePageProps {
  device: DeviceInfo | null;
  snapshot: PolicySnapshotResponse | null;
  isReadOnly: boolean;
  isDemoMode: boolean;
  onSavePolicy: (expectedVersion: number, policy: PolicyDocument) => Promise<void>;
  onDemoBumpServerVersion?: () => void;
}

const SLOTS_48 = Array.from({ length: 48 }, (_, idx) => minutesToTime(idx * 30));

function isSlotCovered(slots: ScheduleSlot[], day: number, slotMinutes: number): boolean {
  return slots.some(
    (s) =>
      s.day_of_week === day &&
      timeToMinutes(s.start) <= slotMinutes &&
      slotMinutes < timeToMinutes(s.end),
  );
}

function toggleHalfHourSlot(slots: ScheduleSlot[], day: number, slotIndex: number): ScheduleSlot[] {
  const startMin = slotIndex * 30;
  const endMin = startMin + 30;
  const start = minutesToTime(startMin);
  const end = minutesToTime(endMin === 1440 ? 1440 : endMin);
  // Keep 23:30-23:59 safe for schema pattern HH:MM (00:00..23:59)
  const boundedEnd = endMin === 1440 ? '23:59' : end;

  const otherDays = slots.filter((s) => s.day_of_week !== day);
  const daySlots = slots.filter((s) => s.day_of_week === day);

  const activeSet = new Set<number>();
  for (const s of daySlots) {
    const sMin = timeToMinutes(s.start);
    const eMin = s.end === '23:59' ? 1440 : timeToMinutes(s.end);
    for (let m = sMin; m < eMin; m += 30) {
      activeSet.add(Math.floor(m / 30));
    }
  }

  if (activeSet.has(slotIndex)) {
    activeSet.delete(slotIndex);
  } else {
    activeSet.add(slotIndex);
  }

  const sorted = [...activeSet].sort((a, b) => a - b);
  const merged: ScheduleSlot[] = [];
  let runStart: number | null = null;
  let prev: number | null = null;

  for (const idx of sorted) {
    if (runStart === null) {
      runStart = idx;
      prev = idx;
    } else if (prev !== null && idx === prev + 1) {
      prev = idx;
    } else {
      const endM = (prev! + 1) * 30;
      merged.push({
        day_of_week: day,
        start: minutesToTime(runStart * 30),
        end: endM >= 1440 ? '23:59' : minutesToTime(endM),
      });
      runStart = idx;
      prev = idx;
    }
  }
  if (runStart !== null && prev !== null) {
    const endM = (prev + 1) * 30;
    merged.push({
      day_of_week: day,
      start: minutesToTime(runStart * 30),
      end: endM >= 1440 ? '23:59' : minutesToTime(endM),
    });
  }
  void start;
  void boundedEnd;

  return [...otherDays, ...merged].sort(
    (a, b) => a.day_of_week - b.day_of_week || timeToMinutes(a.start) - timeToMinutes(b.start),
  );
}

export function AppsSchedulePage({
  device,
  snapshot,
  isReadOnly,
  isDemoMode,
  onSavePolicy,
  onDemoBumpServerVersion,
}: AppsSchedulePageProps) {
  const [draft, setDraft] = useState<PolicyDocument | null>(null);
  const [baseVersion, setBaseVersion] = useState<number>(1);
  const [newDay, setNewDay] = useState(0);
  const [newStart, setNewStart] = useState('18:00');
  const [newEnd, setNewEnd] = useState('20:00');
  const [newAppName, setNewAppName] = useState('');
  const [newExeName, setNewExeName] = useState('');
  const [newExeHash, setNewExeHash] = useState('');
  const [newAppCategory, setNewAppCategory] = useState<AppCategory>('games');
  const [showPreview, setShowPreview] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ kind: 'info' | 'danger' | 'warn'; text: string } | null>(
    null,
  );

  useEffect(() => {
    if (snapshot) {
      setDraft(structuredClone(snapshot.policy));
      setBaseVersion(snapshot.policy_version);
      setStatusMsg(null);
    }
  }, [snapshot]);

  if (!device || !snapshot || !draft) {
    return (
      <section className="card">
        <p className="metric-sub">Hãy chọn một thiết bị đã ghép để cấu hình lịch và ứng dụng.</p>
      </section>
    );
  }

  const validation = validateScheduleSlots(draft.schedule);

  function handleAddScheduleSlot() {
    if (!draft) return;
    const candidate: ScheduleSlot = { day_of_week: newDay, start: newStart, end: newEnd };
    const nextSchedule = [...draft.schedule, candidate];
    const check = validateScheduleSlots(nextSchedule);
    if (!check.valid) {
      setStatusMsg({ kind: 'danger', text: check.errors.join(' ') });
      return;
    }
    setDraft({ ...draft, schedule: nextSchedule });
    setStatusMsg({ kind: 'info', text: `Đã thêm khung ${DAY_LABELS[newDay]} ${newStart}–${newEnd} vào bản nháp.` });
  }

  function handleRemoveSlot(index: number) {
    if (!draft) return;
    setDraft({
      ...draft,
      schedule: draft.schedule.filter((_, idx) => idx !== index),
    });
  }

  function handleAddAppRule() {
    if (!draft) return;
    const exe = newExeName.trim();
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.exe$/i.test(exe)) {
      setStatusMsg({
        kind: 'danger',
        text: 'Tên file thực thi phải kết thúc bằng .exe (ví dụ: sample-game.exe).',
      });
      return;
    }
    const sha = newExeHash.trim().toLowerCase();
    if (sha && !/^[0-9a-f]{64}$/.test(sha)) {
      setStatusMsg({
        kind: 'danger',
        text: 'SHA-256 phải đúng 64 ký tự hex (hoặc để trống nếu chưa trích xuất hash).',
      });
      return;
    }
    const item: AppRuleItem = {
      app_id: crypto.randomUUID(),
      display_name: newAppName.trim() || exe,
      executable_name: exe,
      executable_sha256: sha || '0'.repeat(64),
      category: newAppCategory,
      decision: 'block',
    };
    setDraft({ ...draft, apps: [...draft.apps, item] });
    setNewAppName('');
    setNewExeName('');
    setNewExeHash('');
    setStatusMsg({ kind: 'info', text: `Đã thêm app "${exe}" vào bản nháp.` });
  }

  async function handleSave() {
    if (!draft) return;
    const check = validateScheduleSlots(draft.schedule);
    if (!check.valid) {
      setStatusMsg({ kind: 'danger', text: check.errors.join(' ') });
      return;
    }
    try {
      await onSavePolicy(baseVersion, draft);
      setShowPreview(false);
      setStatusMsg({
        kind: 'info',
        text: `Đã lưu chính sách mới lên Server. Thiết bị sẽ áp dụng sau khi đồng bộ (kiểm tra mục Server vs Applied version).`,
      });
    } catch (err) {
      setStatusMsg({
        kind: 'danger',
        text: err instanceof Error ? err.message : 'Lỗi khi lưu chính sách.',
      });
    }
  }

  return (
    <div>
      <section className="card">
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <h2 className="card-title">Ứng dụng & Khung giờ 7×48 — {device.name}</h2>
            <p className="metric-sub" style={{ margin: 0 }}>
              Phiên bản trên Server: <strong>v{device.server_policy_version}</strong> · Thiết bị đã
              áp dụng: <strong>v{device.applied_policy_version ?? '—'}</strong> · Toàn vẹn:{' '}
              <code>{snapshot.integrity_tag}</code>
            </p>
          </div>
          {device.server_policy_version !== device.applied_policy_version && (
            <span className="pill pill-degraded">
              Chờ thiết bị áp dụng bản mới (khác Saved trên Server)
            </span>
          )}
        </div>

        {isDemoMode && !isReadOnly && onDemoBumpServerVersion && (
          <div style={{ marginTop: 10 }}>
            <button
              type="button"
              className="btn btn-sm btn-warn"
              onClick={() => {
                onDemoBumpServerVersion();
                setStatusMsg({
                  kind: 'warn',
                  text: 'Đã tăng ngầm phiên bản trên Server (Demo) để kiểm chứng lỗi xung đột 409 VERSION_CONFLICT khi bạn bấm Lưu.',
                });
              }}
            >
              Mô phỏng có người khác vừa sửa trên Server (test 409 Conflict)
            </button>
          </div>
        )}
      </section>

      {statusMsg && (
        <div
          className={`alert ${
            statusMsg.kind === 'danger'
              ? 'alert-danger'
              : statusMsg.kind === 'warn'
                ? 'alert-warn'
                : 'alert-info'
          }`}
          role="alert"
        >
          {statusMsg.text}
        </div>
      )}

      {!validation.valid && (
        <div className="alert alert-danger" role="alert">
          {validation.errors.join(' ')}
        </div>
      )}

      <section className="card">
        <h3 className="card-title">1. Lịch sử dụng máy theo tuần (Ma trận 7×48, slot 30 phút)</h3>
        <p className="metric-sub">
          Nhấn vào từng ô 30 phút để bật/tắt, hoặc nhập khoảng <code>[start, end)</code> bên dưới.
          Không cho phép lịch trùng hoặc khung qua nửa đêm (hãy tách 2 khung).
        </p>

        <div className="matrix-wrap" style={{ marginBottom: 12 }}>
          <div className="matrix-grid" role="grid" aria-label="Ma trận lịch 7 ngày nhân 48 slot">
            <div className="matrix-day-label">Thứ / Giờ</div>
            {SLOTS_48.map((label, idx) => (
              <div
                key={label}
                style={{
                  textAlign: 'center',
                  background: 'var(--bg-soft)',
                  borderBottom: '1px solid #e7efe9',
                  padding: '2px 0',
                }}
                title={label}
              >
                {idx % 4 === 0 ? label.slice(0, 2) : ''}
              </div>
            ))}
            {DAY_LABELS.map((dayName, dayIndex) => (
              <div key={dayName} style={{ display: 'contents' }}>
                <div className="matrix-day-label">{dayName}</div>
                {SLOTS_48.map((slotLabel, slotIdx) => {
                  const allowed = isSlotCovered(draft.schedule, dayIndex, slotIdx * 30);
                  return (
                    <button
                      key={`${dayIndex}-${slotIdx}`}
                      type="button"
                      disabled={isReadOnly}
                      className={`matrix-cell ${allowed ? 'allowed' : ''}`}
                      title={`${dayName} ${slotLabel}`}
                      aria-label={`${dayName} ${slotLabel} ${allowed ? 'cho phép' : 'chặn'}`}
                      onClick={() =>
                        setDraft({
                          ...draft,
                          schedule: toggleHalfHourSlot(draft.schedule, dayIndex, slotIdx),
                        })
                      }
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {!isReadOnly && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginBottom: 12 }}>
            <select
              className="ogk-select"
              value={newDay}
              onChange={(e) => setNewDay(Number(e.target.value))}
              aria-label="Chọn thứ"
            >
              {DAY_LABELS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
            <input
              className="ogk-input"
              aria-label="Giờ bắt đầu"
              value={newStart}
              onChange={(e) => setNewStart(e.target.value)}
              placeholder="HH:MM"
              style={{ width: 90 }}
            />
            <span>đến</span>
            <input
              className="ogk-input"
              aria-label="Giờ kết thúc"
              value={newEnd}
              onChange={(e) => setNewEnd(e.target.value)}
              placeholder="HH:MM"
              style={{ width: 90 }}
            />
            <button type="button" className="btn" onClick={handleAddScheduleSlot}>
              Thêm khung giờ
            </button>
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {draft.schedule.map((s, idx) => (
            <span key={`${s.day_of_week}-${s.start}-${idx}`} className="pill pill-online">
              {DAY_LABELS[s.day_of_week]} {s.start}–{s.end}
              {!isReadOnly && (
                <button
                  type="button"
                  style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontWeight: 700 }}
                  aria-label={`Xóa khung ${DAY_LABELS[s.day_of_week]} ${s.start}-${s.end}`}
                  onClick={() => handleRemoveSlot(idx)}
                >
                  ×
                </button>
              )}
            </span>
          ))}
        </div>
      </section>

      <div className="ogk-grid-2">
        <section className="card">
          <h3 className="card-title">2. Hạn mức thời gian (phút / ngày)</h3>
          <div style={{ display: 'grid', gap: 10 }}>
            <label className="ogk-field-inline" style={{ justifyContent: 'space-between' }}>
              <span>Tổng máy ngày thường (phút):</span>
              <input
                type="number"
                min={0}
                max={1440}
                disabled={isReadOnly}
                className="ogk-input"
                value={Math.round(draft.quotas.total_daily_seconds / 60)}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    quotas: {
                      ...draft.quotas,
                      total_daily_seconds: Math.max(0, Number(e.target.value)) * 60,
                    },
                  })
                }
              />
            </label>
            <label className="ogk-field-inline" style={{ justifyContent: 'space-between' }}>
              <span>Tổng máy cuối tuần (phút):</span>
              <input
                type="number"
                min={0}
                max={1440}
                disabled={isReadOnly}
                className="ogk-input"
                value={Math.round(draft.quotas.weekend_daily_seconds / 60)}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    quotas: {
                      ...draft.quotas,
                      weekend_daily_seconds: Math.max(0, Number(e.target.value)) * 60,
                    },
                  })
                }
              />
            </label>
            {(['education', 'entertainment', 'games', 'other'] as AppCategory[]).map((cat) => (
              <label key={cat} className="ogk-field-inline" style={{ justifyContent: 'space-between' }}>
                <span>Nhóm {cat} (phút):</span>
                <input
                  type="number"
                  min={0}
                  max={1440}
                  disabled={isReadOnly}
                  className="ogk-input"
                  value={Math.round((draft.quotas.category_daily_seconds[cat] ?? 0) / 60)}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      quotas: {
                        ...draft.quotas,
                        category_daily_seconds: {
                          ...draft.quotas.category_daily_seconds,
                          [cat]: Math.max(0, Number(e.target.value)) * 60,
                        },
                      },
                    })
                  }
                />
              </label>
            ))}
          </div>
        </section>

        <section className="card">
          <h3 className="card-title">3. Quy tắc ứng dụng (Tên + SHA-256)</h3>
          <div className="ogk-table-wrap">
            <table className="ogk-table">
              <thead>
                <tr>
                  <th>Ứng dụng / .exe</th>
                  <th>SHA-256</th>
                  <th>Quyết định</th>
                </tr>
              </thead>
              <tbody>
                {draft.apps.map((app, idx) => (
                  <tr key={app.app_id}>
                    <td>
                      <strong>{app.display_name}</strong>
                      <div className="metric-sub">
                        <code>{app.executable_name}</code> ({app.category})
                      </div>
                    </td>
                    <td>
                      <code style={{ fontSize: '0.75rem' }}>
                        {app.executable_sha256.slice(0, 16)}…
                      </code>
                    </td>
                    <td>
                      <select
                        className="ogk-select"
                        disabled={isReadOnly}
                        value={app.decision}
                        onChange={(e) => {
                          const nextApps = [...draft.apps];
                          nextApps[idx] = {
                            ...app,
                            decision: e.target.value as 'allow' | 'block',
                          };
                          setDraft({ ...draft, apps: nextApps });
                        }}
                      >
                        <option value="allow">Cho phép</option>
                        <option value="block">Chặn</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!isReadOnly && (
            <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
              <input
                className="ogk-input"
                placeholder="Tên hiển thị (vd: Game demo)"
                value={newAppName}
                onChange={(e) => setNewAppName(e.target.value)}
              />
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input
                  className="ogk-input"
                  placeholder="file.exe"
                  value={newExeName}
                  onChange={(e) => setNewExeName(e.target.value)}
                />
                <select
                  className="ogk-select"
                  value={newAppCategory}
                  onChange={(e) => setNewAppCategory(e.target.value as AppCategory)}
                >
                  <option value="education">education</option>
                  <option value="entertainment">entertainment</option>
                  <option value="games">games</option>
                  <option value="other">other</option>
                </select>
              </div>
              <input
                className="ogk-input"
                placeholder="SHA-256 (64 ký tự hex, tùy chọn)"
                value={newExeHash}
                onChange={(e) => setNewExeHash(e.target.value)}
              />
              <button type="button" className="btn btn-sm" onClick={handleAddAppRule}>
                Thêm quy tắc ứng dụng
              </button>
            </div>
          )}
        </section>
      </div>

      {!isReadOnly && (
        <section className="card">
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              type="button"
              className="btn"
              onClick={() => setShowPreview((prev) => !prev)}
            >
              {showPreview ? 'Ẩn xem trước thay đổi' : 'Xem trước thay đổi chính sách'}
            </button>
            <button type="button" className="btn btn-primary" onClick={() => void handleSave()}>
              Lưu chính sách (từ v{baseVersion})
            </button>
          </div>
          {showPreview && (
            <pre
              style={{
                marginTop: 12,
                padding: 12,
                background: 'var(--bg-soft)',
                borderRadius: 8,
                overflowX: 'auto',
                fontSize: '0.8rem',
              }}
            >
              {JSON.stringify(
                {
                  expected_version: baseVersion,
                  total_daily_minutes: Math.round(draft.quotas.total_daily_seconds / 60),
                  schedule_slots_count: draft.schedule.length,
                  blocked_apps: draft.apps
                    .filter((a) => a.decision === 'block')
                    .map((a) => a.executable_name),
                },
                null,
                2,
              )}
            </pre>
          )}
        </section>
      )}
    </div>
  );
}
