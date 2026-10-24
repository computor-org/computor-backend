'use client';

import SectionCard from '@/src/components/SectionCard';
import Panel from '@/src/components/ui/Panel';
import ProgressTrack from '@/src/components/ui/ProgressTrack';
import { ButtonLink } from '@/src/components/ui/Button';
import { formatScore } from '@/src/components/ui/Score';
import { displayName } from '@/src/utils/displayName';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useResource } from '@/src/hooks/useResource';
import { courseProgress, progressPercent, type CourseProgress, type ProgressContent } from '@/src/utils/studentProgress';
import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';

const COPY = {
  de: {
    title: 'Dein Fortschritt',
    count: (s: number, t: number) => `${s} von ${t} ${t === 1 ? 'Aufgabe' : 'Aufgaben'} eingereicht`,
    barLabel: 'Eingereichte Aufgaben',
    continueWith: 'Weiter mit',
    startWith: 'Beginne mit',
    lastTested: (score: string) => `zuletzt getestet: ${score}`,
    open: 'Aufgabe öffnen',
    all: 'Alle Aufgaben',
    done: 'Du hast alle Aufgaben eingereicht. Deine Ergebnisse und Bewertungen findest du bei den Aufgaben.',
  },
  en: {
    title: 'Your progress',
    count: (s: number, t: number) => `${s} of ${t} ${t === 1 ? 'assignment' : 'assignments'} submitted`,
    barLabel: 'Submitted assignments',
    continueWith: 'Continue with',
    startWith: 'Start with',
    lastTested: (score: string) => `last tested: ${score}`,
    open: 'Open assignment',
    all: 'All assignments',
    done: 'You have submitted every assignment. Your results and grades are listed with the assignments.',
  },
};

/**
 * How far the learner is, and where to pick up (issues#408, #525): one bar over
 * submitted assignments and one "Weiter mit" link to the first assignment that
 * is still open. `compact` drops the card heading and the link to the list, for
 * the top of the assignment list itself.
 */
export function CourseProgressSummary<T extends ProgressContent>({
  courseId,
  progress,
  language,
  compact = false,
}: {
  courseId: string;
  progress: CourseProgress<T>;
  language: UiLanguage;
  compact?: boolean;
}) {
  const t = COPY[language];
  if (progress.total === 0) return null;

  const pct = progressPercent(progress);
  const next = progress.next;
  const score = next?.item.result ? next.item.result.result ?? 0 : null;
  const assignmentsHref = `/courses/${courseId}/student/assignments`;

  const body = (
    <div className="space-y-4" data-testid="course-progress">
      <div className="space-y-1.5">
        <div className="flex items-baseline justify-between gap-3 text-sm">
          <span className="text-fg">{t.count(progress.submitted, progress.total)}</span>
          <span className="text-muted tabular-nums">{pct}%</span>
        </div>
        <ProgressTrack value={pct} tone="green" size="md" label={t.barLabel} />
      </div>

      {next ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="min-w-0 text-sm">
            <span className="text-muted">{progress.started ? t.continueWith : t.startWith}: </span>
            {next.trail.length > 0 && <span className="text-muted">{next.trail.join(' › ')} › </span>}
            <span className="font-medium text-fg">{displayName(next.item)}</span>
            {score != null && <span className="text-muted"> ({t.lastTested(formatScore(score))})</span>}
          </p>
          <div className="flex shrink-0 flex-wrap gap-2">
            <ButtonLink href={`${assignmentsHref}/${next.item.id}`} size="sm">
              {t.open}
            </ButtonLink>
            {!compact && (
              <ButtonLink href={assignmentsHref} variant="secondary" size="sm">
                {t.all}
              </ButtonLink>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-fg">{t.done}</p>
          {!compact && (
            <ButtonLink href={assignmentsHref} variant="secondary" size="sm" className="shrink-0">
              {t.all}
            </ButtonLink>
          )}
        </div>
      )}
    </div>
  );

  return compact ? <Panel>{body}</Panel> : <SectionCard title={t.title}>{body}</SectionCard>;
}

/** The course page's card: loads the learner's own contents and renders the summary. */
export default function CourseProgressCard({ courseId, language }: { courseId: string; language: UiLanguage }) {
  const { data } = useResource(async () => {
    const response = await apiFetch(`${API_BASE_URL}/students/course-contents?course_id=${courseId}`);
    if (!response.ok) return null;
    return (await response.json()) as ProgressContent[];
  }, [courseId]);
  // Quietly absent while loading or on failure: the card is a shortcut, and the
  // assignment list stays the authority.
  if (!Array.isArray(data)) return null;
  return <CourseProgressSummary courseId={courseId} progress={courseProgress(data)} language={language} />;
}
