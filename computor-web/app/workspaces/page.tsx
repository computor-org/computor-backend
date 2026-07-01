'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { CoderClient } from '@/src/clients/CoderClient';
import WorkspaceCard from '@/src/components/workspaces/WorkspaceCard';
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
      <div className="p-6 space-y-6">
        {/* Header */}
        <PageHeader
          breadcrumbs={[{ label: 'Workspaces' }]}
          title="Workspaces"
          subtitle="Manage your development workspaces"
          actions={
            <Link
              href="/workspaces/provision"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              New Workspace
            </Link>
          }
        />

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Health */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Coder Server</p>
                <p className="text-lg font-semibold mt-1">
                  {health === null ? (
                    <span className="text-gray-400">Checking...</span>
                  ) : health.healthy ? (
                    <span className="text-green-600">Healthy</span>
                  ) : (
                    <span className="text-red-600">Unhealthy</span>
                  )}
                </p>
              </div>
              <div className={`p-2 rounded-lg ${health?.healthy ? 'bg-green-100' : 'bg-gray-100'}`}>
                <svg className={`h-6 w-6 ${health?.healthy ? 'text-green-600' : 'text-gray-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
                </svg>
              </div>
            </div>
            {health?.version && <p className="text-xs text-gray-500 mt-2">v{health.version}</p>}
          </div>

          {/* Workspaces count */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">My Workspaces</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{loading ? '-' : workspaces.length}</p>
              </div>
              <div className="p-2 bg-blue-100 rounded-lg">
                <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
            </div>
          </div>

          {/* Templates count */}
          <Link href="/workspaces/templates" className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Templates</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{templateCount}</p>
              </div>
              <div className="p-2 bg-purple-100 rounded-lg">
                <svg className="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                </svg>
              </div>
            </div>
          </Link>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-4" />
                <div className="h-4 bg-gray-200 rounded w-full mb-2" />
                <div className="h-4 bg-gray-200 rounded w-2/3" />
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        <ErrorBanner>{error}</ErrorBanner>

        {/* Empty State */}
        {!loading && !error && workspaces.length === 0 && (
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
        )}

        {/* Workspace Grid */}
        {!loading && !error && workspaces.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workspaces.map((ws) => (
              <WorkspaceCard
                key={ws.id}
                workspace={ws}
                onStart={handleStart}
                onStop={handleStop}
                onDelete={(owner, name) => setDeleteTarget({ owner, name })}
                onViewDetails={handleViewDetails}
              />
            ))}
          </div>
        )}

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
      </div>
    </AuthenticatedLayout>
  );
}
