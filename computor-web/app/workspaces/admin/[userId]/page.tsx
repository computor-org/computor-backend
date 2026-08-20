'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useWorkspaceActions } from '@/src/hooks/useWorkspaceActions';
import { useCoderTemplates } from '@/src/hooks/useCoderTemplates';
import { CoderClient } from '@/src/clients/CoderClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import { WorkspaceRolesClient } from '@/src/clients/WorkspaceRolesClient';
import WorkspaceTable from '@/src/components/workspaces/WorkspaceTable';
import { workspaceDeleteMessage } from '@/src/components/workspaces/deleteMessage';
import WorkspaceDetailsModal from '@/src/components/workspaces/WorkspaceDetailsModal';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import type { CoderWorkspace, WorkspaceDetails } from '@/src/types/workspaces';

const coderClient = new CoderClient();
const rolesClient = new WorkspaceRolesClient();

export default function UserDetailPage() {
  const { userId } = useParams<{ userId: string }>();

  const [deleteTarget, setDeleteTarget] = useState<{ owner: string; name: string } | null>(null);
  const [detailsData, setDetailsData] = useState<WorkspaceDetails | null>(null);
  const [provisioning, setProvisioning] = useState(false);
  const [template, setTemplate] = useState('');
  const [rotateOpen, setRotateOpen] = useState(false);

  const { templates } = useCoderTemplates();
  const notify = useNotify();

  const {
    data,
    loading,
    error,
    reload: fetchUserAndWorkspaces,
    refresh,
  } = useResource(async () => {
    // Fetch user info from the role users list
    const allUsers = await rolesClient.listUsers();
    const foundUser = allUsers.find((u) => u.user_id === userId);
    if (!foundUser) throw new Error('User not found');

    // Fetch workspaces for this user
    let workspaces: CoderWorkspace[] = [];
    if (foundUser.email) {
      try {
        workspaces = (await coderClient.listWorkspaces({ email: foundUser.email })).workspaces;
      } catch {
        // Non-critical: user may not have workspaces
      }
    }

    return { user: foundUser, workspaces };
  }, [userId]);
  const user = data?.user ?? null;
  const workspaces = data?.workspaces ?? [];

  const actions = useWorkspaceActions(refresh);

  const handleProvision = async () => {
    if (!user?.email) return;
    setProvisioning(true);
    // Omitted template = server default; the select allows a specific type.
    await actions.provision({ email: user.email, template: template || null });
    setProvisioning(false);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await actions.remove(deleteTarget.owner, deleteTarget.name);
    setDeleteTarget(null);
  };

  // Scratch-home workspaces (what lecturer bulk-provisioning hands out) lose
  // their home volume with the workspace — do not promise otherwise.
  const deleteMessage = deleteTarget
    ? workspaceDeleteMessage(
        deleteTarget.name,
        workspaces.find(
          (w) => w.name === deleteTarget.name && (w.owner_name || '') === deleteTarget.owner,
        ),
        'other',
      )
    : '';

  const handleOpenWorkspace = async (owner: string, name: string) => {
    const details = await actions.openOrDetails(owner, name);
    if (details) setDetailsData(details);
  };

  const handleRotate = async () => {
    const result = await coderClient.rotateUserAppCredential({ userId });
    setRotateOpen(false);
    // Stopped workspaces count as "not rebuilt" — say so rather than calling
    // them failures, since they pick the new credential up on their next start.
    const pending = result.failed > 0 ? `, ${result.failed} on next start` : '';
    notify(
      `Credential rotated to v${result.key_version} — ${result.succeeded} workspace(s) restarted${pending}`,
      'success',
    );
    await refresh();
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        {/* Header */}
        <PageHeader
          breadcrumbs={[
            { label: 'Workspaces', href: '/workspaces' },
            { label: 'Administration', href: '/workspaces/admin' },
            { label: 'User Detail' },
          ]}
          title="User detail"
          actions={
            user && (
              <div className="flex items-center gap-2">
                <Button variant="secondary" onClick={fetchUserAndWorkspaces}>
                  Refresh
                </Button>
                <select
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className={`${inputCls} w-auto`}
                  aria-label="Workspace template"
                >
                  <option value="">Default template</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.name}>
                      {t.display_name || t.name}
                    </option>
                  ))}
                </select>
                <Button
                  onClick={handleProvision}
                  disabled={!user.email}
                  loading={provisioning}
                  loadingLabel="Provisioning..."
                >
                  Provision Workspace
                </Button>
              </div>
            )
          }
        />

        {/* Error */}
        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
        {/* Loading */}
        {loading && !data && (
          <div className="bg-surface rounded-lg border border-rule p-6 animate-pulse">
            <div className="h-6 bg-sunken rounded w-1/3 mb-4" />
            <div className="space-y-2">
              <div className="h-4 bg-sunken rounded w-1/2" />
              <div className="h-4 bg-sunken rounded w-2/3" />
            </div>
          </div>
        )}

        {/* User Info Card */}
        {user && (
          <div className="bg-surface rounded-lg border border-rule p-6">
            <h2 className="text-lg font-semibold text-fg mb-4">User Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-muted">Name:</span>
                <span className="ml-2 text-fg">
                  {user.given_name || user.family_name
                    ? `${user.given_name || ''} ${user.family_name || ''}`.trim()
                    : '-'}
                </span>
              </div>
              <div>
                <span className="font-medium text-muted">Email:</span>
                <span className="ml-2 text-fg">{user.email || '-'}</span>
              </div>
              <div>
                <span className="font-medium text-muted">Username:</span>
                <span className="ml-2 text-fg font-mono text-xs">{user.username || '-'}</span>
              </div>
              <div>
                <span className="font-medium text-muted">User ID:</span>
                <span className="ml-2 text-muted font-mono text-xs">{user.user_id}</span>
              </div>
              <div className="md:col-span-2">
                <span className="font-medium text-muted">Roles:</span>
                <span className="ml-2">
                  {user.roles.map((role) => (
                    <Badge key={role} color="blue" pill className="mr-1.5">
                      {role}
                    </Badge>
                  ))}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* App credential */}
        {user && (
          <div className="bg-surface rounded-lg border border-rule p-6">
            <h2 className="text-lg font-semibold text-fg mb-2">App credential</h2>
            <p className="text-sm text-muted mb-4 max-w-3xl">
              Every workspace app of this user — terminal, desktop, notebook, editor — requires
              one shared secret, which the proxy injects on their behalf. Rotating it revokes the
              old one. Their running workspaces restart immediately under the new secret; stopped
              ones adopt it when they next start. Do this if the credential may have leaked.
            </p>
            <Button
              variant="secondary"
              className="text-danger-text border-danger-line hover:bg-danger-wash"
              onClick={() => setRotateOpen(true)}
            >
              Rotate app credential
            </Button>
          </div>
        )}

        {/* Workspace Management */}
        {user && (
          <div className="bg-surface rounded-lg border border-rule">
            <div className="p-6 border-b border-rule">
              <h2 className="text-lg font-semibold text-fg">Workspaces</h2>
            </div>

            <div className="overflow-x-auto">
              {workspaces.length === 0 ? (
                <p className="px-6 py-8 text-center text-muted text-sm">No workspaces found for this user</p>
              ) : (
                <WorkspaceTable
                  workspaces={workspaces}
                  onStart={actions.start}
                  onStop={actions.stop}
                  onDelete={(owner, name) => setDeleteTarget({ owner, name })}
                  onViewDetails={handleOpenWorkspace}
                />
              )}
            </div>
          </div>
        )}
        </ScrollArea>

        {/* Delete confirmation */}
        <ConfirmDialog
          open={deleteTarget !== null}
          title="Delete Workspace"
          message={deleteMessage}
          confirmLabel="Delete"
          variant="danger"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />

        {/* Rotate confirmation — type-to-confirm, since running workspaces restart */}
        {rotateOpen && user && (
          <ConfirmDeleteDialog
            title="Rotate app credential"
            message={
              `This revokes the credential ${user.email || user.user_id} uses for every workspace app. ` +
              'Their running workspaces restart immediately under the new one, so unsaved terminal ' +
              'state is lost and open editor sessions reconnect. Stopped workspaces adopt it on their ' +
              'next start.'
            }
            confirmWord={user.email || user.user_id}
            onConfirm={handleRotate}
            onClose={() => setRotateOpen(false)}
          />
        )}

        {/* Details modal */}
        {detailsData && (
          <WorkspaceDetailsModal details={detailsData} onClose={() => setDetailsData(null)} />
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
