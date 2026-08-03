'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCoderTemplates } from '@/src/hooks/useCoderTemplates';
import { useWorkspaceActions } from '@/src/hooks/useWorkspaceActions';
import { useNotify } from '@/src/contexts/NotificationContext';
import { CoderClient } from '@/src/clients/CoderClient';
import WorkspaceTable from '@/src/components/workspaces/WorkspaceTable';
import { workspaceDeleteMessage } from '@/src/components/workspaces/deleteMessage';
import WorkspaceDetailsModal from '@/src/components/workspaces/WorkspaceDetailsModal';
import WorkspaceTypeGrid, { usableOptions } from '@/src/components/workspaces/WorkspaceTypeGrid';
import NewWorkspaceForm from '@/src/components/workspaces/NewWorkspaceForm';
import { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import EmptyState from '@/src/components/EmptyState';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import {
  openLaunchTab,
  workspaceCreatingUrl,
  workspaceLaunchUrl,
} from '@/src/utils/workspaceLaunch';
import type { CoderHealthResponse, CoderWorkspace, WorkspaceDetails } from '@/src/types/workspaces';

const coderClient = new CoderClient();

export default function WorkspacesPage() {
  const router = useRouter();
  const notify = useNotify();
  const { isWorkspaceMaintainer } = usePermissions();

  // Workspace list with silent background polling (pauses on hidden tabs).
  const { data, loading, error, reload, refresh } = useResource(
    async () => (await coderClient.listWorkspaces()).workspaces,
    [],
    { refetchInterval: 3000 },
  );
  const workspaces = data ?? [];
  const runningCount = workspaces.filter(
    (ws) => categorizeStatus(ws.latest_build_status, ws.latest_build_transition) === 'running',
  ).length;
  const busyCount = workspaces.filter(
    (ws) => categorizeStatus(ws.latest_build_status, ws.latest_build_transition) === 'pending',
  ).length;

  // The types this user may have, and what is being deployed right now. Polled
  // slower than the workspaces: a build stage lasts minutes, and the point of
  // watching it at all is that a type can appear (or start building) while the
  // page is open. A 403 here means "you may not create workspaces" — the
  // section hides rather than shouting a permission error at someone who is
  // only here to open the workspace a lecturer made for them.
  const {
    options,
    error: templatesError,
    refresh: refreshTemplates,
  } = useCoderTemplates({ refetchInterval: 10000 });

  // Coder health for the status strip (no polling — cheap indicator only).
  const { data: health } = useResource<CoderHealthResponse>(
    () => coderClient.getHealth().catch(() => ({ healthy: false, message: 'Unable to connect' })),
    [],
  );

  const actions = useWorkspaceActions(refresh);

  const [deleteTarget, setDeleteTarget] = useState<{ owner: string; name: string } | null>(null);
  const [detailsData, setDetailsData] = useState<WorkspaceDetails | null>(null);
  const [creating, setCreating] = useState<string | null>(null);
  const [customFormOpen, setCustomFormOpen] = useState(false);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await actions.remove(deleteTarget.owner, deleteTarget.name);
    setDeleteTarget(null);
  };

  // A scratch home lives and dies with its workspace; the shared home does not.
  // The dialog has to say which, because "your files are safe" is false for the
  // scratch ones lecturers hand out in bulk.
  const deleteMessage = deleteTarget
    ? workspaceDeleteMessage(
        deleteTarget.name,
        workspaces.find(
          (w) => w.name === deleteTarget.name && (w.owner_name || '') === deleteTarget.owner,
        ),
      )
    : '';

  const handleViewDetails = async (owner: string, name: string) => {
    // Opens a running workspace in a new tab; otherwise shows its details.
    const details = await actions.openOrDetails(owner, name);
    if (details) setDetailsData(details);
  };

  // Start the workspace and open it once it is ready. The launch page issues the
  // start itself, so this only has to get the user there — synchronously, since
  // a tab opened after an await would be popup-blocked.
  const handleLaunch = (owner: string, name: string) => {
    if (!openLaunchTab(owner, name)) router.push(workspaceLaunchUrl(owner, name));
  };

  const handleOpenOwn = (workspace: CoderWorkspace) => {
    if (workspace.owner_name) handleLaunch(workspace.owner_name, workspace.name);
  };

  /**
   * Create this type's workspace and open it. No name: the server derives one
   * (and forces it for self-provisioners), which is exactly the workspace the
   * card claims to be about.
   */
  const handleCreate = async (templateName: string) => {
    // Still inside the click — see workspaceCreatingUrl.
    const tab = window.open(workspaceCreatingUrl, '_blank');
    setCreating(templateName);
    try {
      const result = await coderClient.provisionWorkspace({ body: { template: templateName } });
      const workspaceName = result.workspace?.name;
      if (!workspaceName) throw new Error('The workspace was not created.');

      const launchUrl = workspaceLaunchUrl(result.user.username, workspaceName);
      if (tab) {
        tab.location.replace(launchUrl);
        notify('Workspace created — opening in a new tab', 'success');
      } else {
        router.push(launchUrl);
      }
      refresh();
    } catch (err) {
      tab?.close();
      notify(err instanceof Error ? err.message : 'Failed to create workspace', 'error');
    } finally {
      setCreating(null);
    }
  };

  const creatable = usableOptions(options);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Workspaces' }]}
          title="Workspaces"
          subtitle="Your development workspaces — all of them share your home directory"
          actions={
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  reload();
                  refreshTemplates();
                }}
                disabled={loading}
              >
                Refresh
              </Button>
              {/* Maintainers only: everyone else gets exactly one workspace per
                  type, so a name field would be a field with one legal value. */}
              {isWorkspaceMaintainer && creatable.length > 0 && (
                <Button variant="secondary" onClick={() => setCustomFormOpen((open) => !open)}>
                  New workspace…
                </Button>
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
          {busyCount > 0 && (
            <>
              <span className="text-gray-300">·</span>
              <span className="text-blue-700">
                {busyCount} {busyCount === 1 ? 'workspace is' : 'workspaces are'} still working
              </span>
            </>
          )}
        </div>

        {!templatesError && (
          <div className="shrink-0 space-y-3">
            <h2 className="text-sm font-semibold text-gray-900">Create a workspace</h2>
            {customFormOpen && (
              <NewWorkspaceForm
                options={creatable}
                onClose={() => setCustomFormOpen(false)}
                onCreated={refresh}
              />
            )}
            <WorkspaceTypeGrid
              options={options}
              workspaces={workspaces}
              busyTemplate={creating}
              onCreate={handleCreate}
              onOpen={handleOpenOwn}
              isMaintainer={isWorkspaceMaintainer}
            />
          </div>
        )}

        {loading ? (
          <ListLoading>Loading workspaces…</ListLoading>
        ) : !error && workspaces.length === 0 ? (
          <EmptyState
            icon={
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            }
            title="No workspaces"
            description={
              creatable.length > 0
                ? 'Pick a workspace type above to create your first one.'
                : 'No workspaces have been provisioned for you yet. Please contact your administrator.'
            }
          />
        ) : !error ? (
          <>
            <h2 className="shrink-0 text-sm font-semibold text-gray-900">Your workspaces</h2>
            <ScrollPanel>
              <WorkspaceTable
                workspaces={workspaces}
                onStart={actions.start}
                onStop={actions.stop}
                // Deleting a workspace needs workspace:delete, which no
                // self-service role carries — showing it to everyone else only
                // led to a confirmation dialog and then a 403.
                onDelete={
                  isWorkspaceMaintainer
                    ? (owner, name) => setDeleteTarget({ owner, name })
                    : undefined
                }
                onViewDetails={handleViewDetails}
                onLaunch={handleLaunch}
              />
            </ScrollPanel>
          </>
        ) : null}

        {/* Delete Confirmation */}
        <ConfirmDialog
          open={deleteTarget !== null}
          title="Delete Workspace"
          message={deleteMessage}
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
