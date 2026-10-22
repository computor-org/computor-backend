'use client';

import Panel, { PanelList } from '@/src/components/ui/Panel';
import Notice from '@/src/components/ui/Notice';
import Score from '@/src/components/ui/Score';
import EmptyState from '@/src/components/EmptyState';
import GradingStatusBadge from '@/src/components/student/gradingStatus';
import { graderName } from '@/src/utils/graderName';
import { courseRoleLabel, localizedRoleLabel } from '@/src/utils/courseRoles';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
import type {
  SubmissionGroupGradingList,
  SubmissionGroupStudentGet,
} from 'types/generated';

/**
 * What a human said about this student's work.
 *
 * Everything here was already on the wire and thrown away: the page showed the
 * automated test result and nothing else, so a student could not tell whether
 * anyone had looked at their submission, let alone who or when.
 */

const COPY = {
  de: {
    notReviewed: 'Noch nicht geprüft.',
    notGraded: 'Noch nicht bewertet.',
    staffWaiting: 'Die Abgabe wartet auf eine Prüfung.',
    staffNothing: 'Es wurde noch nichts abgegeben.',
    studentWaiting: 'Deine Abgabe wartet darauf, dass ein Tutor sie prüft.',
    studentNothing: 'Reiche deine Arbeit ein, um sie bewerten zu lassen.',
    staleStaff: 'Diese Bewertung gehört zu einer früheren Abgabe. Die letzte Abgabe wurde noch nicht bewertet.',
    staleStudent: 'Diese Bewertung gehört zu einer früheren Abgabe. Deine letzte Abgabe wurde noch nicht bewertet.',
    gradedBy: (by: string) => `Bewertet von ${by}`,
    graderUnknown: 'Bewertende Person unbekannt',
    earlier: 'Frühere Bewertungen',
  },
  en: {
    notReviewed: 'Not reviewed yet.',
    notGraded: 'Not graded yet.',
    staffWaiting: 'The submission is waiting for a review.',
    staffNothing: 'Nothing has been submitted yet.',
    studentWaiting: 'Your submission is waiting for a tutor to look at it.',
    studentNothing: 'Submit your work to have it graded.',
    staleStaff: 'This grade was given on an earlier submission. The most recent submission has not been graded yet.',
    staleStudent: 'This grade was given on an earlier submission. Your most recent submission has not been graded yet.',
    gradedBy: (by: string) => `Graded by ${by}`,
    graderUnknown: 'Grader unknown',
    earlier: 'Earlier grades',
  },
};

/** `graded_at` is the grading's own timestamp; `created_at` is the row's. */
function gradedAt(g: SubmissionGroupGradingList): string {
  return g.graded_at ?? g.created_at;
}

function formatWhen(value: string | null | undefined, language: UiLanguage): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString(language === 'de' ? 'de-AT' : undefined);
}

/** Grader name plus their role, e.g. "Ada Lovelace · Tutor". */
function grader(g: SubmissionGroupGradingList, language: UiLanguage): string | null {
  const name = graderName(g.graded_by_course_member);
  if (!name) return null;
  const role = g.graded_by_course_member?.course_role_id;
  const label = localizedRoleLabel(courseRoleLabel(role), language);
  return role ? `${name} · ${label}` : name;
}

/**
 * The grade that counts, chosen the way the backend chooses it: the newest
 * grading on the artifact the student last submitted. Falling back to the
 * newest grading overall would show a verdict on a superseded attempt as if it
 * were current.
 */
export function currentGrading(
  group: SubmissionGroupStudentGet | null | undefined,
): SubmissionGroupGradingList | null {
  const gradings = group?.gradings ?? [];
  if (gradings.length === 0) return null;

  const byNewest = [...gradings].sort(
    (a, b) => Date.parse(gradedAt(b)) - Date.parse(gradedAt(a)),
  );
  const latestArtifact = group?.latest_submitted_artifact_id;
  // Before the artifact link existed there is nothing to match on, so the
  // newest grading is the best available answer.
  if (!latestArtifact) return byNewest[0];
  return byNewest.find((g) => g.artifact_id === latestArtifact) ?? byNewest[0];
}

