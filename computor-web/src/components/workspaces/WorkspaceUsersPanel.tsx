'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ScrollPanel } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { CoderClient } from '@/src/clients/CoderClient';
import { WorkspaceRolesClient } from '@/src/clients/WorkspaceRolesClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';

const coderClient = new CoderClient();
const rolesClient = new WorkspaceRolesClient();
const WORKSPACE_ROLES = ['_workspace_user', '_workspace_maintainer'] as const;

/** "Users & roles" admin tab: workspace role assignment + per-user overview. */
export default function WorkspaceUsersPanel() {
  const notify = useNotify();
  const [searchQuery, setSearchQuery] = useState('');

  const {
    data,
    loading,
    error,
    reload: fetchUsers,
  } = useResource(() => rolesClient.listUsers(), []);
  const users = useMemo(() => data ?? [], [data]);

  // Assign role form
  const [assignEmail, setAssignEmail] = useState('');
  const [assignRole, setAssignRole] = useState<string>('_workspace_user');
  const [assignProvision, setAssignProvision] = useState(false);
  const [assigning, setAssigning] = useState(false);

  // Workspace status per user
  const [workspaceStatus, setWorkspaceStatus] = useState<Record<string, boolean | 'loading' | null>>({});

  // Role removal confirmation
  const [removeTarget, setRemoveTarget] = useState<{ userId: string; roleId: string; email: string } | null>(null);

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

      // Optionally provision a workspace from the server-default template
      if (assignProvision) {
        try {
          await coderClient.provisionWorkspace({ body: { email: assignEmail } });
          notify('Role assigned and workspace provisioned', 'success');
        } catch {
          notify('Role assigned but workspace provisioning failed', 'error');
        }
      } else {
        notify('Role assigned successfully', 'success');
      }

      setAssignEmail('');
      setAssignProvision(false);
      // Reset workspace statuses so they're re-checked
      setWorkspaceStatus({});
      await fetchUsers();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to assign role', 'error');
    } finally {
      setAssigning(false);
    }
  };

  const handleRemoveRole = async () => {
    if (!removeTarget) return;
    try {
      await rolesClient.removeRole({ userId: removeTarget.userId, roleId: removeTarget.roleId });
      notify('Role removed', 'success');
      setRemoveTarget(null);
      await fetchUsers();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to remove role', 'error');
      setRemoveTarget(null);
    }
  };

  const handleInlineAddRole = async (userId: string, roleId: string) => {
    const u = users.find((x) => x.user_id === userId);
    if (!u?.email) return;
    try {
      await rolesClient.assignRole({ body: { email: u.email, role_id: roleId } });
      notify('Role added', 'success');
      await fetchUsers();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to add role', 'error');
    }
  };

  const handleProvisionForUser = async (email: string) => {
    try {
      // Server-default template; pick a specific one on the user detail page.
      await coderClient.provisionWorkspace({ body: { email } });
      notify('Workspace provisioned', 'success');
      setWorkspaceStatus({});
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Provisioning failed', 'error');
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
    <>
      {/* Assign Role Form */}
      <div className="shrink-0 bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Assign Role</h2>
        <form onSubmit={handleAssignRole} className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="assign-email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              id="assign-email"
              type="email"
              value={assignEmail}
              onChange={(e) => setAssignEmail(e.target.value)}
              className={inputCls}
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
              className={inputCls}
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
          <Button type="submit" loading={assigning} loadingLabel="Assigning...">
            Assign
          </Button>
        </form>
      </div>

      {/* Search */}
      <div className="shrink-0">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={`${inputCls} max-w-md`}
          placeholder="Search by name, email, or username..."
        />
      </div>

      {/* Loading */}
      {loading && !data && (
        <div className="flex-1 min-h-0 bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      <ErrorBanner>{error}</ErrorBanner>

      {/* Users Table */}
      {data && !error && (
        <ScrollPanel>
          <Table className="text-sm">
            <Thead>
              <tr>
                <Th>Name</Th>
                <Th>Email</Th>
                <Th>Username</Th>
                <Th>Roles</Th>
                <Th>Workspace</Th>
                <Th>Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {filteredUsers.length === 0 ? (
                <Tr>
                  <Td colSpan={6} className="py-8 text-center text-gray-500">
                    {searchQuery ? 'No users match your search' : 'No users with workspace roles'}
                  </Td>
                </Tr>
              ) : (
                filteredUsers.map((u) => {
                  const missingRoles = WORKSPACE_ROLES.filter((r) => !u.roles.includes(r));
                  const wsStatus = workspaceStatus[u.user_id];
                  const hasWsRole = u.roles.some((r) => r.startsWith('_workspace'));

                  return (
                    <Tr key={u.user_id} className="hover:bg-gray-50">
                      <Td className="text-gray-900">
                        {u.given_name || u.family_name
                          ? `${u.given_name || ''} ${u.family_name || ''}`.trim()
                          : '-'}
                      </Td>
                      <Td className="text-gray-600">{u.email || '-'}</Td>
                      <Td className="text-gray-600 font-mono text-xs">{u.username || '-'}</Td>
                      <Td>
                        <div className="flex flex-wrap items-center gap-1.5">
                          {u.roles.map((role) => (
                            <Badge key={role} color="blue" pill>
                              {role}
                              <button
                                onClick={() => setRemoveTarget({ userId: u.user_id, roleId: role, email: u.email || '' })}
                                className="text-blue-400 hover:text-red-500 ml-1"
                                title="Remove role"
                              >
                                &times;
                              </button>
                            </Badge>
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
                      </Td>
                      <Td>
                        {!hasWsRole ? (
                          <span className="text-xs text-gray-400">N/A</span>
                        ) : wsStatus === 'loading' ? (
                          <span className="text-xs text-gray-400">Checking...</span>
                        ) : wsStatus === true ? (
                          <Badge color="green" pill>Yes</Badge>
                        ) : wsStatus === false ? (
                          <Button size="xs" variant="secondary" onClick={() => u.email && handleProvisionForUser(u.email)}>
                            Provision
                          </Button>
                        ) : (
                          <span className="text-xs text-gray-400">Unknown</span>
                        )}
                      </Td>
                      <Td>
                        <Link
                          href={`/workspaces/admin/${u.user_id}`}
                          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                        >
                          Manage
                        </Link>
                      </Td>
                    </Tr>
                  );
                })
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
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
    </>
  );
}
