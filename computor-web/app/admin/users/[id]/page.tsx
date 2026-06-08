'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import NotFound from '@/src/components/NotFound';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { AccountsClient } from '@/src/generated/clients/AccountsClient';
import type { UserGet, AccountList, AccountProvider } from 'types/generated';

const SYSTEM_ROLES = ['_admin', '_user_manager', '_organization_manager', '_workspace_user', '_workspace_maintainer'];
const usersClient = new UsersClient();
const accountsClient = new AccountsClient();

export default function UserDetailPage() {
  const userId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isUserManager } = usePermissions();
  const canManage = isAdmin || isUserManager;

  const [user, setUser] = useState<UserGet | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<AccountList[]>([]);
  const [providers, setProviders] = useState<AccountProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [savingRoles, setSavingRoles] = useState(false);

  // Add-account form
  const [addProvider, setAddProvider] = useState<string | null>(null);
  const [providerUrl, setProviderUrl] = useState('');
  const [accountId, setAccountId] = useState('');
  const [savingAccount, setSavingAccount] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const u = await usersClient.getUsersUsersIdGet({ id: userId });
      setUser(u);
      setRoles((u.user_roles ?? []).map((r) => r.role_id));
      const [acc, provs] = await Promise.all([
        accountsClient.listAccountsAccountsGet({ userId, limit: 100 }).catch(() => [] as AccountList[]),
        accountsClient.listAccountProvidersAccountsProvidersGet().catch(() => [] as AccountProvider[]),
      ]);
      setAccounts(acc);
      setProviders(provs);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load user');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  const toggleRole = (r: string) => setRoles((rs) => (rs.includes(r) ? rs.filter((x) => x !== r) : [...rs, r]));

  async function saveRoles() {
    if (!user) return;
    setSavingRoles(true);
    setMsg(null);
    const current = (user.user_roles ?? []).map((r) => r.role_id);
    const toAdd = roles.filter((r) => !current.includes(r));
    const toRemove = current.filter((r) => !roles.includes(r));
    try {
      for (const roleId of toAdd) {
        await apiFetch(`${API_BASE_URL}/user-roles`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId, role_id: roleId }),
        });
      }
      for (const roleId of toRemove) {
        await apiFetch(`${API_BASE_URL}/user-roles/users/${userId}/roles/${roleId}`, { method: 'DELETE' });
      }
      setMsg('Roles updated.');
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Failed to update roles');
    } finally {
      setSavingRoles(false);
    }
  }

  async function toggleArchive() {
    if (!user) return;
    const archiving = !user.archived_at;
    if (!confirm(archiving ? `Archive ${user.email}? They will not be able to log in.` : `Unarchive ${user.email}?`)) return;
    try {
      if (archiving) await usersClient.routeUsersUsersIdArchivePatch({ id: userId });
      else await usersClient.unarchiveUsersUsersIdUnarchivePatch({ id: userId });
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Operation failed');
    }
  }

  async function addAccount() {
    const prov = providers.find((p) => p.id === addProvider);
    if (!prov || !providerUrl.trim() || !accountId.trim()) return;
    setSavingAccount(true);
    setMsg(null);
    try {
      await accountsClient.createAccountsAccountsPost({
        body: { provider: providerUrl.trim(), type: prov.type, provider_account_id: accountId.trim(), user_id: userId },
      });
      setAddProvider(null);
      setProviderUrl('');
      setAccountId('');
      setAccounts(await accountsClient.listAccountsAccountsGet({ userId, limit: 100 }));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Failed to add account');
    } finally {
      setSavingAccount(false);
    }
  }

  async function removeAccount(id: string) {
    if (!confirm('Remove this linked account?')) return;
    try {
      await accountsClient.deleteAccountsAccountsIdDelete({ id });
      setAccounts((a) => a.filter((x) => x.id !== id));
    } catch {
      setMsg('Failed to remove account');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="Requires admin or _user_manager role." backLink="/admin/users" backText="Back" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6 max-w-3xl">
        <Breadcrumbs items={[{ label: 'Users', href: '/admin/users' }, { label: user?.email || 'User' }]} />

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : user ? (
          <>
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{user.email || 'User'}</h1>
                <p className="mt-1 text-sm text-gray-500">{user.given_name} {user.family_name}</p>
              </div>
              <div className="flex items-center gap-2">
                <Link href={`/admin/users/${userId}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  Edit
                </Link>
                <button onClick={toggleArchive} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  {user.archived_at ? 'Unarchive' : 'Archive'}
                </button>
              </div>
            </div>

            {msg && <div className="p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-600">{msg}</div>}

            <section className="bg-white border border-gray-200 rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div><dt className="text-gray-500">Status</dt><dd className="text-gray-900">{user.archived_at ? 'Archived' : 'Active'}</dd></div>
              <div><dt className="text-gray-500">Created</dt><dd className="text-gray-900">{user.created_at ? new Date(user.created_at).toLocaleString() : '—'}</dd></div>
            </section>

            {/* Roles */}
            <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-gray-900">System roles</h2>
              <div className="flex flex-wrap gap-3">
                {SYSTEM_ROLES.map((r) => (
                  <label key={r} className="flex items-center gap-1.5 text-sm text-gray-700">
                    <input type="checkbox" checked={roles.includes(r)} onChange={() => toggleRole(r)} />
                    {r}
                  </label>
                ))}
              </div>
              <button onClick={saveRoles} disabled={savingRoles} className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {savingRoles ? 'Saving…' : 'Save roles'}
              </button>
            </section>

            {/* Accounts */}
            <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-gray-900">Linked accounts</h2>
              {accounts.length === 0 ? (
                <p className="text-sm text-gray-400 italic">No linked accounts.</p>
              ) : (
                <div className="space-y-2">
                  {accounts.map((acc) => {
                    const prov = providers.find((p) => p.provider === acc.provider && p.type === acc.type);
                    return (
                      <div key={acc.id} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="text-sm">
                          <span className="font-medium text-gray-900">{prov?.display_name ?? acc.provider}</span>
                          <span className="mx-2 text-gray-300">·</span>
                          <span className="text-gray-600">{acc.provider_account_id}</span>
                        </div>
                        <button onClick={() => removeAccount(acc.id)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
                      </div>
                    );
                  })}
                </div>
              )}
              <div className="border-t border-gray-100 pt-3">
                {addProvider === null ? (
                  <div className="flex flex-wrap gap-2">
                    {providers.map((p) => (
                      <button key={p.id} onClick={() => { setAddProvider(p.id); setProviderUrl(p.provider); setAccountId(''); }} className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50">
                        + {p.display_name}
                      </button>
                    ))}
                  </div>
                ) : (
                  (() => {
                    const prov = providers.find((p) => p.id === addProvider)!;
                    return (
                      <div className="space-y-2">
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">Provider URL</label>
                          <input value={providerUrl} onChange={(e) => setProviderUrl(e.target.value)} placeholder="gitlab.com" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" autoFocus />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">{prov.field_label}</label>
                          <input value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder={prov.placeholder} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <div className="flex justify-end gap-2">
                          <button onClick={() => setAddProvider(null)} className="px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 rounded-lg">Cancel</button>
                          <button onClick={addAccount} disabled={savingAccount || !providerUrl.trim() || !accountId.trim()} className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                            {savingAccount ? '…' : 'Link account'}
                          </button>
                        </div>
                      </div>
                    );
                  })()
                )}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </AuthenticatedLayout>
  );
}
