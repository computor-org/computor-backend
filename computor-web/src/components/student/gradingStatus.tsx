'use client';

import Badge from '@/src/components/Badge';
import type { Tone } from '@/src/components/ui/tones';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';

/**
 * The grading-status vocabulary, in one place.
 *
 * These four slugs come straight off `GradingStatus` in
 * computor-types/grading.py (0..3 → snake_case) and reach the client as strings
 * on `CourseContentStudent*.status` / `.latest_grade_status` and on every entry
 * of `submission_group.gradings`.
 *
 * The mapping used to live twice, in two visual languages and with two spellings
 * of the same state — `ContentTree` said "Correction needed", `NeedsAttention`
 * said "Correction necessary". A third call site is what made that a problem, so
 * both now read from here. The backend's own wording wins.
 *
 * `dot` exists because the grading table draws a coloured dot rather than a
 * chip; it is the same tone expressed as a fill.
 */
export type GradingStatusSlug =
  | 'not_reviewed'
  | 'corrected'
  | 'correction_necessary'
  | 'improvement_possible';

export const GRADING_STATUS: Record<
  GradingStatusSlug,
  { label: string; tone: Tone; dot: string }
> = {
  corrected: { label: 'Corrected', tone: 'success', dot: 'bg-success' },
  correction_necessary: { label: 'Correction necessary', tone: 'error', dot: 'bg-danger' },
  improvement_possible: { label: 'Improvement possible', tone: 'warning', dot: 'bg-amber-500' },
  not_reviewed: { label: 'Not reviewed', tone: 'muted', dot: 'bg-faint' },
};

/** Display labels per language. `GRADING_STATUS[x].label` stays the English wording. */
const GRADING_LABEL: Record<UiLanguage, Record<GradingStatusSlug, string>> = {
  de: {
    corrected: 'Korrigiert',
    correction_necessary: 'Korrektur nötig',
    improvement_possible: 'Verbesserung möglich',
    not_reviewed: 'Nicht geprüft',
  },
  en: {
    corrected: GRADING_STATUS.corrected.label,
    correction_necessary: GRADING_STATUS.correction_necessary.label,
    improvement_possible: GRADING_STATUS.improvement_possible.label,
    not_reviewed: GRADING_STATUS.not_reviewed.label,
  },
};

export function isGradingStatus(status: string | null | undefined): status is GradingStatusSlug {
  return status != null && status in GRADING_STATUS;
}

/** `-` for an unknown or absent status, matching how the tables read today. */
export function gradingStatusLabel(
  status: string | null | undefined,
  language: UiLanguage = 'en',
): string {
  return isGradingStatus(status) ? GRADING_LABEL[language][status] : '-';
}

export function gradingStatusTone(status: string | null | undefined): Tone {
  return isGradingStatus(status) ? GRADING_STATUS[status].tone : 'muted';
}

export function gradingStatusDot(status: string | null | undefined): string {
  return isGradingStatus(status) ? GRADING_STATUS[status].dot : 'bg-faint';
}

/**
 * A verdict a human has actually reached. `not_reviewed` and an absent status
 * are both "nobody has looked at this yet", which is the default state of most
 * of a semester and is not worth a chip on every row.
 */
export function isGradingVerdict(status: string | null | undefined): status is GradingStatusSlug {
  return isGradingStatus(status) && status !== 'not_reviewed';
}

export default function GradingStatusBadge({
  status,
  className = '',
  language,
}: {
  status: string | null | undefined;
  className?: string;
  /** Defaults to the signed-in interface language. */
  language?: UiLanguage;
}) {
  const uiLanguage = useUiLanguage();
  if (!isGradingStatus(status)) return null;
  return (
    <Badge tone={GRADING_STATUS[status].tone} className={className}>
      {gradingStatusLabel(status, language ?? uiLanguage)}
    </Badge>
  );
}
