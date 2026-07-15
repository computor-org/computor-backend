'use client';

import { useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useWorkspaceActions } from '@/src/hooks/useWorkspaceActions';
import { CoderClient } from '@/src/clients/CoderClient';
import WorkspaceTable from '@/src/components/workspaces/WorkspaceTable';
import WorkspaceDetailsModal from '@/src/components/workspaces/WorkspaceDetailsModal';
import { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import type { CoderHealthResponse, WorkspaceDetails } from '@/src/types/workspaces';

const coderClient = new CoderClient();

export default function WorkspacesPage() {
  const { canProvisionWorkspace } = usePermissions();

  // Workspace list with silent background polling (pauses on hidden tabs).
  const { data, loading, error, reload, refresh } = useResource(
    async () => (await coderClient.listWorkspaces()).workspaces,
    [],
    { refetchInterval: 3000 },
  );
  const workspaces = data ?? [];
  const runningCount = workspaces.filter(
    (ws) => categorizeStatus(ws.latest_build_status) === 'running',
  ).length;

  // Coder health for the status strip (no polling — cheap indicator only).
  const { data: health } = useResource<CoderHealthResponse>(
    () => coderClient.getHealth().catch(() => ({ healthy: false, message: 'Unable to connect' })),
    [],
  );

  const actions = useWorkspaceActions(refresh);

  const [deleteTarget, setDeleteTarget] = useState<{ owner: string; name: string } | null>(null);
  const [detailsData, setDetailsData] = useState<WorkspaceDetails | null>(null);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await actions.remove(deleteTarget.owner, deleteTarget.name);
    setDeleteTarget(null);
  };

  const handleViewDetails = async (owner: string, name: string) => {
    // Opens a running workspace in a new tab; otherwise shows its details.
    const details = await actions.openOrDetails(owner, name);
    if (details) setDetailsData(details);
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Workspaces' }]}
          title="Workspaces"
          subtitle="Your development workspaces — all of them share your home directory"
          actions={
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={() => reload()} disabled={loading}>
                Refresh
              </Button>
              {canProvisionWorkspace && (
                <ButtonLink href="/workspaces/create">New Workspace</ButtonLink>
              )}
            </div>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {/* Compact status strip */}
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
                ? 'Coder healthy'
                : 'Coder unreachable'}
          </span>
          <span className="text-gray-300">·</span>
          <span>{loading ? '—' : `${runningCount} running / ${workspaces.length} total`}</span>
        </div>

        {loading ? (
          <ListLoading>Loading workspaces…</ListLoading>
        ) : !error && workspaces.length === 0 ? (
          <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">No workspaces</h3>
            {canProvisionWorkspace ? (
              <>
                <p className="mt-2 text-sm text-gray-500">Get started by creating your first workspace.</p>
                <ButtonLink href="/workspaces/create" className="mt-4">
                  New Workspace
                </ButtonLink>
              </>
            ) : (
              <p className="mt-2 text-sm text-gray-500">
                No workspaces have been provisioned for you yet. Please contact your administrator.
              </p>
            )}
          </div>
        ) : !error ? (
          <ScrollPanel>
            <WorkspaceTable
              workspaces={workspaces}
              onStart={actions.start}
              onStop={actions.stop}
              onDelete={(owner, name) => setDeleteTarget({ owner, name })}
              onViewDetails={handleViewDetails}
            />
          </ScrollPanel>
        ) : null}

        {/* Delete Confirmation */}
        <ConfirmDialog
          open={deleteTarget !== null}
          title="Delete Workspace"
          message={`Are you sure you want to delete workspace "${deleteTarget?.name}"? Your home directory is shared across workspaces and will NOT be deleted.`}
          confirmLabel="Delete"
          variant="danger"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />

        {/* Details Modal */}
        {detailsData && (
          <WorkspaceDetailsModal details={detailsData} onClose={() => setDetailsData(null)} />
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
