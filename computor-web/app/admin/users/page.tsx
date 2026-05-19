'use client';

import { useEffect, useState, useCallback } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { RolesClient } from '@/src/generated/clients/RolesClient';
import { AccountsClient } from '@/src/generated/clients/AccountsClient';
import { AccountProvidersClient, AccountProvider } from '@/src/generated/clients/AccountProvidersClient';
import type { UserList, UserGet, UserCreate, RoleList, AccountList } from 'types/generated';

const usersClient = new UsersClient();
const rolesClient = new RolesClient();
const accountsClient = new AccountsClient();
const accountProvidersClient = new AccountProvidersClient();

const SYSTEM_ROLES = ['_admin', '_user_manager', '_organization_manager', '_workspace_user', '_workspace_maintainer'];

function RoleBadge({ roleId }: { roleId: string }) {
  const colors: Record<string, string> = {
    '_admin': 'bg-red-100 text-red-800',
    '_user_manager': 'bg-purple-100 text-purple-800',
    '_organization_manager': 'bg-blue-100 text-blue-800',
    '_workspace_maintainer': 'bg-orange-100 text-orange-800',
    '_workspace_user': 'bg-green-100 text-green-800',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[roleId] ?? 'bg-gray-100 text-gray-700'}`}>
      {roleId}
    </span>
  );
}

interface CreateUserModal {
  open: boolean;
  username: string;
  email: string;
  givenName: string;
  familyName: string;
  roles: string[];
  error: string | null;
  saving: boolean;
}

interface RolesModal {
  open: boolean;
  user: UserGet | null;
  selectedRoles: string[];
  saving: boolean;
  error: string | null;
}

export default function UsersPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [users, setUsers] = useState<UserList[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [allRoles, setAllRoles] = useState<RoleList[]>([]);

  const [createModal, setCreateModal] = useState<CreateUserModal>({
    open: false, username: '', email: '', givenName: '', familyName: '', roles: [], error: null, saving: false,
  });

  const [rolesModal, setRolesModal] = useState<RolesModal>({
    open: false, user: null, selectedRoles: [], saving: false, error: null,
  });

  const [resetConfirm, setResetConfirm] = useState<{ open: boolean; userId: string; username: string } | null>(null);

  const [accountsModal, setAccountsModal] = useState<{
    open: boolean;
    user: UserList | null;
    accounts: AccountList[];
    loading: boolean;
    addingProvider: string | null;  // provider id being added, or null
    accountId: string;
    saving: boolean;
    error: string | null;
  }>({ open: false, user: null, accounts: [], loading: false, addingProvider: null, accountId: '', saving: false, error: null });

  const [providers, setProviders] = useState<AccountProvider[]>([]);

  const isAdmin = user?.role === 'admin';
  const isUserManager = isAdmin || (user?.systemRoles?.includes('_user_manager') ?? false);

  const notify = (message: string, type: 'success' | 'error') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await usersClient.listUsersUsersGet({
        username: search || undefined,
        limit: 200,
      });
      setUsers(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    if (!isUserManager) return;
    fetchUsers();
    rolesClient.listRolesRolesGet({ builtin: true }).then(setAllRoles).catch(() => {});
    accountProvidersClient.listProviders().then(setProviders).catch(() => {});
  }, [authLoading, isAuthenticated, isUserManager, fetchUsers]);

  // Guard
  if (authLoading) return <AuthenticatedLayout><div className="p-8 text-gray-500">Loading…</div></AuthenticatedLayout>;
  if (!isAuthenticated || !isUserManager) {
    return (
      <AuthenticatedLayout>
        <div className="p-8 text-red-600 font-medium">Access denied. Requires admin or _user_manager role.</div>
      </AuthenticatedLayout>
    );
  }

  const handleCreateUser = async () => {
    setCreateModal(m => ({ ...m, error: null, saving: true }));
    try {
      const payload: UserCreate = {
        username: createModal.username,
        email: createModal.email,
        given_name: createModal.givenName || undefined,
        family_name: createModal.familyName || undefined,
      };
      const created = await usersClient.createUsersUsersPost({ body: payload });

      // Assign roles
      for (const roleId of createModal.roles) {
        await fetch(`/api/user-roles-proxy?user_id=${created.id}&role_id=${roleId}`, { method: 'POST' }).catch(() => {});
      }

      setCreateModal(m => ({ ...m, open: false, username: '', email: '', givenName: '', familyName: '', roles: [], saving: false }));
      notify(`User ${created.username} created`, 'success');
      fetchUsers();
    } catch (e) {
      setCreateModal(m => ({ ...m, error: e instanceof Error ? e.message : 'Failed to create user', saving: false }));
    }
  };

  const handleArchiveToggle = async (u: UserList) => {
    try {
      if (u.archived_at) {
        await usersClient.unarchiveUsersUsersIdUnarchivePatch({ id: u.id });
        notify(`${u.username} unarchived`, 'success');
      } else {
        await usersClient.routeUsersUsersIdArchivePatch({ id: u.id });
        notify(`${u.username} archived`, 'success');
      }
      fetchUsers();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Operation failed', 'error');
    }
  };

  const openRolesModal = async (u: UserList) => {
    try {
      const full = await usersClient.getUsersUsersIdGet({ id: u.id });
      const currentRoleIds = (full.user_roles ?? []).map(r => r.role_id);
      setRolesModal({ open: true, user: full, selectedRoles: currentRoleIds, saving: false, error: null });
    } catch (e) {
      notify('Failed to load user roles', 'error');
    }
  };

  const handleSaveRoles = async () => {
    if (!rolesModal.user) return;
    setRolesModal(m => ({ ...m, saving: true, error: null }));
    const userId = rolesModal.user.id;
    const current = (rolesModal.user.user_roles ?? []).map(r => r.role_id);
    const toAdd = rolesModal.selectedRoles.filter(r => !current.includes(r));
    const toRemove = current.filter(r => !rolesModal.selectedRoles.includes(r));
    try {
      for (const roleId of toAdd) {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/user-roles`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, role_id: roleId }),
        });
      }
      for (const roleId of toRemove) {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/user-roles/users/${userId}/roles/${roleId}`, {
          method: 'DELETE',
          credentials: 'include',
        });
      }
      setRolesModal(m => ({ ...m, open: false, user: null, saving: false }));
      notify('Roles updated', 'success');
      fetchUsers();
    } catch (e) {
      setRolesModal(m => ({ ...m, error: e instanceof Error ? e.message : 'Failed to update roles', saving: false }));
    }
  };

  const handleResetPassword = async (userId: string) => {
    try {
      const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API}/password/reset`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, manager_password: '' }),
      });
      if (!res.ok) throw new Error('Failed');
      notify('Password reset — user must set a new password', 'success');
    } catch {
      notify('Failed to reset password', 'error');
    }
    setResetConfirm(null);
  };

  const openAccountsModal = async (u: UserList) => {
    setAccountsModal(m => ({ ...m, open: true, user: u, accounts: [], loading: true, addingProvider: null, accountId: '', error: null }));
    try {
      const data = await accountsClient.listAccountsAccountsGet({ userId: u.id, limit: 100 });
      setAccountsModal(m => ({ ...m, accounts: data, loading: false }));
    } catch {
      setAccountsModal(m => ({ ...m, loading: false, error: 'Failed to load accounts' }));
    }
  };

  const handleAddAccount = async () => {
    const { user: u, addingProvider, accountId } = accountsModal;
    if (!u || !addingProvider || !accountId.trim()) return;
    const prov = providers.find(p => p.id === addingProvider);
    if (!prov) return;
    setAccountsModal(m => ({ ...m, saving: true, error: null }));
    try {
      await accountsClient.createAccountsAccountsPost({
        body: { provider: prov.provider, type: prov.type, provider_account_id: accountId.trim(), user_id: u.id },
      });
      const data = await accountsClient.listAccountsAccountsGet({ userId: u.id, limit: 100 });
      setAccountsModal(m => ({ ...m, accounts: data, addingProvider: null, accountId: '', saving: false }));
      notify('Account linked', 'success');
    } catch (e) {
      setAccountsModal(m => ({ ...m, error: e instanceof Error ? e.message : 'Failed to add account', saving: false }));
    }
  };

  const handleDeleteAccount = async (accountId: string) => {
    try {
      await accountsClient.deleteAccountsAccountsIdDelete({ id: accountId });
      setAccountsModal(m => ({ ...m, accounts: m.accounts.filter(a => a.id !== accountId) }));
      notify('Account removed', 'success');
    } catch {
      notify('Failed to remove account', 'error');
    }
  };

  const filtered = users.filter(u =>
    !search ||
    u.username?.toLowerCase().includes(search.toLowerCase()) ||
    u.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <AuthenticatedLayout>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Users</h1>
            <p className="text-sm text-gray-500 mt-1">{users.length} total</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCreateModal(m => ({ ...m, open: true }))}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              + Create User
            </button>
          </div>
        </div>

        {/* Notification */}
        {notification && (
          <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${notification.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
            {notification.message}
          </div>
        )}

        {/* Search */}
        <div className="mb-4">
          <input
            type="text"
            placeholder="Search by username or email…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Table */}
        {loading ? (
          <div className="text-gray-500 py-8 text-center">Loading users…</div>
        ) : error ? (
          <div className="text-red-600 py-8 text-center">{error}</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map(u => (
                  <tr key={u.id} className={u.archived_at ? 'opacity-50' : ''}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900 text-sm">{u.username}</div>
                      <div className="text-xs text-gray-500">{u.given_name} {u.family_name}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{u.email ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${u.archived_at ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-800'}`}>
                        {u.archived_at ? 'Archived' : 'Active'}
                      </span>
                      {u.is_service && (
                        <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">Service</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => openRolesModal(u)}
                          className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        >
                          Roles
                        </button>
                        <button
                          onClick={() => openAccountsModal(u)}
                          className="px-2 py-1 text-xs text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                        >
                          Accounts
                        </button>
                        <button
                          onClick={() => handleArchiveToggle(u)}
                          className="px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded transition-colors"
                        >
                          {u.archived_at ? 'Unarchive' : 'Archive'}
                        </button>
                        {isAdmin && (
                          <button
                            onClick={() => setResetConfirm({ open: true, userId: u.id, username: u.username ?? '' })}
                            className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
                          >
                            Reset PW
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500">No users found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create User Modal */}
      {createModal.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Create User</h2>
              {createModal.error && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{createModal.error}</div>
              )}
              <div className="space-y-3">
                {[
                  { label: 'Username *', key: 'username', placeholder: 'john.doe' },
                  { label: 'Email *', key: 'email', placeholder: 'john@example.com' },
                  { label: 'Given Name', key: 'givenName', placeholder: 'John' },
                  { label: 'Family Name', key: 'familyName', placeholder: 'Doe' },
                ].map(f => (
                  <div key={f.key}>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{f.label}</label>
                    <input
                      type="text"
                      placeholder={f.placeholder}
                      value={(createModal as any)[f.key]}
                      onChange={e => setCreateModal(m => ({ ...m, [f.key]: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                ))}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Roles</label>
                  <div className="flex flex-wrap gap-2">
                    {SYSTEM_ROLES.map(r => (
                      <label key={r} className="flex items-center gap-1 text-xs cursor-pointer">
                        <input
                          type="checkbox"
                          checked={createModal.roles.includes(r)}
                          onChange={e => setCreateModal(m => ({
                            ...m,
                            roles: e.target.checked ? [...m.roles, r] : m.roles.filter(x => x !== r),
                          }))}
                        />
                        {r}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
              <p className="mt-3 text-xs text-gray-500">User will have no password set. Send them an invite link to let them set one.</p>
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button
                onClick={() => setCreateModal(m => ({ ...m, open: false, error: null }))}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateUser}
                disabled={createModal.saving || !createModal.username || !createModal.email}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {createModal.saving ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Roles Modal */}
      {rolesModal.open && rolesModal.user && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-1">Roles for {rolesModal.user.username}</h2>
              <p className="text-xs text-gray-500 mb-4">{rolesModal.user.email}</p>
              {rolesModal.error && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{rolesModal.error}</div>
              )}
              <div className="space-y-2">
                {SYSTEM_ROLES.map(r => (
                  <label key={r} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rolesModal.selectedRoles.includes(r)}
                      onChange={e => setRolesModal(m => ({
                        ...m,
                        selectedRoles: e.target.checked
                          ? [...m.selectedRoles, r]
                          : m.selectedRoles.filter(x => x !== r),
                      }))}
                    />
                    <RoleBadge roleId={r} />
                  </label>
                ))}
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button
                onClick={() => setRolesModal(m => ({ ...m, open: false, user: null }))}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRoles}
                disabled={rolesModal.saving}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {rolesModal.saving ? 'Saving…' : 'Save Roles'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Password Confirm */}
      {resetConfirm?.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Reset Password?</h2>
            <p className="text-sm text-gray-600 mb-4">
              This will clear <strong>{resetConfirm.username}</strong>'s password. They will need to set a new one via invite link or admin.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setResetConfirm(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
              <button
                onClick={() => handleResetPassword(resetConfirm.userId)}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Reset Password
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Accounts Modal */}
      {accountsModal.open && accountsModal.user && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 flex flex-col max-h-[80vh]">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900">Accounts — {accountsModal.user.username}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{accountsModal.user.email}</p>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {accountsModal.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{accountsModal.error}</div>
              )}

              {/* Existing accounts */}
              {accountsModal.loading ? (
                <div className="text-sm text-gray-500">Loading accounts…</div>
              ) : accountsModal.accounts.length === 0 ? (
                <div className="text-sm text-gray-400 italic">No linked accounts yet.</div>
              ) : (
                <div className="space-y-2">
                  {accountsModal.accounts.map(acc => {
                    const prov = providers.find(p => p.provider === acc.provider && p.type === acc.type);
                    return (
                      <div key={acc.id} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                        <div>
                          <span className="text-sm font-medium text-gray-900">{prov?.display_name ?? acc.provider}</span>
                          <span className="mx-2 text-gray-300">·</span>
                          <span className="text-sm text-gray-600">{acc.provider_account_id}</span>
                        </div>
                        <button
                          onClick={() => handleDeleteAccount(acc.id)}
                          className="text-xs text-red-500 hover:text-red-700 transition-colors"
                        >
                          Remove
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Add account form */}
              <div className="border-t border-gray-100 pt-4">
                <p className="text-xs font-medium text-gray-700 mb-2">Link new account</p>
                {accountsModal.addingProvider === null ? (
                  <div className="flex flex-wrap gap-2">
                    {providers.map(p => (
                      <button
                        key={p.id}
                        onClick={() => setAccountsModal(m => ({ ...m, addingProvider: p.id, accountId: '', error: null }))}
                        className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        + {p.display_name}
                      </button>
                    ))}
                  </div>
                ) : (() => {
                  const prov = providers.find(p => p.id === accountsModal.addingProvider)!;
                  return (
                    <div className="space-y-2">
                      <label className="block text-xs font-medium text-gray-700">{prov.field_label}</label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          placeholder={prov.placeholder}
                          value={accountsModal.accountId}
                          onChange={e => setAccountsModal(m => ({ ...m, accountId: e.target.value }))}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                          autoFocus
                        />
                        <button
                          onClick={handleAddAccount}
                          disabled={accountsModal.saving || !accountsModal.accountId.trim()}
                          className="px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                        >
                          {accountsModal.saving ? '…' : 'Add'}
                        </button>
                        <button
                          onClick={() => setAccountsModal(m => ({ ...m, addingProvider: null, accountId: '' }))}
                          className="px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  );
                })()}
              </div>
            </div>

            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end">
              <button
                onClick={() => setAccountsModal(m => ({ ...m, open: false, user: null }))}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}
