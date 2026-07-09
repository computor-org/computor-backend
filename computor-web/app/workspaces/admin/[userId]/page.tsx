'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useWorkspaceActions } from '@/src/hooks/useWorkspaceActions';
import { useCoderTemplates } from '@/src/hooks/useCoderTemplates';
import { CoderClient } from '@/src/clients/CoderClient';
import { WorkspaceRolesClient } from '@/src/clients/WorkspaceRolesClient';
import WorkspaceTable from '@/src/components/workspaces/WorkspaceTable';
import WorkspaceDetailsModal from '@/src/components/workspaces/WorkspaceDetailsModal';
import ConfirmDialog from '@/src/components/ConfirmDialog';
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

  const { templates } = useCoderTemplates();

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

  const handleOpenWorkspace = async (owner: string, name: string) => {
    const details = await actions.openOrDetails(owner, name);
    if (details) setDetailsData(details);
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
          title="User Detail"
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

        <ScrollArea className="space-y-6">
        {/* Loading */}
        {loading && !data && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/3 mb-4" />
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded w-1/2" />
              <div className="h-4 bg-gray-200 rounded w-2/3" />
            </div>
          </div>
        )}

        {/* User Info Card */}
        {user && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">User Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-600">Name:</span>
                <span className="ml-2 text-gray-900">
                  {user.given_name || user.family_name
                    ? `${user.given_name || ''} ${user.family_name || ''}`.trim()
                    : '-'}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-600">Email:</span>
                <span className="ml-2 text-gray-900">{user.email || '-'}</span>
              </div>
              <div>
                <span className="font-medium text-gray-600">Username:</span>
                <span className="ml-2 text-gray-900 font-mono text-xs">{user.username || '-'}</span>
              </div>
              <div>
                <span className="font-medium text-gray-600">User ID:</span>
                <span className="ml-2 text-gray-500 font-mono text-xs">{user.user_id}</span>
              </div>
              <div className="md:col-span-2">
                <span className="font-medium text-gray-600">Roles:</span>
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

        {/* Workspace Management */}
        {user && (
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Workspaces</h2>
            </div>

            <div className="overflow-x-auto">
              {workspaces.length === 0 ? (
                <p className="px-6 py-8 text-center text-gray-500 text-sm">No workspaces found for this user</p>
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
          message={`Are you sure you want to delete workspace "${deleteTarget?.name}"? The user's shared home directory will NOT be deleted.`}
          confirmLabel="Delete"
          variant="danger"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />

        {/* Details modal */}
        {detailsData && (
          <WorkspaceDetailsModal details={detailsData} onClose={() => setDetailsData(null)} />
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
