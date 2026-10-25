'use client';

import Panel from '@/src/components/ui/Panel';
import Score from '@/src/components/ui/Score';
import Badge from '@/src/components/Badge';
import EmptyState from '@/src/components/EmptyState';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
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

const COPY = {
  de: {
    none: 'Noch keine Testläufe.',
    when: 'Zeitpunkt',
    kind: 'Art',
    version: 'Version',
    result: 'Ergebnis',
    status: 'Status',
    submission: 'Abgabe',
    testRun: 'Testlauf',
    unknown: 'unbekannt',
  },
  en: {
    none: 'No test runs yet.',
    when: 'When',
    kind: 'Kind',
    version: 'Version',
    result: 'Result',
    status: 'Status',
    submission: 'Submission',
    testRun: 'Test run',
    unknown: 'unknown',
  },
};

const STATUS_DE: Record<TaskStatus, string> = {
  finished: 'abgeschlossen',
  failed: 'fehlgeschlagen',
  cancelled: 'abgebrochen',
  deferred: 'zurückgestellt',
  queued: 'in Warteschlange',
  started: 'gestartet',
};

/** TaskStatus, as the test system reports it — not a grading verdict. */
const STATUS_TONE: Record<TaskStatus, Tone> = {
  finished: 'success',
  failed: 'error',
  cancelled: 'muted',
  deferred: 'muted',
  queued: 'warning',
  started: 'warning',
};

export function statusTone(status: TaskStatus | null | undefined): Tone {
  return (status && STATUS_TONE[status]) || 'muted';
}

function formatWhen(value: string | null | undefined, language: UiLanguage): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString(language === 'de' ? 'de-AT' : undefined);
}

/**
 * A commit hash shortens to its first eight characters, as in git. Other
 * version identifiers (a VS Code submission's "qa-returning-week_1.basis1")
 * are names, and cutting them off at eight characters leaves "qa-retur".
 */
function shortVersion(version: string): string {
  return /^[0-9a-f]{12,64}$/i.test(version) ? version.slice(0, 8) : version;
}

export default function TestRunHistory({
  results,
  artifacts,
}: {
  results: ResultList[];
  artifacts: SubmissionArtifactList[];
}) {
  const language = useUiLanguage();
  const t = COPY[language];
  if (results.length === 0) {
    return <EmptyState compact title={t.none} />;
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
            <th className="text-left py-2 px-4">{t.when}</th>
            <th className="text-left py-2 px-4">{t.kind}</th>
            <th className="text-left py-2 px-4">{t.version}</th>
            <th className="text-right py-2 px-4">{t.result}</th>
            <th className="text-left py-2 px-4">{t.status}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-rule-soft">
          {rows.map((r) => {
            const isSubmission = r.submission_artifact_id != null && submitted.has(r.submission_artifact_id);
            return (
              <tr key={r.id}>
                <td className="py-2 px-4 text-muted whitespace-nowrap">{formatWhen(r.created_at, language)}</td>
                <td className="py-2 px-4">
                  <Badge tone={isSubmission ? 'info' : 'muted'}>
                    {isSubmission ? t.submission : t.testRun}
                  </Badge>
                </td>
                <td className="py-2 px-4 font-mono text-xs text-muted" title={r.version_identifier ?? undefined}>
                  {r.version_identifier ? shortVersion(r.version_identifier) : '—'}
                </td>
                <td className="py-2 px-4 text-right">
                  <Score value={r.result} decimals={1} />
                </td>
                <td className="py-2 px-4">
                  <Badge tone={statusTone(r.status)}>{r.status ? (language === 'de' ? STATUS_DE[r.status] ?? r.status : r.status) : t.unknown}</Badge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}
