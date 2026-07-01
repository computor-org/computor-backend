'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import ErrorBanner from '@/src/components/ErrorBanner';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Forbidden from '@/src/components/Forbidden';
import SystemRoleCheckboxes from '@/src/components/SystemRoleCheckboxes';
import { useNotify } from '@/src/contexts/NotificationContext';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { AccountsClient } from '@/src/generated/clients/AccountsClient';
import type { UserGet, AccountList, AccountProvider } from 'types/generated';

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
  const [savingRoles, setSavingRoles] = useState(false);
  const notify = useNotify();

  // Confirmation dialogs (styled, instead of window.confirm)
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false);
  const [removeAccountId, setRemoveAccountId] = useState<string | null>(null);

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
    const current = (user.user_roles ?? []).map((r) => r.role_id);
    const toAdd = roles.filter((r) => !current.includes(r));
    const toRemove = current.filter((r) => !roles.includes(r));
    try {
      for (const roleId of toAdd) {
        await api.post('/user-roles', { user_id: userId, role_id: roleId });
      }
      for (const roleId of toRemove) {
        await api.del(`/user-roles/users/${userId}/roles/${roleId}`);
      }
      notify('Roles updated.', 'success');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to update roles', 'error');
    } finally {
      setSavingRoles(false);
    }
  }

  async function toggleArchive() {
    if (!user) return;
    setShowArchiveConfirm(false);
    const archiving = !user.archived_at;
    try {
      if (archiving) await usersClient.routeUsersUsersIdArchivePatch({ id: userId });
      else await usersClient.unarchiveUsersUsersIdUnarchivePatch({ id: userId });
      notify(archiving ? 'User archived.' : 'User unarchived.', 'success');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Operation failed', 'error');
    }
  }

  async function addAccount() {
    const prov = providers.find((p) => p.id === addProvider);
    if (!prov || !providerUrl.trim() || !accountId.trim()) return;
    setSavingAccount(true);
    try {
      await accountsClient.createAccountsAccountsPost({
        body: { provider: providerUrl.trim(), type: prov.type, provider_account_id: accountId.trim(), user_id: userId },
      });
      setAddProvider(null);
      setProviderUrl('');
      setAccountId('');
      setAccounts(await accountsClient.listAccountsAccountsGet({ userId, limit: 100 }));
      notify('Account linked.', 'success');
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to add account', 'error');
    } finally {
      setSavingAccount(false);
    }
  }

  async function removeAccount(id: string) {
    setRemoveAccountId(null);
    try {
      await accountsClient.deleteAccountsAccountsIdDelete({ id });
      setAccounts((a) => a.filter((x) => x.id !== id));
      notify('Linked account removed.', 'success');
    } catch {
      notify('Failed to remove account', 'error');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Requires admin or _user_manager role." backLink="/admin/users" backText="Back" />;
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6 max-w-3xl">
        <Breadcrumbs items={[{ label: 'Users', href: '/admin/users' }, { label: user?.email || 'User' }]} />

        <ErrorBanner>{error}</ErrorBanner>

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
                <button onClick={() => setShowArchiveConfirm(true)} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  {user.archived_at ? 'Unarchive' : 'Archive'}
                </button>
              </div>
            </div>

            <section className="bg-white border border-gray-200 rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div><dt className="text-gray-500">Status</dt><dd className="text-gray-900">{user.archived_at ? 'Archived' : 'Active'}</dd></div>
              <div><dt className="text-gray-500">Created</dt><dd className="text-gray-900">{user.created_at ? new Date(user.created_at).toLocaleString() : '—'}</dd></div>
            </section>

            {/* Roles */}
            <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-gray-900">System roles</h2>
              <SystemRoleCheckboxes selected={roles} onToggle={toggleRole} disabled={savingRoles} />
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
                        <button onClick={() => setRemoveAccountId(acc.id)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
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
                            {savingAccount ? 'Linking…' : 'Link account'}
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

        <ConfirmDialog
          open={showArchiveConfirm}
          title={user?.archived_at ? 'Unarchive user' : 'Archive user'}
          message={
            user?.archived_at
              ? `Unarchive ${user?.email}? They will be able to log in again.`
              : `Archive ${user?.email}? They will not be able to log in.`
          }
          confirmLabel={user?.archived_at ? 'Unarchive' : 'Archive'}
          variant={user?.archived_at ? 'default' : 'danger'}
          onConfirm={toggleArchive}
          onCancel={() => setShowArchiveConfirm(false)}
        />
        <ConfirmDialog
          open={removeAccountId !== null}
          title="Remove linked account"
          message="Remove this linked account? The user can no longer sign in or be matched through it."
          confirmLabel="Remove"
          variant="danger"
          onConfirm={() => removeAccountId && removeAccount(removeAccountId)}
          onCancel={() => setRemoveAccountId(null)}
        />
      </div>
    </AuthenticatedLayout>
  );
}
