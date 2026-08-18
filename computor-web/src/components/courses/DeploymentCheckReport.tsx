'use client';

import type { ReactNode } from 'react';
import type { CourseDeployResult, CourseDeployWarning } from '@/src/generated/types/common';
import Button from '../ui/Button';
import Spinner from '../ui/Spinner';

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
const NEUTRAL = 'border-gray-200 bg-gray-50';

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
  return (
    <div className="mt-2">
      <div>
        <Button variant="ghost" size="xs" onClick={onClear}>
          Clear file
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
  if (status === 'waiting') {
    return (
      <div className={`${BOX} ${NEUTRAL} text-gray-500`}>
        Select a course family above — the file is then checked automatically.
      </div>
    );
  }

  if (status === 'checking') {
    return (
      <div className={`${BOX} ${NEUTRAL} flex items-center gap-2 text-gray-500`}>
        <Spinner size="sm" label="Checking the file" />
        Checking the file…
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className={`${BOX} border-red-200 bg-red-50 text-red-700`}>
        <div className="font-medium">This file can’t be used.</div>
        <div>{failure}</div>
        {onRecheck && (
          <div className="pt-1">
            <Button variant="ghost" size="xs" onClick={onRecheck}>
              Check again
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
    ? 'border-red-200 bg-red-50'
    : warnings.length
      ? 'border-amber-200 bg-amber-50'
      : NEUTRAL;

  return (
    <div className={`${BOX} ${tone}`}>
      <div className="text-gray-700">
        <span className="font-medium">{result.course_title || result.course_path}</span>{' '}
        <span className="font-mono text-gray-500">({result.course_path})</span>
      </div>
      <div className="text-gray-500">
        {s.content_types ?? 0} content types · {s.units ?? 0} units · {s.assignments ?? 0} assignments ·{' '}
        {s.examples_assigned ?? 0} examples
      </div>

      {errors.length > 0 && (
        <div className="pt-1 text-red-700">
          <div className="font-medium">
            {errors.length === 1 ? '1 problem blocks' : `${errors.length} problems block`} this file
            — fix it and upload it again:
          </div>
          <ul className="list-disc pl-4">
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="pt-1 text-amber-700">
          <div className="font-medium">
            {warnings.length === 1 ? '1 thing is' : `${warnings.length} things are`} missing or
            incomplete{createdCourseId ? ':' : ' — the course can still be created:'}
          </div>
          <ul className="list-disc pl-4">
            {warnings.map((w, i) => (
              <li key={i}>{warningText(w)}</li>
            ))}
          </ul>
        </div>
      )}

      {errors.length === 0 && warnings.length === 0 && !createdCourseId && (
        <div className="text-green-700">Everything checks out — ready to create.</div>
      )}

      {createdCourseId && (
        <div className="flex items-center gap-2 pt-1 text-green-700">
          <span>Course created{warnings.length > 0 ? ' with the issues above.' : '.'}</span>
          <Button variant="ghost" size="xs" onClick={onOpenCourse}>
            Open course
          </Button>
        </div>
      )}
    </div>
  );
}
