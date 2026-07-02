'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AnalyticsApiError,
  getJob,
  isFailedJob,
  isTerminalJob,
  triggerRefresh,
  type AnalyticsCutoffs,
  type AnalyticsJobStatus,
} from '@/src/api/analytics';
import { formatDateTime } from './format';

/**
 * One-click import of the latest data from the source ("green") site into the
 * analytics store. Starts an audited job and polls it to completion, then asks
 * the page to reload. The button keeps the same verb through the flow:
 * "Update data" -> "Updating…" -> back to "Update data".
 */
export default function RefreshControl({
  courseId,
  cutoffs,
  initialJob,
  onRefreshed,
}: {
  courseId: string;
  cutoffs: AnalyticsCutoffs;
  initialJob?: AnalyticsJobStatus | null;
  onRefreshed: () => void;
}) {
  // `liveJob` is set once a refresh runs in this control; until then we show the
  // job the page handed us from the latest summary. Deriving rather than syncing
  // via an effect keeps the two sources in order without a cascading render.
  const [liveJob, setLiveJob] = useState<AnalyticsJobStatus | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const job = liveJob ?? initialJob ?? null;

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const poll = useCallback(
    (jobId: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const next = await getJob(jobId);
          setLiveJob(next);
          if (isTerminalJob(next.status)) {
            stopPolling();
            setRunning(false);
            if (!isFailedJob(next.status)) {
              onRefreshed();
            } else {
              setError(next.error || 'The update job failed.');
            }
          }
        } catch (e) {
          stopPolling();
          setRunning(false);
          setError(e instanceof Error ? e.message : 'Lost contact with the update job.');
        }
      }, 2000);
    },
    [onRefreshed, stopPolling],
  );

  const start = useCallback(async () => {
    setError(null);
    setRunning(true);
    try {
      const started = await triggerRefresh(courseId, {
        source_name: 'green',
        submission_cutoff: cutoffs.submissionCutoff ?? null,
        grading_cutoff: cutoffs.gradingCutoff ?? null,
      });
      setLiveJob(started);
      if (isTerminalJob(started.status)) {
        setRunning(false);
        if (!isFailedJob(started.status)) onRefreshed();
        else setError(started.error || 'The update job failed.');
      } else {
        poll(started.job_id);
      }
    } catch (e) {
      setRunning(false);
      if (e instanceof AnalyticsApiError && e.status === 403) {
        setError('You need a lecturer role on this course to update analytics.');
      } else {
        setError(e instanceof Error ? e.message : 'Could not start the update.');
      }
    }
  }, [courseId, cutoffs, onRefreshed, poll]);

  const rowTotal = job ? Object.values(job.row_counts ?? {}).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={start}
        disabled={running}
        data-testid="analytics-refresh"
        className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <svg
          className={`h-4 w-4 ${running ? 'animate-spin' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        {running ? 'Updating…' : 'Update data'}
      </button>
      <JobLine job={job} running={running} rowTotal={rowTotal} />
      {error && (
        <p className="max-w-xs text-right text-xs text-red-600" data-testid="analytics-refresh-error">
          {error}
        </p>
      )}
    </div>
  );
}

function JobLine({
  job,
  running,
  rowTotal,
}: {
  job: AnalyticsJobStatus | null;
  running: boolean;
  rowTotal: number;
}) {
  if (!job) {
    return <p className="text-xs text-gray-400">No update has run yet.</p>;
  }
  const when = formatDateTime(job.finished_at || job.started_at || job.created_at);
  return (
    <p className="text-right text-xs text-gray-500" data-testid="analytics-job-status">
      <span className="font-medium">{running ? 'Importing from green…' : `Last update: ${job.status}`}</span>
      {' · '}
      {when}
      {rowTotal > 0 && ` · ${rowTotal.toLocaleString()} rows`}
    </p>
  );
}
