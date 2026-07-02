/** Formatting + small domain helpers for the lecturer analytics views. */

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${value.toFixed(digits)}%`;
}

export function formatGrade(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toFixed(1);
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return String(value);
}

/** Render an ISO timestamp in the viewer's locale, or an em dash when absent. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatStudentName(student: {
  given_name?: string | null;
  family_name?: string | null;
  username?: string | null;
}): string {
  const full = [student.given_name, student.family_name].filter(Boolean).join(' ').trim();
  return full || student.username || 'Unknown student';
}

/**
 * `<input type="datetime-local">` works in the browser's local time and has no
 * timezone. Convert an ISO instant to the matching local-input value, and back
 * to an ISO-Z instant for the API.
 */
export function isoToLocalInput(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(
    d.getMinutes(),
  )}`;
}

export function localInputToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

/** Late-acceleration markers are review cues, not verdicts — keep the wording
 * neutral and the styling calm. */
export function latenessTone(lateCount: number): {
  label: string;
  className: string;
} {
  if (lateCount <= 0) {
    return { label: 'On time', className: 'text-gray-500' };
  }
  if (lateCount <= 2) {
    return { label: `${lateCount} late`, className: 'text-amber-600' };
  }
  return { label: `${lateCount} late`, className: 'text-orange-600 font-medium' };
}

/** Timeline event relation -> short label + color for the marker. */
export function cutoffRelationTone(relation: string | null | undefined): {
  label: string;
  dot: string;
} {
  switch (relation) {
    case 'before':
      return { label: 'before cutoff', dot: 'bg-emerald-500' };
    case 'after':
      return { label: 'after cutoff', dot: 'bg-orange-500' };
    case 'at':
      return { label: 'at cutoff', dot: 'bg-amber-500' };
    default:
      return { label: '', dot: 'bg-gray-400' };
  }
}
