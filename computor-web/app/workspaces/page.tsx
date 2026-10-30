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
import WorkspaceTypeGrid, { ownWorkspace, usableOptions } from '@/src/components/workspaces/WorkspaceTypeGrid';
import NewWorkspaceForm from '@/src/components/workspaces/NewWorkspaceForm';
import { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import EmptyState from '@/src/components/EmptyState';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import { ApiError } from '@/src/api/client';
import LearningOptions from '@/src/components/courses/LearningOptions';
import {
  openLaunchTab,
  workspaceCreatingUrl,
  workspaceLaunchUrl,
} from '@/src/utils/workspaceLaunch';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import type { CoderHealthResponse, CoderWorkspace, WorkspaceDetails } from '@/src/types/workspaces';

const coderClient = new CoderClient();

const COPY = {
  de: {
    title: 'Arbeitsumgebungen',
    subtitle: 'Deine Entwicklungsumgebungen, alle teilen sich dein Home-Verzeichnis',
    refresh: 'Aktualisieren',
    newWorkspace: 'Neue Arbeitsumgebung …',
    checking: 'Arbeitsumgebungen werden geprüft …',
    healthy: 'Arbeitsumgebungen verfügbar',
    unreachable: 'Arbeitsumgebungen derzeit nicht erreichbar',
    runningOfTotal: (running: number, total: number) => `${running} aktiv / ${total} gesamt`,
    stillWorking: (n: number) =>
      n === 1 ? '1 Arbeitsumgebung ist noch in Arbeit' : `${n} Arbeitsumgebungen sind noch in Arbeit`,
    createHeading: 'Arbeitsumgebung erstellen',
    openHeading: 'Arbeitsumgebung öffnen',
    openOrCreateHeading: 'Arbeitsumgebung öffnen oder erstellen',
    loading: 'Arbeitsumgebungen werden geladen …',
    emptyTitle: 'Keine Arbeitsumgebungen',
    emptyCreate: 'Wähle oben eine Art von Arbeitsumgebung aus, um deine erste zu erstellen.',
    emptyNone: 'Für dich wurde noch keine Arbeitsumgebung bereitgestellt. Wende dich an die Administration.',
    noCourseTitle: 'Noch keine Arbeitsumgebung',
    noCourse: 'Tritt zuerst einem Kurs bei, der Arbeitsumgebungen anbietet. Danach kannst du sie hier starten.',
    joinCourse: 'Kurs beitreten',
    yours: 'Deine Arbeitsumgebungen',
    deleteTitle: 'Arbeitsumgebung löschen',
    delete: 'Löschen',
    notCreated: 'Die Arbeitsumgebung wurde nicht erstellt.',
    createdOpening: 'Arbeitsumgebung erstellt, sie öffnet sich in einem neuen Tab',
    createFailed: 'Die Arbeitsumgebung konnte nicht erstellt werden',
  },
  en: {
    title: 'Workspaces',
    subtitle: 'Your development workspaces — all of them share your home directory',
    refresh: 'Refresh',
    newWorkspace: 'New workspace…',
    checking: 'Checking workspaces…',
    healthy: 'Workspaces available',
    unreachable: 'Workspaces unavailable right now',
    runningOfTotal: (running: number, total: number) => `${running} running / ${total} total`,
    stillWorking: (n: number) =>
      n === 1 ? '1 workspace is still working' : `${n} workspaces are still working`,
    createHeading: 'Create a workspace',
    openHeading: 'Open a workspace',
    openOrCreateHeading: 'Open or create a workspace',
    loading: 'Loading workspaces…',
    emptyTitle: 'No workspaces',
    emptyCreate: 'Pick a workspace type above to create your first one.',
    emptyNone: 'No workspaces have been provisioned for you yet. Please contact your administrator.',
    noCourseTitle: 'No workspace yet',
    noCourse: 'First join a course that offers workspaces. Then you can start one here.',
    joinCourse: 'Join a course',
    yours: 'Your workspaces',
    deleteTitle: 'Delete Workspace',
    delete: 'Delete',
    notCreated: 'The workspace was not created.',
    createdOpening: 'Workspace created — opening in a new tab',
    createFailed: 'Failed to create workspace',
  },
};

export default function WorkspacesPage() {
  const router = useRouter();
  const language = useUiLanguage();
  const t = COPY[language];
  const notify = useNotify();
  const [creationFailed, setCreationFailed] = useState(false);
  const { isWorkspaceMaintainer } = usePermissions();

  // Workspace list with silent background polling (pauses on hidden tabs).
  const { data, loading, error, reload, refresh } = useResource(
    async () => {
      try {
        return { workspaces: (await coderClient.listWorkspaces()).workspaces, noCourse: false };
      } catch (e) {
        // Without a workspace role, the list is refused until the user is in a
        // course that offers workspaces: something they fix themselves.
        if (e instanceof ApiError && e.status === 403 && e.errorCode === 'AUTHZ_001') {
          return { workspaces: [], noCourse: true };
        }
        throw e;
      }
    },
    [],
    { refetchInterval: 3000 },
  );
  const workspaces = data?.workspaces ?? [];
  const noCourse = data?.noCourse ?? false;
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
  const ownedTypes = options.filter((option) => ownWorkspace(option, workspaces)).length;

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
        'self',
        language,
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
    setCreationFailed(false);
    // Still inside the click — see workspaceCreatingUrl.
    const tab = window.open(workspaceCreatingUrl, '_blank');
    setCreating(templateName);
    try {
      const result = await coderClient.provisionWorkspace({ body: { template: templateName } });
      const workspaceName = result.workspace?.name;
      if (!workspaceName) throw new Error(t.notCreated);

      const launchUrl = workspaceLaunchUrl(result.user.username, workspaceName);
      if (tab) {
        tab.location.replace(launchUrl);
        notify(t.createdOpening, 'success');
      } else {
        router.push(launchUrl);
      }
      refresh();
    } catch (err) {
      setCreationFailed(true);
      tab?.close();
      notify(err instanceof Error ? err.message : t.createFailed, 'error');
    } finally {
      setCreating(null);
    }
  };

  const creatable = usableOptions(options);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.title }]}
          title={t.title}
          subtitle={t.subtitle}
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
                {t.refresh}
              </Button>
              {/* Maintainers only: everyone else gets exactly one workspace per
                  type, so a name field would be a field with one legal value. */}
              {isWorkspaceMaintainer && creatable.length > 0 && (
                <Button variant="secondary" onClick={() => setCustomFormOpen((open) => !open)}>
                  {t.newWorkspace}
                </Button>
              )}
            </div>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>
        {creationFailed && <LearningOptions capacity language={language} />}

        {/* Compact status strip */}
        <div className="shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
          <span className="inline-flex items-center gap-1.5">
            <span
              className={`h-2 w-2 rounded-full ${
                health === null ? 'bg-faint' : health.healthy ? 'bg-success' : 'bg-danger'
              }`}
            />
            {health === null
              ? t.checking
              : health.healthy
                ? t.healthy
                : t.unreachable}
          </span>
          <span className="text-faint">·</span>
          <span>{loading ? '—' : t.runningOfTotal(runningCount, workspaces.length)}</span>
          {busyCount > 0 && (
            <>
              <span className="text-faint">·</span>
              <span className="text-accent-text">
                {t.stillWorking(busyCount)}
              </span>
            </>
          )}
        </div>

        {!templatesError && (
          <div className="shrink-0 space-y-3">
            {/* The cards open the workspace a type already has, so "create" alone is only right while there is none. */}
            <h2 className="text-sm font-semibold text-fg">
              {ownedTypes === 0
                ? t.createHeading
                : ownedTypes === options.length
                  ? t.openHeading
                  : t.openOrCreateHeading}
            </h2>
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
          <ListLoading>{t.loading}</ListLoading>
        ) : noCourse ? (
          <EmptyState
            title={t.noCourseTitle}
            description={t.noCourse}
            action={<ButtonLink href="/courses/catalog">{t.joinCourse}</ButtonLink>}
          />
        ) : !error && workspaces.length === 0 ? (
          <EmptyState
            icon={
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            }
            title={t.emptyTitle}
            description={
              creatable.length > 0
                ? t.emptyCreate
                : t.emptyNone
            }
          />
        ) : !error ? (
          <>
            <h2 className="shrink-0 text-sm font-semibold text-fg">{t.yours}</h2>
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
          title={t.deleteTitle}
          message={deleteMessage}
          confirmLabel={t.delete}
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
