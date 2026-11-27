import type { ScheduleSlot } from '../types/ogk';

export const DAY_LABELS = [
  'Thứ 2',
  'Thứ 3',
  'Thứ 4',
  'Thứ 5',
  'Thứ 6',
  'Thứ 7',
  'Chủ nhật',
] as const;

const TIME_PATTERN = /^(?:[01][0-9]|2[0-3]):(?:00|30)$/;

export function timeToMinutes(hhmm: string): number {
  const [hoursText, minutesText] = hhmm.split(':');
  return Number(hoursText) * 60 + Number(minutesText);
}

export function minutesToTime(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

export interface ScheduleValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Validate 7x48 half-open schedule slots [start, end) per docs/POLICY_RULES.md:
 * - No empty slots (start >= end rejected)
 * - No cross-midnight slots (must split into two frames across days)
 * - No overlapping intervals on the same day
 * - Only 30-minute boundary resolution (00 / 30)
 */
export function validateScheduleSlots(slots: ScheduleSlot[]): ScheduleValidationResult {
  const errors: string[] = [];
  const byDay = new Map<number, ScheduleSlot[]>();

  for (const slot of slots) {
    if (slot.day_of_week < 0 || slot.day_of_week > 6) {
      errors.push(`Thứ không hợp lệ: ${slot.day_of_week}.`);
      continue;
    }
    if (!TIME_PATTERN.test(slot.start) || !TIME_PATTERN.test(slot.end)) {
      errors.push(
        `${DAY_LABELS[slot.day_of_week]}: giờ phải đúng bội số 30 phút HH:00 hoặc HH:30 (${slot.start}–${slot.end}).`,
      );
      continue;
    }
    const startMinutes = timeToMinutes(slot.start);
    const endMinutes = timeToMinutes(slot.end);

    if (startMinutes > endMinutes) {
      errors.push(
        `${DAY_LABELS[slot.day_of_week]} (${slot.start}–${slot.end}): Không cho phép khung giờ qua nửa đêm; hãy tách thành 2 khung riêng.`,
      );
      continue;
    }
    if (startMinutes === endMinutes) {
      errors.push(
        `${DAY_LABELS[slot.day_of_week]} (${slot.start}–${slot.end}): Khung giờ rỗng không hợp lệ.`,
      );
      continue;
    }

    const dayList = byDay.get(slot.day_of_week) ?? [];
    dayList.push(slot);
    byDay.set(slot.day_of_week, dayList);
  }

  for (const [day, daySlots] of byDay.entries()) {
    const sorted = [...daySlots].sort(
      (a, b) => timeToMinutes(a.start) - timeToMinutes(b.start),
    );
    for (let i = 1; i < sorted.length; i += 1) {
      const prev = sorted[i - 1];
      const curr = sorted[i];
      if (timeToMinutes(curr.start) < timeToMinutes(prev.end)) {
        errors.push(
          `${DAY_LABELS[day]}: Khung ${prev.start}–${prev.end} bị trùng với ${curr.start}–${curr.end}.`,
        );
      }
    }
  }

  return { valid: errors.length === 0, errors };
}

export function normalizeDomainInput(raw: string): string | null {
  const trimmed = raw.trim().toLowerCase().replace(/\.+$/, '');
  if (!trimmed || trimmed.length > 253) {
    return null;
  }
  const domainRegex =
    /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
  return domainRegex.test(trimmed) ? trimmed : null;
}

export function formatDuration(seconds: number): string {
  const clamped = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(clamped / 3600);
  const minutes = Math.floor((clamped % 3600) / 60);
  if (hours > 0) {
    return `${hours}g ${minutes}p`;
  }
  return `${minutes}p`;
}

export function formatTimeShort(isoString: string): string {
  const parsed = new Date(isoString);
  if (Number.isNaN(parsed.getTime())) {
    return isoString;
  }
  return parsed.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
  });
}
