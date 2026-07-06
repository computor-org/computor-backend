'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { CoderClient } from '@/src/clients/CoderClient';
import WorkspaceTable from '@/src/components/workspaces/WorkspaceTable';
import { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Modal from '@/src/components/Modal';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import { useNotify } from '@/src/contexts/NotificationContext';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import type { CoderHealthResponse, WorkspaceDetails } from '@/src/types/workspaces';

const coderClient = new CoderClient();

export default function WorkspacesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const notify = useNotify();
  const [health, setHealth] = useState<CoderHealthResponse | null>(null);
  const [templateCount, setTemplateCount] = useState<number>(0);

  // Main load: workspaces (health and template count are non-blocking side loads)
  const { data, loading, error, reload, setData } = useResource(async () => {
    coderClient.getHealth()
      .then((d) => setHealth(d))
      .catch(() => setHealth({ healthy: false, message: 'Unable to connect' }));

    coderClient.listTemplates()
      .then((d) => setTemplateCount(d.count))
      .catch(() => {});

    return (await coderClient.listWorkspaces()).workspaces;
  }, []);
  const workspaces = data ?? [];
  const runningCount = workspaces.filter(
    (ws) => categorizeStatus(ws.latest_build_status) === 'running',
  ).length;

  // Delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState<{ owner: string; name: string } | null>(null);

  // Details modal state
  const [detailsData, setDetailsData] = useState<WorkspaceDetails | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  // Polling ref
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Targeted workspace refresh for polling/actions: updates data without
  // toggling the loading state; transient failures are ignored. If the
  // initial load had failed, a successful poll triggers a full reload so
  // the error state recovers (matching the previous behavior).
  const fetchWorkspaces = useCallback(async () => {
    try {
      const fresh = (await coderClient.listWorkspaces()).workspaces;
      if (error) {
        reload();
      } else {
        setData(fresh);
      }
    } catch {
      // ignore transient polling failures
    }
  }, [error, reload, setData]);

  // Polling: every 3 seconds with visibility API pause
  useEffect(() => {
    if (authLoading || !isAuthenticated || loading) return;

    const startPolling = () => {
      if (pollingRef.current) return;
      pollingRef.current = setInterval(fetchWorkspaces, 3000);
    };

    const stopPolling = () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };

    const handleVisibility = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        fetchWorkspaces();
        startPolling();
      }
    };

    startPolling();
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      stopPolling();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [authLoading, isAuthenticated, loading, fetchWorkspaces]);

  const handleStart = async (owner: string, name: string) => {
    try {
      await coderClient.startWorkspace({ username: owner, workspaceName: name });
      notify('Workspace starting...', 'success');
      setTimeout(fetchWorkspaces, 2000);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to start', 'error');
    }
  };

  const handleStop = async (owner: string, name: string) => {
    try {
      await coderClient.stopWorkspace({ username: owner, workspaceName: name });
      notify('Workspace stopping...', 'success');
      setTimeout(fetchWorkspaces, 2000);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to stop', 'error');
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await coderClient.deleteWorkspace({ username: deleteTarget.owner, workspaceName: deleteTarget.name });
      notify('Workspace deleted', 'success');
      setDeleteTarget(null);
      fetchWorkspaces();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to delete', 'error');
      setDeleteTarget(null);
    }
  };

  const handleViewDetails = async (owner: string, name: string) => {
    try {
      const data = await coderClient.getWorkspaceDetails({ username: owner, workspaceName: name });

      // If running and has a URL, open it
      if (data.status === 'running' && (data.code_server_url || data.access_url)) {
        window.open(data.code_server_url || data.access_url || '', '_blank');
        return;
      }

      // Otherwise show details modal
      setDetailsData(data);
      setDetailsOpen(true);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to fetch details', 'error');
    }
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Workspaces' }]}
          title="Workspaces"
          subtitle="Manage your development workspaces"
          actions={
            <div className="flex items-center gap-2">
              <button
                onClick={() => reload()}
                disabled={loading}
                className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Refresh
              </button>
              <Link
                href="/workspaces/provision"
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                New Workspace
              </Link>
            </div>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {/* Compact status strip — replaces the old oversized stat cards. */}
        <div className="shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600">
          <span className="inline-flex items-center gap-1.5">
            <span
              className={`h-2 w-2 rounded-full ${
                health === null ? 'bg-gray-300' : health.healthy ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            {health === null
              ? 'Checking Coder…'
              : health.healthy
                ? `Coder healthy${health.version ? ` · v${health.version}` : ''}`
                : 'Coder unreachable'}
          </span>
          <span className="text-gray-300">·</span>
          <span>{loading ? '—' : `${runningCount} running / ${workspaces.length} total`}</span>
          <span className="text-gray-300">·</span>
          <Link href="/workspaces/templates" className="text-blue-600 hover:underline">
            {templateCount} {templateCount === 1 ? 'template' : 'templates'}
          </Link>
        </div>

        {loading ? (
          <ListLoading>Loading workspaces…</ListLoading>
        ) : !error && workspaces.length === 0 ? (
          <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">No workspaces</h3>
            <p className="mt-2 text-sm text-gray-500">Get started by provisioning your first workspace.</p>
            <Link
              href="/workspaces/provision"
              className="mt-4 inline-block px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              New Workspace
            </Link>
          </div>
        ) : !error ? (
          <ScrollPanel>
            <WorkspaceTable
              workspaces={workspaces}
              onStart={handleStart}
              onStop={handleStop}
              onDelete={(owner, name) => setDeleteTarget({ owner, name })}
              onViewDetails={handleViewDetails}
            />
          </ScrollPanel>
        ) : null}

        {/* Delete Confirmation */}
        <ConfirmDialog
          open={deleteTarget !== null}
          title="Delete Workspace"
          message={`Are you sure you want to delete workspace "${deleteTarget?.name}"? This action cannot be undone.`}
          confirmLabel="Delete"
          variant="danger"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />

        {/* Details Modal */}
        {detailsOpen && detailsData && (
          <Modal title="Workspace Details" onClose={() => setDetailsOpen(false)} maxWidth="max-w-lg">
            <div className="p-6 pt-4 max-h-[80vh] overflow-y-auto">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-gray-100">
                    <tr><td className="py-2 font-medium text-gray-600 pr-4">Name</td><td className="py-2 text-gray-900">{detailsData.workspace.name}</td></tr>
                    <tr><td className="py-2 font-medium text-gray-600 pr-4">Status</td><td className="py-2"><WorkspaceStatusBadge status={detailsData.status} size="sm" /></td></tr>
                    <tr><td className="py-2 font-medium text-gray-600 pr-4">Template</td><td className="py-2 text-gray-900">{detailsData.workspace.template_name}</td></tr>
                    <tr><td className="py-2 font-medium text-gray-600 pr-4">Owner</td><td className="py-2 text-gray-900">{detailsData.workspace.owner_name}</td></tr>
                    <tr><td className="py-2 font-medium text-gray-600 pr-4">ID</td><td className="py-2 text-gray-500 font-mono text-xs">{detailsData.workspace.id}</td></tr>
                    {detailsData.access_url && (
                      <tr><td className="py-2 font-medium text-gray-600 pr-4">Access URL</td><td className="py-2"><a href={detailsData.access_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs break-all">{detailsData.access_url}</a></td></tr>
                    )}
                    {detailsData.code_server_url && (
                      <tr><td className="py-2 font-medium text-gray-600 pr-4">Code Server</td><td className="py-2"><a href={detailsData.code_server_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs break-all">{detailsData.code_server_url}</a></td></tr>
                    )}
                    {detailsData.workspace.created_at && (
                      <tr><td className="py-2 font-medium text-gray-600 pr-4">Created</td><td className="py-2 text-gray-900">{new Date(detailsData.workspace.created_at).toLocaleString()}</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </Modal>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
