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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';

const usersClient = new UsersClient();
const userClient = new UserRolesClient();
const accountsClient = new AccountsClient();

const COPY = {
  de: {
    loadFailed: 'Benutzer konnte nicht geladen werden',
    rolesUpdated: 'Rollen aktualisiert.',
    rolesFailed: 'Rollen konnten nicht aktualisiert werden',
    archived: 'Benutzer archiviert.',
    unarchived: 'Benutzer wiederhergestellt.',
    operationFailed: 'Vorgang fehlgeschlagen',
    banned: 'Benutzer gesperrt. Eine Anmeldung ist nicht mehr möglich.',
    banFailed: 'Benutzer konnte nicht gesperrt werden',
    unbanned: 'Sperre aufgehoben. Der Benutzer kann sich wieder anmelden.',
    unbanFailed: 'Sperre konnte nicht aufgehoben werden',
    accountLinked: 'Konto verknüpft.',
    accountAddFailed: 'Konto konnte nicht hinzugefügt werden',
    deleted: 'Benutzer gelöscht.',
    accountRemoved: 'Verknüpftes Konto entfernt.',
    accountRemoveFailed: 'Konto konnte nicht entfernt werden',
    forbidden: 'Erfordert die Rolle admin oder _user_manager.',
    back: 'Zurück',
    users: 'Benutzer',
    user: 'Benutzer',
    edit: 'Bearbeiten',
    unarchive: 'Wiederherstellen',
    archive: 'Archivieren',
    loading: 'Wird geladen…',
    status: 'Status',
    bannedLabel: 'Gesperrt',
    archivedLabel: 'Archiviert',
    active: 'Aktiv',
    created: 'Erstellt',
    accessControl: 'Zugriffskontrolle',
    bannedOn: (when: string) => `Gesperrt am ${when}. Dieser Benutzer kann sich nicht anmelden.`,
    reason: (reason: string) => `Grund: ${reason}`,
    unbanUser: 'Sperre aufheben',
    banExplain: 'Eine Sperre verhindert sofort die Anmeldung dieses Benutzers und beendet seine aktiven Sitzungen.',
    reasonPlaceholder: 'Grund (optional)',
    banUser: 'Benutzer sperren',
    systemRoles: 'Systemrollen',
    saving: 'Wird gespeichert…',
    saveRoles: 'Rollen speichern',
    linkedAccounts: 'Verknüpfte Konten',
    noAccounts: 'Keine verknüpften Konten.',
    remove: 'Entfernen',
    providerUrl: 'Provider-URL',
    cancel: 'Abbrechen',
    linking: 'Wird verknüpft…',
    linkAccount: 'Konto verknüpfen',
    deleteUser: 'Benutzer löschen',
    deleteExplainSignedIn: 'Dieser Benutzer hat sich bereits angemeldet. Das Löschen erfolgt bewusst in zwei Schritten: Zuerst wird der Benutzer archiviert, danach kann ein Administrator ihn endgültig löschen.',
    deleteExplainNever: 'Dieser Benutzer hat sich noch nie angemeldet (vorab durch Import, manuelles Anlegen oder eine nicht eingelöste Einladung angelegt). Beim Löschen werden der Datensatz und seine Kursmitgliedschaften entfernt.',
    deleteButton: 'Benutzer löschen…',
    unarchiveTitle: 'Benutzer wiederherstellen',
    archiveTitle: 'Benutzer archivieren',
    unarchiveMessage: (email: string | null | undefined) => `${email} wiederherstellen? Der Benutzer kann sich dann wieder anmelden.`,
    archiveMessage: (email: string | null | undefined) => `${email} archivieren? Der Benutzer kann sich dann nicht mehr anmelden.`,
    banTitle: 'Benutzer sperren',
    banMessage: (email: string | null | undefined) => `${email} sperren? Der Benutzer wird abgemeldet und kann sich bis zur Aufhebung der Sperre nicht anmelden.`,
    banConfirm: 'Sperren',
    unbanTitle: 'Sperre aufheben',
    unbanMessage: (email: string | null | undefined) => `Sperre für ${email} aufheben? Der Benutzer kann sich wieder anmelden.`,
    unbanConfirm: 'Aufheben',
    deleteMessage: (email: string | null | undefined) => `${email} endgültig löschen? Das kann nicht rückgängig gemacht werden.`,
    blockedAdmin: 'Benutzer mit einer Admin-Rolle können nicht gelöscht werden. Entziehe zuerst die Admin-Rolle.',
    blockedArchiveFirst: 'Dieser Benutzer hat sich bereits angemeldet. Archiviere ihn zuerst, danach kann ein Administrator das Konto löschen.',
    blockedAdminOnly: 'Nur Administratoren können einen Benutzer löschen, der sich bereits angemeldet hat.',
    removeTitle: 'Verknüpftes Konto entfernen',
    removeMessage: 'Dieses verknüpfte Konto entfernen? Der Benutzer kann sich darüber nicht mehr anmelden und wird darüber nicht mehr zugeordnet.',
  },
  en: {
    loadFailed: 'Failed to load user',
    rolesUpdated: 'Roles updated.',
    rolesFailed: 'Failed to update roles',
    archived: 'User archived.',
    unarchived: 'User unarchived.',
    operationFailed: 'Operation failed',
    banned: 'User banned. They can no longer sign in.',
    banFailed: 'Failed to ban user',
    unbanned: 'User unbanned. They can sign in again.',
    unbanFailed: 'Failed to unban user',
    accountLinked: 'Account linked.',
    accountAddFailed: 'Failed to add account',
    deleted: 'User deleted.',
    accountRemoved: 'Linked account removed.',
    accountRemoveFailed: 'Failed to remove account',
    forbidden: 'Requires admin or _user_manager role.',
    back: 'Back',
    users: 'Users',
    user: 'User',
    edit: 'Edit',
    unarchive: 'Unarchive',
    archive: 'Archive',
    loading: 'Loading…',
    status: 'Status',
    bannedLabel: 'Banned',
    archivedLabel: 'Archived',
    active: 'Active',
    created: 'Created',
    accessControl: 'Access control',
    bannedOn: (when: string) => `Banned on ${when}. This user cannot authenticate.`,
    reason: (reason: string) => `Reason: ${reason}`,
    unbanUser: 'Unban user',
    banExplain: 'Banning immediately blocks this user from signing in and revokes their active sessions.',
    reasonPlaceholder: 'Reason (optional)',
    banUser: 'Ban user',
    systemRoles: 'System roles',
    saving: 'Saving…',
    saveRoles: 'Save roles',
    linkedAccounts: 'Linked accounts',
    noAccounts: 'No linked accounts.',
    remove: 'Remove',
    providerUrl: 'Provider URL',
    cancel: 'Cancel',
    linking: 'Linking…',
    linkAccount: 'Link account',
    deleteUser: 'Delete user',
    deleteExplainSignedIn: 'This user has signed in before. Deletion is a deliberate two-step action: archive the user first, then an administrator can permanently delete them.',
    deleteExplainNever: 'This user has never signed in (pre-provisioned by import, manual creation, or an unredeemed invite). Deleting removes the record together with its course memberships.',
    deleteButton: 'Delete user…',
    unarchiveTitle: 'Unarchive user',
    archiveTitle: 'Archive user',
    unarchiveMessage: (email: string | null | undefined) => `Unarchive ${email}? They will be able to log in again.`,
    archiveMessage: (email: string | null | undefined) => `Archive ${email}? They will not be able to log in.`,
    banTitle: 'Ban user',
    banMessage: (email: string | null | undefined) => `Ban ${email}? They will be signed out and blocked from authenticating until unbanned.`,
    banConfirm: 'Ban',
    unbanTitle: 'Unban user',
    unbanMessage: (email: string | null | undefined) => `Unban ${email}? They will be able to sign in again.`,
    unbanConfirm: 'Unban',
    deleteMessage: (email: string | null | undefined) => `Permanently delete ${email}? This cannot be undone.`,
    blockedAdmin: 'Users holding an admin role cannot be deleted. Revoke the admin role first.',
    blockedArchiveFirst: 'This user has signed in before. Archive them first; an administrator can then delete the account.',
    blockedAdminOnly: 'Only administrators can delete a user who has signed in.',
    removeTitle: 'Remove linked account',
    removeMessage: 'Remove this linked account? The user can no longer sign in or be matched through it.',
  },
};

