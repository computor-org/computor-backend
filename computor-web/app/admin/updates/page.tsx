'use client';

import { useEffect, useRef, useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { UpdateClient } from '@/src/clients/UpdateClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import type { SystemUpdateState, SystemUpdateStatusGet } from '@/src/types/update';

const updateClient = new UpdateClient();

/** After this long without API contact during a run, stop assuming "in progress". */
const IN_PROGRESS_GRACE_MS = 30 * 60 * 1000;

const shortCommit = (commit: string | null | undefined) =>
  commit ? commit.slice(0, 7) : '—';

const PHASE_LABELS: Record<string, string> = {
  preflight: 'Running preflight checks',
  checking: 'Fetching from repository',
  checking_out: 'Checking out new version',
  building: 'Building images',
  entering_maintenance: 'Entering maintenance mode',
  starting: 'Starting services',
  health_check: 'Waiting for services to become healthy',
  finalizing: 'Finalizing',
  rolling_back: 'Rolling back to previous version',
};

export default function UpdatesPage() {
  const { isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();
  const notify = useNotify();

  // Poll every 5s. During an update the API goes down: useResource keeps the
  // last data on error, and lastStatusRef lets us render an "in progress"
  // panel instead of a scary error banner until the API comes back.
  const { data: status, loading, error, reload } = useResource(
    () => updateClient.getStatus(),
    [],
    { refetchInterval: 5000 },
  );
  const lastStatusRef = useRef<SystemUpdateStatusGet | null>(null);
  const notifiedOutcomeRef = useRef<string | null>(null);
  if (status) lastStatusRef.current = status;

  const [checking, setChecking] = useState(false);
  const [showUpdateConfirm, setShowUpdateConfirm] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const lastStatus = lastStatusRef.current;
  const state: SystemUpdateState | undefined = (status ?? lastStatus)?.state;
  const runInProgress = state?.status === 'requested' || state?.status === 'running';

  // API unreachable while a run was in progress → expected downtime, not an error.
  const runStartedAt = state?.started_at || state?.requested_at;
  const withinGrace =
    !!runStartedAt && Date.now() - new Date(runStartedAt).getTime() < IN_PROGRESS_GRACE_MS;
  const showDowntimePanel = !!error && runInProgress && withinGrace;

  // When the API comes back with a terminal state, surface the outcome once.
  // (Effect, not render: notify() updates the notification context's state.)
  useEffect(() => {
    if (!status || error || !status.state || runInProgress) return;
    const s = status.state;
    const key = `${s.status}:${s.finished_at ?? ''}`;
    if (
      notifiedOutcomeRef.current !== null &&
      notifiedOutcomeRef.current !== key &&
      (s.status === 'success' || s.status === 'failed' || s.status === 'rolled_back')
    ) {
      notify(
        s.status === 'success'
          ? 'Update completed successfully'
          : s.status === 'rolled_back'
            ? 'Update failed — rolled back to the previous version'
            : 'Update failed',
        s.status === 'success' ? 'success' : 'error',
      );
    }
    notifiedOutcomeRef.current = key;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, error, runInProgress]);

  const handleCheckNow = async () => {
    setChecking(true);
    try {
      await updateClient.checkNow();
      await reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Update check failed', 'error');
    } finally {
      setChecking(false);
    }
  };

  const handleTriggerUpdate = async () => {
    setShowUpdateConfirm(false);
    setTriggering(true);
    try {
      await updateClient.triggerUpdate();
      notify('Update requested — the system will go into maintenance shortly', 'success');
      await reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to request update', 'error');
    } finally {
      setTriggering(false);
    }
  };

  const handleCopyCommit = async (commit: string) => {
    try {
      await navigator.clipboard.writeText(commit);
      notify('Commit hash copied', 'success');
    } catch {
      notify('Could not copy to clipboard', 'error');
    }
  };

  // Access control
  if (!authLoading && !isAdmin) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-red-800">Access Denied</h2>
            <p className="text-sm text-red-600 mt-2">Admin privileges are required to access this page.</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const view = status ?? lastStatus;
  const updateDisabledReason = !view
    ? null
    : !view.update_enabled
      ? 'Self-update is disabled. Set UPDATE_ENABLED=true in .env and restart to enable it.'
      : !view.updater_online
        ? 'The updater sidecar is not running (development environment, or the sidecar is down). Updates can only be triggered in production.'
        : runInProgress
          ? 'An update is already in progress.'
          : null;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Updates' }]}
          title="System Updates"
          subtitle="Compare the running version with the tracked repository branch and run one-click updates."
        />

        {/* API down during an update is expected — show progress, not an error */}
        {showDowntimePanel ? (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-3">
              <svg className="h-5 w-5 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-blue-800">
                  Update in progress — the system is restarting
                </p>
                <p className="text-sm text-blue-700">
                  {(state?.phase && PHASE_LABELS[state.phase]) || 'Working'}… This page will resume
                  automatically when the API is back. Do not close this tab.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <ErrorBanner>{error}</ErrorBanner>
        )}

        <ScrollArea className="space-y-6">
          {/* Loading skeleton */}
          {loading && !view && (
            <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded w-1/4 mb-4" />
              <div className="h-4 bg-gray-200 rounded w-1/2" />
            </div>
          )}

          {view && (
            <>
              {/* Version card */}
              <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Version</h2>
                  {view.update_available ? (
                    <Badge color="yellow" pill>Update available</Badge>
                  ) : view.remote_commit ? (
                    <Badge color="green" pill>Up to date</Badge>
                  ) : null}
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600 w-36">Running commit:</span>
                    <code className="text-sm font-mono text-gray-900">{shortCommit(view.running_commit)}</code>
                    {view.running_commit !== 'unknown' && (
                      <button
                        onClick={() => handleCopyCommit(view.running_commit)}
                        className="text-xs text-blue-600 hover:text-blue-800"
                        title={view.running_commit}
                      >
                        copy full hash
                      </button>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600 w-36">Running branch:</span>
                    <span className="text-sm text-gray-900">{view.running_branch}</span>
                  </div>
                </div>
              </div>

              {/* Remote card */}
              <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Tracked Repository</h2>
                  <button
                    onClick={handleCheckNow}
                    disabled={checking || !view.repo_url}
                    className="px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50 transition-colors"
                  >
                    {checking ? 'Checking…' : 'Check now'}
                  </button>
                </div>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600 w-36">Repository:</span>
                    <span className="text-sm text-gray-900 break-all">
                      {view.repo_url || <span className="text-gray-400">SYSTEM_REPO_URL not configured</span>}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600 w-36">Tracked branch:</span>
                    <span className="text-sm text-gray-900">{view.tracked_branch}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-600 w-36">Latest commit:</span>
                    <code className="text-sm font-mono text-gray-900">{shortCommit(view.remote_commit)}</code>
                    {view.remote_checked_at && (
                      <span className="text-xs text-gray-500">
                        checked {new Date(view.remote_checked_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  {view.remote_error && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">
                        <strong>Update check failed:</strong> {view.remote_error}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Last update run */}
              {state && state.status !== 'idle' && (
                <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">
                      {runInProgress ? 'Update in Progress' : 'Last Update'}
                    </h2>
                    {state.status === 'success' && <Badge color="green" pill>Success</Badge>}
                    {state.status === 'failed' && <Badge color="red" pill>Failed</Badge>}
                    {state.status === 'rolled_back' && <Badge color="yellow" pill>Rolled back</Badge>}
                    {runInProgress && <Badge color="blue" pill>Running</Badge>}
                  </div>
                  <div className="space-y-3">
                    {runInProgress && state.phase && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-gray-600 w-36">Phase:</span>
                        <span className="text-sm text-gray-900">
                          {PHASE_LABELS[state.phase] || state.phase}…
                        </span>
                      </div>
                    )}
                    {state.from_commit && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-gray-600 w-36">From → to:</span>
                        <code className="text-sm font-mono text-gray-900">
                          {shortCommit(state.from_commit)} → {shortCommit(state.to_commit)}
                        </code>
                      </div>
                    )}
                    {state.requested_by && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-gray-600 w-36">Requested by:</span>
                        <span className="text-sm text-gray-900">{state.requested_by_name || state.requested_by}</span>
                      </div>
                    )}
                    {state.finished_at && (
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-gray-600 w-36">Finished:</span>
                        <span className="text-sm text-gray-900">{new Date(state.finished_at).toLocaleString()}</span>
                      </div>
                    )}
                    {state.error && (
                      <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-sm text-red-700 whitespace-pre-wrap">{state.error}</p>
                      </div>
                    )}
                    {state.status === 'success' && (
                      <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-center justify-between gap-3">
                        <p className="text-sm text-green-700">
                          The system was updated. Reload to load the new frontend version.
                        </p>
                        <button
                          onClick={() => window.location.reload()}
                          className="px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors shrink-0"
                        >
                          Reload page
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
                <button
                  onClick={() => setShowUpdateConfirm(true)}
                  disabled={!!updateDisabledReason || triggering || !view.update_available}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {triggering ? 'Requesting…' : 'Update now'}
                </button>
                {updateDisabledReason ? (
                  <p className="text-sm text-gray-500 mt-2">{updateDisabledReason}</p>
                ) : !view.update_available ? (
                  <p className="text-sm text-gray-500 mt-2">The system is already up to date.</p>
                ) : (
                  <p className="text-sm text-gray-500 mt-2">
                    Updates to <code className="font-mono">{shortCommit(view.remote_commit)}</code> on{' '}
                    <code className="font-mono">{view.tracked_branch}</code>.
                  </p>
                )}
              </div>

              {/* Info */}
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
                <h2 className="text-sm font-semibold text-gray-900 mb-3">How Self-Update Works</h2>
                <ul className="text-sm text-gray-600 space-y-2">
                  <li>
                    <strong>Downtime:</strong> the update builds the new images first, then serves a static
                    maintenance page while services restart — expect a few minutes of downtime.
                  </li>
                  <li>
                    <strong>Rollback:</strong> if the system does not come back healthy, the updater
                    automatically rolls back to the previous version.
                  </li>
                  <li>
                    <strong>Database migrations</strong> run automatically on startup and are <em>not</em> reverted
                    by a rollback — migrations must stay backward-compatible for one version.
                  </li>
                  <li>
                    <strong>Configuration:</strong> the tracked repository and branch come from{' '}
                    <code className="px-1.5 py-0.5 bg-gray-200 rounded text-xs font-mono">SYSTEM_REPO_URL</code> /{' '}
                    <code className="px-1.5 py-0.5 bg-gray-200 rounded text-xs font-mono">SYSTEM_REPO_BRANCH</code> in{' '}
                    <code className="px-1.5 py-0.5 bg-gray-200 rounded text-xs font-mono">.env</code>; your .env is
                    never modified by an update.
                  </li>
                </ul>
              </div>
            </>
          )}
        </ScrollArea>

        <ConfirmDialog
          open={showUpdateConfirm}
          title="Update the System"
          message="The entire system — including this page — will go offline for several minutes while the update runs. If the new version fails its health check, the previous version is restored automatically. Start the update?"
          confirmLabel="Update now"
          variant="danger"
          onConfirm={handleTriggerUpdate}
          onCancel={() => setShowUpdateConfirm(false)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
