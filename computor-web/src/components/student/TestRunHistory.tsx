'use client';

import Panel from '@/src/components/ui/Panel';
import Score from '@/src/components/ui/Score';
import Badge from '@/src/components/Badge';
import EmptyState from '@/src/components/EmptyState';
import type { Tone } from '@/src/components/ui/tones';
import type { ResultList, SubmissionArtifactList, TaskStatus } from 'types/generated';

/**
 * Every test run on this assignment, newest first.
 *
 * A `Result` knows which artifact it ran against but not whether that artifact
 * was an official submission, so the artifact list is joined in to tell a
 * practice run apart from a submitted one. (The VS Code extension shows the
 * same table but hardcodes `submit: null`, so its "Submission" chip never
 * appears.)
 */

/** TaskStatus, as the test system reports it — not a grading verdict. */
const STATUS_TONE: Record<TaskStatus, Tone> = {
  finished: 'success',
  failed: 'error',
  cancelled: 'muted',
  deferred: 'muted',
  queued: 'warning',
  started: 'warning',
};

function statusTone(status: TaskStatus | null | undefined): Tone {
  return (status && STATUS_TONE[status]) || 'muted';
}

function formatWhen(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

export default function TestRunHistory({
  results,
  artifacts,
}: {
  results: ResultList[];
  artifacts: SubmissionArtifactList[];
}) {
  if (results.length === 0) {
    return <EmptyState compact title="No test runs yet." />;
  }

  const submitted = new Set(
    artifacts.filter((a) => a.submit).map((a) => a.id),
  );
  const rows = [...results].sort(
    (a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? ''),
  );

  return (
    <Panel padding="none" className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-canvas border-b border-rule text-xs font-medium text-muted">
            <th className="text-left py-2 px-4">When</th>
            <th className="text-left py-2 px-4">Kind</th>
            <th className="text-left py-2 px-4">Version</th>
            <th className="text-right py-2 px-4">Result</th>
            <th className="text-left py-2 px-4">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule-soft">
          {rows.map((r) => {
            const isSubmission = r.submission_artifact_id != null && submitted.has(r.submission_artifact_id);
            return (
              <tr key={r.id}>
                <td className="py-2 px-4 text-muted whitespace-nowrap">{formatWhen(r.created_at)}</td>
                <td className="py-2 px-4">
                  <Badge tone={isSubmission ? 'info' : 'muted'}>
                    {isSubmission ? 'Submission' : 'Test run'}
                  </Badge>
                </td>
                <td className="py-2 px-4 font-mono text-xs text-muted">
                  {r.version_identifier ? r.version_identifier.slice(0, 8) : '—'}
                </td>
                <td className="py-2 px-4 text-right">
                  <Score value={r.result} decimals={1} />
                </td>
                <td className="py-2 px-4">
                  <Badge tone={statusTone(r.status)}>{r.status ?? 'unknown'}</Badge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}