export default function UserDetailPage() {
  const userId = useParams().id as string;
  const router = useRouter();
  const language = useUiLanguage();
  const t = COPY[language];
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
      setError(e instanceof Error ? e.message : t.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [userId, t.loadFailed]);

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
      notify(t.rolesUpdated, 'success');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.rolesFailed, 'error');
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
      notify(archiving ? t.archived : t.unarchived, 'success');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.operationFailed, 'error');
    }
  }

  async function banUser() {
    if (!user) return;
    setShowBanConfirm(false);
    try {
      await usersClient.banUserUsersUserIdBanPatch({ userId, body: { reason: banReason.trim() || null } });
      notify(t.banned, 'success');
      setBanReason('');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.banFailed, 'error');
    }
  }

  async function unbanUser() {
    if (!user) return;
    setShowUnbanConfirm(false);
    try {
      await usersClient.unbanUserUsersUserIdUnbanPatch({ userId });
      notify(t.unbanned, 'success');
      await load();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.unbanFailed, 'error');
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
      notify(t.accountLinked, 'success');
    } catch (e) {
      notify(e instanceof Error ? e.message : t.accountAddFailed, 'error');
    } finally {
      setSavingAccount(false);
    }
  }

  // Thrown errors surface inside ConfirmDeleteDialog (e.g. the backend's
  // "archive first" refusal), so the dialog explains a blocked delete in place.
  async function deleteUser() {
    await usersClient.deleteUsersUsersIdDelete({ id: userId });
    notify(t.deleted, 'success');
    router.push('/admin/users');
  }

  async function removeAccount(id: string) {
    setRemoveAccountId(null);
    try {
      await accountsClient.deleteAccountsAccountsIdDelete({ id });
      setAccounts((a) => a.filter((x) => x.id !== id));
      notify(t.accountRemoved, 'success');
    } catch {
      notify(t.accountRemoveFailed, 'error');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} backLink="/admin/users" backText={t.back} />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: t.users, href: '/admin/users' }, { label: user?.email || t.user }]}
          title={user?.email || t.user}
          subtitle={user && <span className="text-sm text-muted">{user.given_name} {user.family_name}</span>}
          actions={
            user ? (
              <>
                <ButtonLink href={`/admin/users/${userId}/edit`} variant="secondary">{t.edit}</ButtonLink>
                <Button variant="secondary" onClick={() => setShowArchiveConfirm(true)}>
                  {user.archived_at ? t.unarchive : t.archive}
                </Button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : user ? (
          <ScrollArea>
            <section className="bg-surface border border-rule rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div>
                <dt className="text-muted">{t.status}</dt>
                <dd className="text-fg">
                  {user.banned_at ? <span className="text-danger-text font-medium">{t.bannedLabel}</span> : user.archived_at ? t.archivedLabel : t.active}
                </dd>
              </div>
              <div><dt className="text-muted">{t.created}</dt><dd className="text-fg">{formatDateTime(user.created_at, language)}</dd></div>
            </section>

            {/* Access control (ban / unban) */}
            <section className="bg-surface border border-rule rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-fg">{t.accessControl}</h2>
              {user.banned_at ? (
                <div className="space-y-2 text-sm">
                  <p className="text-danger-text font-medium">
                    {t.bannedOn(formatDateTime(user.banned_at, language))}
                  </p>
                  {user.ban_reason ? <p className="text-muted">{t.reason(user.ban_reason)}</p> : null}
                  <Button onClick={() => setShowUnbanConfirm(true)}>{t.unbanUser}</Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-muted">{t.banExplain}</p>
                  <input
                    value={banReason}
                    onChange={(e) => setBanReason(e.target.value)}
                    placeholder={t.reasonPlaceholder}
                    maxLength={1024}
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line"
                  />
                  <Button variant="danger" onClick={() => setShowBanConfirm(true)}>{t.banUser}</Button>
                </div>
              )}
            </section>

            {/* Roles */}
            <section className="bg-surface border border-rule rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-fg">{t.systemRoles}</h2>
              <SystemRoleCheckboxes selected={roles} onToggle={toggleRole} disabled={savingRoles} />
              <Button onClick={saveRoles} loading={savingRoles} loadingLabel={t.saving}>{t.saveRoles}</Button>
            </section>

            {/* Accounts */}
            <section className="bg-surface border border-rule rounded-lg p-6 space-y-3">
              <h2 className="text-lg font-semibold text-fg">{t.linkedAccounts}</h2>
              {accounts.length === 0 ? (
                <p className="text-sm text-subtle italic">{t.noAccounts}</p>
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
                        <Button variant="dangerGhost" size="xs" onClick={() => setRemoveAccountId(acc.id)}>{t.remove}</Button>
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
                          <label className="block text-xs font-medium text-body mb-1">{t.providerUrl}</label>
                          <input value={providerUrl} onChange={(e) => setProviderUrl(e.target.value)} placeholder="gitlab.com" className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line" autoFocus />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-body mb-1">{prov.field_label}</label>
                          <input value={accountId} onChange={(e) => setAccountId(e.target.value)} placeholder={prov.placeholder} className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line" />
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => setAddProvider(null)}>{t.cancel}</Button>
                          <Button size="sm" onClick={addAccount} disabled={!providerUrl.trim() || !accountId.trim()} loading={savingAccount} loadingLabel={t.linking}>
                            {t.linkAccount}
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
                <h2 className="text-lg font-semibold text-danger-text">{t.deleteUser}</h2>
                <p className="text-sm text-muted">
                  {accounts.some((a) => a.builtin === true) ? t.deleteExplainSignedIn : t.deleteExplainNever}
                </p>
                <Button variant="danger" onClick={() => setShowDeleteDialog(true)}>{t.deleteButton}</Button>
              </section>
            )}
          </ScrollArea>
        ) : null}

        <ConfirmDialog
          open={showArchiveConfirm}
          title={user?.archived_at ? t.unarchiveTitle : t.archiveTitle}
          message={
            user?.archived_at
              ? t.unarchiveMessage(user?.email)
              : t.archiveMessage(user?.email)
          }
          confirmLabel={user?.archived_at ? t.unarchive : t.archive}
          variant={user?.archived_at ? 'default' : 'danger'}
          onConfirm={toggleArchive}
          onCancel={() => setShowArchiveConfirm(false)}
        />
        <ConfirmDialog
          open={showBanConfirm}
          title={t.banTitle}
          message={t.banMessage(user?.email)}
          confirmLabel={t.banConfirm}
          variant="danger"
          onConfirm={banUser}
          onCancel={() => setShowBanConfirm(false)}
        />
        <ConfirmDialog
          open={showUnbanConfirm}
          title={t.unbanTitle}
          message={t.unbanMessage(user?.email)}
          confirmLabel={t.unbanConfirm}
          onConfirm={unbanUser}
          onCancel={() => setShowUnbanConfirm(false)}
        />
        {showDeleteDialog && user && (
          <ConfirmDeleteDialog
            title={t.deleteUser}
            message={t.deleteMessage(user.email)}
            confirmWord={user.email ?? 'DELETE'}
            blockedReason={
              roles.some((r) => r === '_admin' || r.endsWith('_admin'))
                ? t.blockedAdmin
                : accounts.some((a) => a.builtin === true) && !user.archived_at
                  ? t.blockedArchiveFirst
                  : accounts.some((a) => a.builtin === true) && !isAdmin
                    ? t.blockedAdminOnly
                    : null
            }
            onConfirm={deleteUser}
            onClose={() => setShowDeleteDialog(false)}
          />
        )}
        <ConfirmDialog
          open={removeAccountId !== null}
          title={t.removeTitle}
          message={t.removeMessage}
          confirmLabel={t.remove}
          variant="danger"
          onConfirm={() => removeAccountId && removeAccount(removeAccountId)}
          onCancel={() => setRemoveAccountId(null)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
