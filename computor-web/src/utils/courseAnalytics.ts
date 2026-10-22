/**
 * Small pure helpers for the lecturer analytics views (typical errors,
 * attempt timeline, flags). Kept free of React so they can be unit-tested.
 */

import type { Tone } from '@/src/components/ui/tones';
import type {
  ActivityEvent,
  FlagReason,
  TypicalError,
} from 'types/generated';

/** "45 min", "2 h 5 min", "3 d 4 h" — for durations and estimates. */
export function formatMinutes(minutes: number | null | undefined): string {
  if (minutes == null || Number.isNaN(minutes)) return '—';
  const m = Math.round(minutes);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) {
    const rest = m % 60;
    return rest ? `${h} h ${rest} min` : `${h} h`;
  }
  const d = Math.floor(h / 24);
  const restH = h % 24;
  return restH ? `${d} d ${restH} h` : `${d} d`;
}

/** Relation of the last submission to the due date, in words. */
export function formatDueRelation(hoursBeforeDue: number | null | undefined): string {
  if (hoursBeforeDue == null) return '—';
  const text = formatMinutes(Math.abs(hoursBeforeDue) * 60);
  return hoursBeforeDue >= 0 ? `${text} before due` : `${text} after due`;
}

export function flagTone(severity: string | null | undefined): Tone {
  return severity === 'warning' ? 'warning' : 'info';
}

/** Warnings first, then by title, so the most pressing reason leads. */
export function sortFlags(flags: FlagReason[]): FlagReason[] {
  const rank = (f: FlagReason) => (f.severity === 'warning' ? 0 : 1);
  return [...flags].sort(
    (a, b) =>
      rank(a) - rank(b) ||
      a.title.localeCompare(b.title) ||
      (a.course_content_title ?? '').localeCompare(b.course_content_title ?? ''),
  );
}

/** Distinct assignments mentioned in a list of typical errors, by title. */
export function assignmentsOf(errors: TypicalError[]): { id: string; title: string }[] {
  const seen = new Map<string, string>();
  for (const e of errors) {
    if (!seen.has(e.course_content_id)) {
      seen.set(e.course_content_id, e.course_content_title || e.course_content_id);
    }
  }
  return [...seen.entries()]
    .map(([id, title]) => ({ id, title }))
    .sort((a, b) => a.title.localeCompare(b.title));
}

export interface StripMark {
  /** 0..1 along the strip. */
  x: number;
  kind: string;
  grade: number | null;
  at: string;
}

/**
 * Place events of one assignment on a shared time axis [start, end]. Events
 * outside the window are clamped to its edges; an empty window puts every
 * mark in the middle.
 */
export function stripMarks(events: ActivityEvent[], start: number, end: number): StripMark[] {
  const span = end - start;
  return events
    .filter((e) => e.kind === 'test_run' || e.kind === 'submission')
    .map((e) => {
      const t = Date.parse(e.at);
      const x = span > 0 ? Math.min(1, Math.max(0, (t - start) / span)) : 0.5;
      return { x, kind: e.kind, grade: e.grade ?? null, at: e.at };
    })
    .sort((a, b) => a.x - b.x);
}