/** True when the grade shown was left on a submission that is no longer the latest. */
export function isStaleGrading(
  group: SubmissionGroupStudentGet | null | undefined,
  current: SubmissionGroupGradingList | null,
): boolean {
  const latestArtifact = group?.latest_submitted_artifact_id;
  return Boolean(latestArtifact && current?.artifact_id && current.artifact_id !== latestArtifact);
}

/**
 * `gradings[].status` is the numeric GradingStatus, while the content-level
 * `status` fields are already slugs. Map the one to the other so both go
 * through the same badge.
 */
const STATUS_SLUG = [
  'not_reviewed',
  'corrected',
  'correction_necessary',
  'improvement_possible',
] as const;

export function statusSlug(status: number | null | undefined): string | null {
  return status == null ? null : (STATUS_SLUG[status] ?? null);
}

function GradingRow({ entry }: { entry: SubmissionGroupGradingList }) {
  const language = useUiLanguage();
  const t = COPY[language];
  const by = grader(entry, language);
  return (
    <div className="px-4 py-3 space-y-1">
      <div className="flex flex-wrap items-center gap-3">
        <Score value={entry.grading} decimals={1} />
        <GradingStatusBadge status={statusSlug(entry.status)} />
        <span className="text-xs text-subtle">{formatWhen(gradedAt(entry), language)}</span>
      </div>
      <p className="text-xs text-muted">{by ? t.gradedBy(by) : t.graderUnknown}</p>
      {entry.feedback && <p className="text-sm text-body whitespace-pre-wrap">{entry.feedback}</p>}
    </div>
  );
}

export default function GradingPanel({
  group,
  submitted,
  audience = 'student',
}: {
  group: SubmissionGroupStudentGet | null | undefined;
  submitted?: boolean | null;
  /** Wording only: the student reads "your submission", staff read "the submission". */
  audience?: 'student' | 'staff';
}) {
  const language = useUiLanguage();
  const t = COPY[language];
  const staff = audience === 'staff';
  const current = currentGrading(group);
  // A group can carry a headline grade without a gradings array behind it, so
  // the flat fields are the fallback rather than an alternative source.
  const grade = current?.grading ?? group?.grading ?? null;
  const status = current ? statusSlug(current.status) : (group?.status ?? null);

  if (grade == null && !status) {
    return (
      <EmptyState
        compact
        title={submitted ? t.notReviewed : t.notGraded}
        description={
          staff
            ? submitted
              ? t.staffWaiting
              : t.staffNothing
            : submitted
              ? t.studentWaiting
              : t.studentNothing
        }
      />
    );
  }

  const by = current ? grader(current, language) : graderName(group?.graded_by_course_member);
  const history = (group?.gradings ?? [])
    .filter((g) => g.id !== current?.id)
    .sort((a, b) => Date.parse(gradedAt(b)) - Date.parse(gradedAt(a)));

  return (
    <>
      {isStaleGrading(group, current) && (
        <Notice tone="warning">
          {staff ? t.staleStaff : t.staleStudent}
        </Notice>
      )}

      <Panel padding="compact" className="bg-canvas space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <Score value={grade} decimals={1} className="text-lg" />
          <GradingStatusBadge status={status} />
          {current && <span className="text-xs text-subtle">{formatWhen(gradedAt(current), language)}</span>}
        </div>
        <p className="text-xs text-muted">{by ? t.gradedBy(by) : t.graderUnknown}</p>
        {current?.feedback && (
          <p className="text-sm text-body whitespace-pre-wrap">{current.feedback}</p>
        )}
      </Panel>

      {history.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-fg">{t.earlier}</h3>
          <PanelList>
            {history.map((entry) => (
              <GradingRow key={entry.id} entry={entry} />
            ))}
          </PanelList>
        </div>
      )}
    </>
  );
}
