'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import Forbidden from '@/src/components/Forbidden';
import SystemRoleCheckboxes from '@/src/components/SystemRoleCheckboxes';
import ConnectUsersSection from '@/src/components/users/ConnectUsersSection';
import { useNotify } from '@/src/contexts/NotificationContext';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { UserRolesClient } from '@/src/generated/clients/UserRolesClient';
import { AccountsClient } from '@/src/generated/clients/AccountsClient';
import type { UserGet, AccountList, AccountProvider } from 'types/generated';

const usersClient = new UsersClient();
const userClient = new UserRolesClient();
const accountsClient = new AccountsClient();

export default function UserDetailPage() {
  const userId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user: authUser } = useAuth();
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
  const [showBanConfirm, setShowBanConfirm] = useState(false);
  const [showUnbanConfirm, setShowUnbanConfirm] = useState(false);
  const [banReason, setBanReason] = useState('');
  const [removeAccountId, setRemoveAccountId] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

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
        await userClient.createUserRoleUserRolesPost({ body: { user_id: userId, role_id: roleId } });
      }
      for (const roleId of toRemove) {
        await userClient.deleteUserRoleEndpointUserRolesUsersUserIdRolesRoleIdDelete({ userId, roleId });
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

  async function banUser() {
    if (!user) return;
    setShowBanConfirm(false);
    try {
      await usersClient.banUserUsersUserIdBanPatch({ userId, body: { reason: banReason.trim() || null } });
      notify('User banned. They can no longer sign in.', 'success');
      setBanReason('');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to ban user', 'error');
    }
  }

  async function unbanUser() {
    if (!user) return;
    setShowUnbanConfirm(false);
    try {
      await usersClient.unbanUserUsersUserIdUnbanPatch({ userId });
      notify('User unbanned. They can sign in again.', 'success');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to unban user', 'error');
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

  // Thrown errors surface inside ConfirmDeleteDialog (e.g. the backend's
  // "archive first" refusal), so the dialog explains a blocked delete in place.
  async function deleteUser() {
    await usersClient.deleteUsersUsersIdDelete({ id: userId });
    notify('User deleted.', 'success');
    router.push('/admin/users');
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
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: 'Users', href: '/admin/users' }, { label: user?.email || 'User' }]}
          title={user?.email || 'User'}
          subtitle={user && <span className="text-sm text-muted">{user.given_name} {user.family_name}</span>}
          actions={
            user ? (
              <>
                <ButtonLink href={`/admin/users/${userId}/edit`} variant="secondary">Edit</ButtonLink>
                <Button variant="secondary" onClick={() => setShowArchiveConfirm(true)}>
                  {user.archived_at ? 'Unarchive' : 'Archive'}
                </Button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : user ? (
          <ScrollArea>
            <section className="bg-surface border border-rule rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div>
                <dt className="text-muted">Status</dt>
                <dd className="text-fg">
                  {user.banned_at ? <span className="text-danger-text font-medium">Banned</span> : user.archived_at ? 'Archived' : 'Active'}
                </dd>
              </div>
              <div><dt className="text-muted">Created</dt><dd className="text-fg">{user.created_at ? new Date(user.created_at).toLocaleString() : '—'}</dd></div>
            </section>

            {/* Access control (ban / unban) */}
            <section className="bg-surface border border-rule rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-fg">Access control</h2>
              {user.banned_at ? (
                <div className="space-y-2 text-sm">
                  <p className="text-danger-text font-medium">
                    Banned on {new Date(user.banned_at).toLocaleString()}. This user cannot authenticate.
                  </p>
                  {user.ban_reason ? <p className="text-muted">Reason: {user.ban_reason}</p> : null}
                  <Button onClick={() => setShowUnbanConfirm(true)}>Unban user</Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-muted">Banning immediately blocks this user from signing in and revokes their active sessions.</p>
                  <input
                    value={banReason}
                    onChange={(e) => setBanReason(e.target.value)}
                    placeholder="Reason (optional)"
                    maxLength={1024}
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line"
                  />
                  <Button variant="danger" onClick={() => setShowBanConfirm(true)}>Ban user</Button>
                </div>
              )}
            </section>

            {/* Roles */}
            <section className="bg-surface border border-rule rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-fg">System roles</h2>
              <SystemRoleCheckboxes selected={roles} onToggle={toggleRole} disabled={savingRoles} />
              <Button onClick={saveRoles} loading={savingRoles} loadingLabel="Saving…">Save roles</Button>
            </section>

            {/* Accounts */}
            <section className="bg-surface border border-rule rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-fg">Linked accounts</h2>
              {accounts.length === 0 ? (
                <p className="text-sm text-subtle italic">No linked accounts.</p>
              ) : (
                <div className="space-y-2">
                  {accounts.map((acc) => {
                    const prov = providers.find((p) => p.provider === acc.provider && p.type === acc.type);
                    return (
                      <div key={acc.id} className="flex items-center justify-between px-3 py-2 bg-canvas rounded-lg border border-rule">
                        <div className="text-sm">
                          <span className="font-medium text-fg">{prov?.display_name ?? acc.provider}</span>
                          <span className="mx-2 text-faint">·</span>
                          <span className="text-muted">{acc.provider_account_id}</span>
                        </div>
                        <Button variant="dangerGhost" size="xs" onClick={() => setRemoveAccountId(acc.id)}>Remove</Button>
                      </div>
                    );
                  })}
                </div>
              )}
              <div className="border-t border-rule-soft pt-3">
                {addProvider === null ? (
                  <div className="flex flex-wrap gap-2">
                    {providers.map((p) => (
                      <Button key={p.id} variant="secondary" size="xs" onClick={() => { setAddProvider(p.id); setProviderUrl(p.provider); setAccountId(''); }}>
                        + {p.display_name}
                      </Button>
                    ))}
                  </div>
                ) : (
                  (() => {
                    const prov = providers.find((p) => p.id === addProvider)!;
                    return (
                      <div className="space-y-2">
                        <div>
                          <label className="block text-xs font-medium text-body mb-1">Provider URL</label>
                          <input value={providerUrl} onChange={(e) => setProviderUrl(e.target.value)} placeholder="gitlab.com" className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line" autoFocus />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-body mb-1">{prov.field_label}</label>
                          <input value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder={prov.placeholder} className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line" />
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => setAddProvider(null)}>Cancel</Button>
                          <Button size="sm" onClick={addAccount} disabled={!providerUrl.trim() || !accountId.trim()} loading={savingAccount} loadingLabel="Linking…">
                            Link account
                          </Button>
                        </div>
                      </div>
                    );
                  })()
                )}
              </div>
            </section>

            {/* Connect users (absorb a pre-provisioned roster import) */}
            {!user.is_service && (
              <ConnectUsersSection
                key={user.id}
                user={user}
                hasBuiltinAccount={accounts.some((a) => a.builtin === true)}
                onConnected={load}
              />
            )}

            {/* Danger zone: two-step delete policy (issue #382). The backend
                guard is the authority; the hints here mirror what it will
                refuse so the reader learns it before the attempt. */}
            {!user.is_service && authUser?.id !== user.id && (
              <section className="bg-surface border border-danger-line rounded-lg p-6 space-y-3">
                <h2 className="text-lg font-semibold text-danger-text">Delete user</h2>
                <p className="text-sm text-muted">
                  {accounts.some((a) => a.builtin === true)
                    ? 'This user has signed in before. Deletion is a deliberate two-step action: archive the user first, then an administrator can permanently delete them.'
                    : 'This user has never signed in (pre-provisioned by import, manual creation, or an unredeemed invite). Deleting removes the record together with its course memberships.'}
                </p>
                <Button variant="danger" onClick={() => setShowDeleteDialog(true)}>Delete user…</Button>
              </section>
            )}
          </ScrollArea>
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
          open={showBanConfirm}
          title="Ban user"
          message={`Ban ${user?.email}? They will be signed out and blocked from authenticating until unbanned.`}
          confirmLabel="Ban"
          variant="danger"
          onConfirm={banUser}
          onCancel={() => setShowBanConfirm(false)}
        />
        <ConfirmDialog
          open={showUnbanConfirm}
          title="Unban user"
          message={`Unban ${user?.email}? They will be able to sign in again.`}
          confirmLabel="Unban"
          onConfirm={unbanUser}
          onCancel={() => setShowUnbanConfirm(false)}
        />
        {showDeleteDialog && user && (
          <ConfirmDeleteDialog
            title="Delete user"
            message={`Permanently delete ${user.email}? This cannot be undone.`}
            confirmWord={user.email ?? 'DELETE'}
            blockedReason={
              roles.some((r) => r === '_admin' || r.endsWith('_admin'))
                ? 'Users holding an admin role cannot be deleted. Revoke the admin role first.'
                : accounts.some((a) => a.builtin === true) && !user.archived_at
                  ? 'This user has signed in before. Archive them first; an administrator can then delete the account.'
                  : accounts.some((a) => a.builtin === true) && !isAdmin
                    ? 'Only administrators can delete a user who has signed in.'
                    : null
            }
            onConfirm={deleteUser}
            onClose={() => setShowDeleteDialog(false)}
          />
        )}
        <ConfirmDialog
          open={removeAccountId !== null}
          title="Remove linked account"
          message="Remove this linked account? The user can no longer sign in or be matched through it."
          confirmLabel="Remove"
          variant="danger"
          onConfirm={() => removeAccountId && removeAccount(removeAccountId)}
          onCancel={() => setRemoveAccountId(null)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
