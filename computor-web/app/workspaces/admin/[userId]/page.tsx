'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useResource } from '@/src/hooks/useResource';
import { CoderClient } from '@/src/clients/CoderClient';
import { WorkspaceRolesClient } from '@/src/clients/WorkspaceRolesClient';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import { useNotify } from '@/src/contexts/NotificationContext';
import type { CoderWorkspace, WorkspaceTemplate } from '@/src/types/workspaces';

const coderClient = new CoderClient();
const rolesClient = new WorkspaceRolesClient();

export default function UserDetailPage() {
  const { userId } = useParams<{ userId: string }>();
  const notify = useNotify();

  const [deleteTarget, setDeleteTarget] = useState<{ owner: string; name: string } | null>(null);
  const [provisioning, setProvisioning] = useState(false);

  const {
    data,
    loading,
    error,
    reload: fetchUserAndWorkspaces,
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

  const handleProvision = async () => {
    if (!user?.email) return;
    setProvisioning(true);
    try {
      await coderClient.provisionWorkspace({
        body: { email: user.email, template: 'python-workspace' as WorkspaceTemplate },
      });
      notify('Workspace provisioned', 'success');
      await fetchUserAndWorkspaces();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Provisioning failed', 'error');
    } finally {
      setProvisioning(false);
    }
  };

  const handleStart = async (owner: string, name: string) => {
    try {
      await coderClient.startWorkspace({ username: owner, workspaceName: name });
      notify('Workspace starting...', 'success');
      setTimeout(fetchUserAndWorkspaces, 2000);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to start', 'error');
    }
  };

  const handleStop = async (owner: string, name: string) => {
    try {
      await coderClient.stopWorkspace({ username: owner, workspaceName: name });
      notify('Workspace stopping...', 'success');
      setTimeout(fetchUserAndWorkspaces, 2000);
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
      await fetchUserAndWorkspaces();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to delete', 'error');
      setDeleteTarget(null);
    }
  };

  const handleOpenWorkspace = async (owner: string, name: string) => {
    try {
      const data = await coderClient.getWorkspaceDetails({ username: owner, workspaceName: name });
      if (data.code_server_url || data.access_url) {
        window.open((data.code_server_url || data.access_url)!, '_blank');
      } else {
        notify('No access URL available', 'error');
      }
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to open', 'error');
    }
  };

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6 max-w-4xl">
        {/* Header */}
        <PageHeader
          breadcrumbs={[
            { label: 'Workspaces', href: '/workspaces' },
            { label: 'Administration', href: '/workspaces/admin' },
            { label: 'User Detail' },
          ]}
          title="User Detail"
        />

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

        {/* Error */}
        <ErrorBanner>{error}</ErrorBanner>

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
                    <span key={role} className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 mr-1.5">
                      {role}
                    </span>
                  ))}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Workspace Management */}
        {user && (
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Workspaces</h2>
              <div className="flex gap-2">
                <button
                  onClick={fetchUserAndWorkspaces}
                  className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Refresh
                </button>
                <button
                  onClick={handleProvision}
                  disabled={provisioning || !user.email}
                  className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {provisioning ? 'Provisioning...' : 'Provision New Workspace'}
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Template</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {workspaces.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                        No workspaces found for this user
                      </td>
                    </tr>
                  ) : (
                    workspaces.map((ws) => {
                      const status = ws.latest_build_status;
                      const isRunning = status === 'running' || status === 'succeeded';
                      const isStopped = status === 'stopped' || status === 'canceled';

                      return (
                        <tr key={ws.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-900 font-medium">{ws.name}</td>
                          <td className="px-4 py-3 text-gray-600">{ws.template_name || '-'}</td>
                          <td className="px-4 py-3"><WorkspaceStatusBadge status={status} size="sm" /></td>
                          <td className="px-4 py-3 text-gray-600 text-xs">
                            {ws.created_at ? new Date(ws.created_at).toLocaleDateString() : '-'}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {isRunning && (
                                <>
                                  <button
                                    onClick={() => handleOpenWorkspace(ws.owner_name || '', ws.name)}
                                    className="px-2 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100"
                                  >
                                    Open
                                  </button>
                                  <button
                                    onClick={() => handleStop(ws.owner_name || '', ws.name)}
                                    className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
                                  >
                                    Stop
                                  </button>
                                </>
                              )}
                              {isStopped && (
                                <button
                                  onClick={() => handleStart(ws.owner_name || '', ws.name)}
                                  className="px-2 py-1 text-xs font-medium text-green-600 bg-green-50 rounded hover:bg-green-100"
                                >
                                  Start
                                </button>
                              )}
                              <button
                                onClick={() => setDeleteTarget({ owner: ws.owner_name || '', name: ws.name })}
                                className="px-2 py-1 text-xs font-medium text-red-600 bg-red-50 rounded hover:bg-red-100"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Delete confirmation */}
        <ConfirmDialog
          open={deleteTarget !== null}
          title="Delete Workspace"
          message={`Are you sure you want to delete workspace "${deleteTarget?.name}"? This action cannot be undone.`}
          confirmLabel="Delete"
          variant="danger"
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      </div>
    </AuthenticatedLayout>
  );
}
