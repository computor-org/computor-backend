'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { CoderClient } from '@/src/clients/CoderClient';
import { WorkspaceRolesClient } from '@/src/clients/WorkspaceRolesClient';
import Notification from '@/src/components/workspaces/Notification';
import ConfirmDialog from '@/src/components/workspaces/ConfirmDialog';
import type { WorkspaceRoleUser, WorkspaceTemplate } from '@/src/types/workspaces';

const coderClient = new CoderClient();
const rolesClient = new WorkspaceRolesClient();
const WORKSPACE_ROLES = ['_workspace_user', '_workspace_maintainer'] as const;

export default function WorkspaceAdminPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [users, setUsers] = useState<WorkspaceRoleUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Assign role form
  const [assignEmail, setAssignEmail] = useState('');
  const [assignRole, setAssignRole] = useState<string>('_workspace_user');
  const [assignProvision, setAssignProvision] = useState(false);
  const [assigning, setAssigning] = useState(false);

  // Workspace status per user
  const [workspaceStatus, setWorkspaceStatus] = useState<Record<string, boolean | 'loading' | null>>({});

  // Role removal confirmation
  const [removeTarget, setRemoveTarget] = useState<{ userId: string; roleId: string; email: string } | null>(null);

  const fetchUsers = async () => {
    try {
      const data = await rolesClient.listUsers();
      setUsers(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    fetchUsers();
  }, [authLoading, isAuthenticated]);

  // Check workspace status for each user with a workspace role
  useEffect(() => {
    if (users.length === 0) return;

    users.forEach((u) => {
      if (!u.email || !u.roles.some((r) => r.startsWith('_workspace'))) return;
      if (workspaceStatus[u.user_id] !== undefined) return;

      setWorkspaceStatus((prev) => ({ ...prev, [u.user_id]: 'loading' }));

      coderClient.checkWorkspaceExists({ email: u.email })
        .then((exists) => {
          setWorkspaceStatus((prev) => ({ ...prev, [u.user_id]: exists }));
        })
        .catch(() => {
          setWorkspaceStatus((prev) => ({ ...prev, [u.user_id]: null }));
        });
    });
  }, [users, workspaceStatus]);

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignEmail || !assignRole) return;

    setAssigning(true);
    try {
      await rolesClient.assignRole({
        body: { email: assignEmail, role_id: assignRole },
      });

      // Optionally provision workspace
      if (assignProvision) {
        try {
          await coderClient.provisionWorkspace({
            body: { email: assignEmail, template: 'python-workspace' as WorkspaceTemplate },
          });
          setNotification({ message: 'Role assigned and workspace provisioned', type: 'success' });
        } catch {
          setNotification({ message: 'Role assigned but workspace provisioning failed', type: 'error' });
        }
      } else {
        setNotification({ message: 'Role assigned successfully', type: 'success' });
      }

      setAssignEmail('');
      setAssignProvision(false);
      // Reset workspace statuses so they're re-checked
      setWorkspaceStatus({});
      await fetchUsers();
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Failed to assign role', type: 'error' });
    } finally {
      setAssigning(false);
    }
  };

  const handleRemoveRole = async () => {
    if (!removeTarget) return;
    try {
      await rolesClient.removeRole({ userId: removeTarget.userId, roleId: removeTarget.roleId });
      setNotification({ message: 'Role removed', type: 'success' });
      setRemoveTarget(null);
      await fetchUsers();
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Failed to remove role', type: 'error' });
      setRemoveTarget(null);
    }
  };

  const handleInlineAddRole = async (userId: string, roleId: string) => {
    const u = users.find((x) => x.user_id === userId);
    if (!u?.email) return;
    try {
      await rolesClient.assignRole({ body: { email: u.email, role_id: roleId } });
      setNotification({ message: 'Role added', type: 'success' });
      await fetchUsers();
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Failed to add role', type: 'error' });
    }
  };

  const handleProvisionForUser = async (email: string) => {
    try {
      await coderClient.provisionWorkspace({
        body: { email, template: 'python-workspace' as WorkspaceTemplate },
      });
      setNotification({ message: 'Workspace provisioned', type: 'success' });
      setWorkspaceStatus({});
    } catch (err) {
      setNotification({ message: err instanceof Error ? err.message : 'Provisioning failed', type: 'error' });
    }
  };

  // Filter users
  const filteredUsers = users.filter((u) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (u.email?.toLowerCase().includes(q)) ||
      (u.username?.toLowerCase().includes(q)) ||
      (u.given_name?.toLowerCase().includes(q)) ||
      (u.family_name?.toLowerCase().includes(q))
    );
  });

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {notification && (
          <Notification message={notification.message} type={notification.type} onClose={() => setNotification(null)} />
        )}

        {/* Header */}
        <div>
          <Link href="/workspaces" className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-2">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Workspaces
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">Workspace Administration</h1>
          <p className="mt-2 text-gray-600">Manage workspace roles and user access</p>
        </div>

        {/* Assign Role Form */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Assign Role</h2>
          <form onSubmit={handleAssignRole} className="flex flex-wrap items-end gap-4">
            <div className="flex-1 min-w-[200px]">
              <label htmlFor="assign-email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                id="assign-email"
                type="email"
                value={assignEmail}
                onChange={(e) => setAssignEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                placeholder="user@example.com"
                required
              />
            </div>
            <div className="w-48">
              <label htmlFor="assign-role" className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select
                id="assign-role"
                value={assignRole}
                onChange={(e) => setAssignRole(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              >
                {WORKSPACE_ROLES.map((role) => (
                  <option key={role} value={role}>{role}</option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={assignProvision}
                onChange={(e) => setAssignProvision(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              Provision workspace
            </label>
            <button
              type="submit"
              disabled={assigning}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {assigning ? 'Assigning...' : 'Assign'}
            </button>
          </form>
        </div>

        {/* Search */}
        <div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            placeholder="Search by name, email, or username..."
          />
        </div>

        {/* Loading */}
        {loading && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-4" />
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-gray-200 rounded" />
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Users Table */}
        {!loading && !error && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Username</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Roles</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Workspace</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredUsers.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        {searchQuery ? 'No users match your search' : 'No users with workspace roles'}
                      </td>
                    </tr>
                  ) : (
                    filteredUsers.map((u) => {
                      const missingRoles = WORKSPACE_ROLES.filter((r) => !u.roles.includes(r));
                      const wsStatus = workspaceStatus[u.user_id];
                      const hasWsRole = u.roles.some((r) => r.startsWith('_workspace'));

                      return (
                        <tr key={u.user_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-900">
                            {u.given_name || u.family_name
                              ? `${u.given_name || ''} ${u.family_name || ''}`.trim()
                              : '-'}
                          </td>
                          <td className="px-4 py-3 text-gray-600">{u.email || '-'}</td>
                          <td className="px-4 py-3 text-gray-600 font-mono text-xs">{u.username || '-'}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap items-center gap-1.5">
                              {u.roles.map((role) => (
                                <span
                                  key={role}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700"
                                >
                                  {role}
                                  <button
                                    onClick={() => setRemoveTarget({ userId: u.user_id, roleId: role, email: u.email || '' })}
                                    className="text-indigo-400 hover:text-red-500 ml-0.5"
                                    title="Remove role"
                                  >
                                    &times;
                                  </button>
                                </span>
                              ))}
                              {missingRoles.length > 0 && (
                                <select
                                  className="text-xs border border-gray-200 rounded px-1 py-0.5 text-gray-500"
                                  value=""
                                  onChange={(e) => {
                                    if (e.target.value) handleInlineAddRole(u.user_id, e.target.value);
                                  }}
                                >
                                  <option value="">+ Add</option>
                                  {missingRoles.map((r) => (
                                    <option key={r} value={r}>{r}</option>
                                  ))}
                                </select>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            {!hasWsRole ? (
                              <span className="text-xs text-gray-400">N/A</span>
                            ) : wsStatus === 'loading' ? (
                              <span className="text-xs text-gray-400">Checking...</span>
                            ) : wsStatus === true ? (
                              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Yes</span>
                            ) : wsStatus === false ? (
                              <button
                                onClick={() => u.email && handleProvisionForUser(u.email)}
                                className="px-2 py-0.5 rounded text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100"
                              >
                                Provision
                              </button>
                            ) : (
                              <span className="text-xs text-gray-400">Unknown</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <Link
                              href={`/workspaces/admin/${u.user_id}`}
                              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                            >
                              Manage
                            </Link>
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

        {/* Remove role confirmation */}
        <ConfirmDialog
          open={removeTarget !== null}
          title="Remove Role"
          message={`Remove role "${removeTarget?.roleId}" from ${removeTarget?.email || 'this user'}?`}
          confirmLabel="Remove"
          variant="danger"
          onConfirm={handleRemoveRole}
          onCancel={() => setRemoveTarget(null)}
        />
      </div>
    </AuthenticatedLayout>
  );
}
