'use client';

import type { ReactNode } from 'react';
import type { CourseDeployResult, CourseDeployWarning } from '@/src/generated/types/common';
import Button from '../ui/Button';
import Spinner from '../ui/Spinner';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    clear: 'Datei entfernen',
    waiting: 'Wähle oben eine Kursfamilie, dann wird die Datei automatisch geprüft.',
    checking: 'Datei wird geprüft …',
    unusable: 'Diese Datei lässt sich nicht verwenden.',
    recheck: 'Erneut prüfen',
    counts: (types: number, units: number, assignments: number, examples: number) =>
      `${types} Inhaltstypen · ${units} Einheiten · ${assignments} Aufgaben · ${examples} Beispiele`,
    errors: (n: number) => n === 1
      ? 'Ein Problem blockiert diese Datei. Behebe es und lade sie erneut hoch:'
      : `${n} Probleme blockieren diese Datei. Behebe sie und lade sie erneut hoch:`,
    warnings: (n: number, created: boolean) => (n === 1
      ? 'Eine Angabe fehlt oder ist unvollständig'
      : `${n} Angaben fehlen oder sind unvollständig`) + (created ? ':' : '. Der Kurs kann trotzdem angelegt werden:'),
    ready: 'Alles in Ordnung, der Kurs kann angelegt werden.',
    created: (withIssues: boolean) => withIssues ? 'Kurs angelegt, mit den oben genannten Mängeln.' : 'Kurs angelegt.',
    open: 'Kurs öffnen',
  },
  en: {
    clear: 'Clear file',
    waiting: 'Select a course family above — the file is then checked automatically.',
    checking: 'Checking the file…',
    unusable: 'This file can’t be used.',
    recheck: 'Check again',
    counts: (types: number, units: number, assignments: number, examples: number) =>
      `${types} content types · ${units} units · ${assignments} assignments · ${examples} examples`,
    errors: (n: number) => `${n === 1 ? '1 problem blocks' : `${n} problems block`} this file — fix it and upload it again:`,
    warnings: (n: number, created: boolean) =>
      `${n === 1 ? '1 thing is' : `${n} things are`} missing or incomplete${created ? ':' : ' — the course can still be created:'}`,
    ready: 'Everything checks out — ready to create.',
    created: (withIssues: boolean) => `Course created${withIssues ? ' with the issues above.' : '.'}`,
    open: 'Open course',
  },
};

/**
 * Where the automatic check of an uploaded `course_deployment.yaml` stands.
 *
 * `waiting` — a file is loaded but no course family is picked yet, so there is
 * nothing to check it against; `checking` — a validate-only deploy is in flight.
 */
export type DeployCheckStatus = 'waiting' | 'checking' | 'done' | 'failed';

/** "path: reason" — the path is what makes a warning actionable. */
export function warningText(w: CourseDeployWarning): string {
  return w.path ? `${w.path}: ${w.reason}` : w.reason;
}

const BOX = 'mt-2 rounded-md border p-3 text-xs space-y-1';
const NEUTRAL = 'border-rule bg-canvas';

/**
 * Verdict of the automatic validate pass, shown under the file field. It is the
 * only place the user learns what the uploaded file will produce, so it always
 * says something: which course, the counts, and every error and warning
 * verbatim.
 */
export default function DeploymentCheckReport({
  status,
  result,
  failure,
  createdCourseId,
  onClear,
  onRecheck,
  onOpenCourse,
}: {
  status: DeployCheckStatus;
  result: CourseDeployResult | null;
  failure?: string | null;
  /** Set once the course has been created — the verdict then reports what happened. */
  createdCourseId?: string | null;
  onClear: () => void;
  onRecheck?: () => void;
  onOpenCourse?: () => void;
}) {
  const t = COPY[useUiLanguage()];
  return (
    <div className="mt-2">
      <div>
        <Button variant="ghost" size="xs" onClick={onClear}>
          {t.clear}
        </Button>
      </div>
      <Verdict
        status={status}
        result={result}
        failure={failure}
        createdCourseId={createdCourseId}
        onRecheck={onRecheck}
        onOpenCourse={onOpenCourse}
      />
    </div>
  );
}

function Verdict({
  status,
  result,
  failure,
  createdCourseId,
  onRecheck,
  onOpenCourse,
}: {
  status: DeployCheckStatus;
  result: CourseDeployResult | null;
  failure?: string | null;
  createdCourseId?: string | null;
  onRecheck?: () => void;
  onOpenCourse?: () => void;
}): ReactNode {
  const t = COPY[useUiLanguage()];
  if (status === 'waiting') {
    return (
      <div className={`${BOX} ${NEUTRAL} text-muted`}>
        {t.waiting}
      </div>
    );
  }

  if (status === 'checking') {
    return (
      <div className={`${BOX} ${NEUTRAL} flex items-center gap-2 text-muted`}>
        <Spinner size="sm" label={t.checking} />
        {t.checking}
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className={`${BOX} border-danger-line bg-danger-wash text-danger-text`}>
        <div className="font-medium">{t.unusable}</div>
        <div>{failure}</div>
        {onRecheck && (
          <div className="pt-1">
            <Button variant="ghost" size="xs" onClick={onRecheck}>
              {t.recheck}
            </Button>
          </div>
        )}
      </div>
    );
  }

  if (!result) return null;

  const errors = result.errors ?? [];
  const warnings = result.warnings ?? [];
  const s = result.summary ?? {};
  const tone = errors.length
    ? 'border-danger-line bg-danger-wash'
    : warnings.length
      ? 'border-warn-line bg-warn-wash'
      : NEUTRAL;

  return (
    <div className={`${BOX} ${tone}`}>
      <div className="text-body">
        <span className="font-medium">{result.course_title || result.course_path}</span>{' '}
        <span className="font-mono text-muted">({result.course_path})</span>
      </div>
      <div className="text-muted">
        {t.counts(s.content_types ?? 0, s.units ?? 0, s.assignments ?? 0, s.examples_assigned ?? 0)}
      </div>

      {errors.length > 0 && (
        <div className="pt-1 text-danger-text">
          <div className="font-medium">{t.errors(errors.length)}</div>
          <ul className="list-disc pl-4">
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="pt-1 text-warn-text">
          <div className="font-medium">{t.warnings(warnings.length, Boolean(createdCourseId))}</div>
          <ul className="list-disc pl-4">
            {warnings.map((w, i) => (
              <li key={i}>{warningText(w)}</li>
            ))}
          </ul>
        </div>
      )}

      {errors.length === 0 && warnings.length === 0 && !createdCourseId && (
        <div className="text-success-text">{t.ready}</div>
      )}

      {createdCourseId && (
        <div className="flex items-center gap-2 pt-1 text-success-text">
          <span>{t.created(warnings.length > 0)}</span>
          <Button variant="ghost" size="xs" onClick={onOpenCourse}>
            {t.open}
          </Button>
        </div>
      )}
    </div>
  );
}
