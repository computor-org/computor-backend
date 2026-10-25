'use client';

import { useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading, PageLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Forbidden from '@/src/components/Forbidden';
import Modal from '@/src/components/Modal';
import SystemRoleCheckboxes from '@/src/components/SystemRoleCheckboxes';
import { useSystemRoles } from '@/src/hooks/useSystemRoles';
import { useResource } from '@/src/hooks/useResource';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { InviteLinkClient } from '@/src/generated/clients/InviteLinkClient';
import type { InviteLinkList, InviteLinkCreate } from 'types/generated';
import { Table, Thead, Tbody, Th } from '@/src/components/ui/Table';
import Button from '@/src/components/ui/Button';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDate } from '@/src/utils/locale';

const invitesClient = new InviteLinkClient();

const BASE_URL = typeof window !== 'undefined' ? window.location.origin : '';

const COPY = {
  de: {
    revoked: 'Widerrufen',
    expired: 'Abgelaufen',
    used: 'Verbraucht',
    active: 'Aktiv',
    forbidden: 'Erfordert die Rolle admin oder _user_manager.',
    backToDashboard: 'Zurück zur Übersicht',
    created: 'Einladungslink erstellt',
    createFailed: 'Einladung konnte nicht erstellt werden',
    revokedToast: 'Einladung widerrufen',
    revokeFailed: 'Einladung konnte nicht widerrufen werden',
    users: 'Benutzer',
    title: 'Einladungslinks',
    subtitle: 'Erstelle Links, über die Personen ein Passwort festlegen und sich anmelden können. Es werden keine E-Mails versendet, kopiere jeden Link und gib ihn selbst weiter.',
    newInvite: '+ Neue Einladung',
    noteEmail: 'Notiz / E-Mail',
    uses: 'Verwendungen',
    expires: 'Läuft ab',
    roles: 'Rollen',
    status: 'Status',
    actions: 'Aktionen',
    noNote: 'Keine Notiz',
    restrictedTo: (email: string) => `Beschränkt auf: ${email}`,
    none: 'Keine',
    copied: 'Kopiert!',
    copyLink: 'Link kopieren',
    revoke: 'Widerrufen',
    empty: 'Noch keine Einladungslinks. Erstelle den ersten.',
    modalTitle: 'Neuer Einladungslink',
    restrictEmail: 'Auf E-Mail-Adresse beschränken',
    restrictEmailHint: '(optional, leer lassen, um jede Adresse zuzulassen)',
    expiresIn: 'Läuft ab in (Tagen)',
    maxUses: 'Maximale Verwendungen',
    note: 'Notiz',
    optional: '(optional)',
    notePlaceholder: 'z. B. Studierende WS2024',
    autoRoles: 'Rollen bei Annahme automatisch zuweisen',
    cancel: 'Abbrechen',
    creating: 'Wird erstellt…',
    createInvite: 'Einladung erstellen',
    revokeTitle: 'Einladung widerrufen?',
    revokeMessage: 'Dieser Link funktioniert sofort nicht mehr.',
  },
  en: {
    revoked: 'Revoked',
    expired: 'Expired',
    used: 'Used',
    active: 'Active',
    forbidden: 'Requires admin or _user_manager role.',
    backToDashboard: 'Back to Dashboard',
    created: 'Invite link created',
    createFailed: 'Failed to create invite',
    revokedToast: 'Invite revoked',
    revokeFailed: 'Failed to revoke invite',
    users: 'Users',
    title: 'Invite links',
    subtitle: 'Create links that let people set a password and sign in. Nothing is emailed — copy each link and share it yourself.',
    newInvite: '+ New Invite',
    noteEmail: 'Note / Email',
    uses: 'Uses',
    expires: 'Expires',
    roles: 'Roles',
    status: 'Status',
    actions: 'Actions',
    noNote: 'No note',
    restrictedTo: (email: string) => `Restricted to: ${email}`,
    none: 'None',
    copied: 'Copied!',
    copyLink: 'Copy Link',
    revoke: 'Revoke',
    empty: 'No invite links yet. Create one to get started.',
    modalTitle: 'New invite link',
    restrictEmail: 'Restrict to email',
    restrictEmailHint: '(optional — leave empty to allow any email)',
    expiresIn: 'Expires in (days)',
    maxUses: 'Max uses',
    note: 'Note',
    optional: '(optional)',
    notePlaceholder: 'e.g. WS2024 students',
    autoRoles: 'Auto-assign roles on acceptance',
    cancel: 'Cancel',
    creating: 'Creating…',
    createInvite: 'Create Invite',
    revokeTitle: 'Revoke Invite?',
    revokeMessage: 'This link will immediately stop working.',
  },
};

function StatusBadge({ invite }: { invite: InviteLinkList }) {
  const t = COPY[useUiLanguage()];
  const now = new Date();
  const expired = new Date(invite.expires_at) < now;
  const revoked = !!invite.revoked_at;
  const exhausted = invite.use_count >= invite.max_uses;

  if (revoked) return <Badge tone="error">{t.revoked}</Badge>;
  if (expired) return <Badge tone="muted">{t.expired}</Badge>;
  if (exhausted) return <Badge tone="muted">{t.used}</Badge>;
  return <Badge tone="success">{t.active}</Badge>;
}

interface CreateModal {
  open: boolean;
  email: string;
  maxUses: number;
  expiresInDays: number;
  roles: string[];
  note: string;
  saving: boolean;
  error: string | null;
}

export default function InvitesPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [revokeConfirm, setRevokeConfirm] = useState<string | null>(null);

  const [createModal, setCreateModal] = useState<CreateModal>({
    open: false, email: '', maxUses: 1, expiresInDays: 7, roles: [], note: '', saving: false, error: null,
  });

  const { roles: systemRoles } = useSystemRoles();
  const roleLabel = (id: string) => systemRoles.find(r => r.id === id)?.title ?? id;

  // Backend-refreshed scopes (via usePermissions) instead of the cached
  // session's role string, which can go stale between logins.
  const { isUserManager } = usePermissions();

  const notify = useNotify();

  const { data, loading, error, reload } = useResource(
    () => invitesClient.list(),
    [],
    { enabled: isUserManager },
  );
  const invites = data ?? [];

  if (authLoading) return <AuthenticatedLayout><PageLoading width="wide" /></AuthenticatedLayout>;
  if (!isAuthenticated || !isUserManager) {
    return <Forbidden message={t.forbidden} backLink="/dashboard" backText={t.backToDashboard} />;
  }

  const inviteUrl = (token: string) => `${BASE_URL}/invite/${token}`;

  const handleCopy = (id: string, token: string) => {
    navigator.clipboard.writeText(inviteUrl(token)).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const handleCreate = async () => {
    setCreateModal(m => ({ ...m, saving: true, error: null }));
    try {
      const payload: InviteLinkCreate = {
        email: createModal.email.trim() || undefined,
        max_uses: createModal.maxUses,
        expires_in_days: createModal.expiresInDays,
        roles: createModal.roles,
        note: createModal.note.trim() || undefined,
      };
      await invitesClient.create(payload);
      setCreateModal(m => ({ ...m, open: false, email: '', maxUses: 1, expiresInDays: 7, roles: [], note: '', saving: false }));
      notify(t.created, 'success');
      reload();
    } catch (e) {
      setCreateModal(m => ({ ...m, error: e instanceof Error ? e.message : t.createFailed, saving: false }));
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await invitesClient.delete(id);
      notify(t.revokedToast, 'success');
      reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.revokeFailed, 'error');
    }
    setRevokeConfirm(null);
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.users, href: '/admin/users' }, { label: t.title }]}
          title={t.title}
          subtitle={t.subtitle}
          actions={
            <Button onClick={() => setCreateModal(m => ({ ...m, open: true }))}>
              {t.newInvite}
            </Button>
          }
        />

        {loading ? (
          <ListLoading />
        ) : error ? (
          <ErrorBanner>{error}</ErrorBanner>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <tr>
                  <Th>{t.noteEmail}</Th>
                  <Th>{t.uses}</Th>
                  <Th>{t.expires}</Th>
                  <Th>{t.roles}</Th>
                  <Th>{t.status}</Th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-muted uppercase tracking-wider">{t.actions}</th>
                </tr>
              </Thead>
              <Tbody>
                {invites.map(inv => (
                  <tr key={inv.id}>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-fg">{inv.note || <span className="text-subtle italic">{t.noNote}</span>}</div>
                      {inv.email && <div className="text-xs text-muted">{t.restrictedTo(inv.email)}</div>}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted">{inv.use_count} / {inv.max_uses}</td>
                    <td className="px-4 py-3 text-sm text-muted">{formatDate(inv.expires_at, language)}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {inv.roles && inv.roles.length > 0
                          ? inv.roles.map(r => (
                              <Badge key={r} tone="info">{roleLabel(r)}</Badge>
                            ))
                          : <span className="text-xs text-subtle">{t.none}</span>
                        }
                      </div>
                    </td>
                    <td className="px-4 py-3"><StatusBadge invite={inv} /></td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="accentGhost" size="xs" onClick={() => handleCopy(inv.id, inv.token)}>
                          {copiedId === inv.id ? t.copied : t.copyLink}
                        </Button>
                        {!inv.revoked_at && (
                          <Button variant="dangerGhost" size="xs" onClick={() => setRevokeConfirm(inv.id)}>
                            {t.revoke}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {invites.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted">{t.empty}</td>
                  </tr>
                )}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}
      </ListPageLayout>

      {/* Create Modal */}
      {createModal.open && (
        <Modal title={t.modalTitle} onClose={() => setCreateModal(m => ({ ...m, open: false, error: null }))}>
            <div className="p-6 pt-4">
              {createModal.error && (
                <div className="mb-3"><ErrorBanner>{createModal.error}</ErrorBanner></div>
              )}
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-body mb-1">
                    {t.restrictEmail} <span className="text-subtle font-normal">{t.restrictEmailHint}</span>
                  </label>
                  <input
                    type="email"
                    placeholder="student@example.com"
                    value={createModal.email}
                    onChange={e => setCreateModal(m => ({ ...m, email: e.target.value }))}
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-body mb-1">{t.expiresIn}</label>
                    <input
                      type="number"
                      min={1}
                      max={365}
                      value={createModal.expiresInDays}
                      onChange={e => setCreateModal(m => ({ ...m, expiresInDays: parseInt(e.target.value) || 7 }))}
                      className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-body mb-1">{t.maxUses}</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={createModal.maxUses}
                      onChange={e => setCreateModal(m => ({ ...m, maxUses: parseInt(e.target.value) || 1 }))}
                      className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-body mb-1">{t.note} <span className="text-subtle font-normal">{t.optional}</span></label>
                  <input
                    type="text"
                    placeholder={t.notePlaceholder}
                    value={createModal.note}
                    onChange={e => setCreateModal(m => ({ ...m, note: e.target.value }))}
                    className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-body mb-2">{t.autoRoles}</label>
                  <SystemRoleCheckboxes
                    selected={createModal.roles}
                    onToggle={roleId => setCreateModal(m => ({
                      ...m,
                      roles: m.roles.includes(roleId) ? m.roles.filter(x => x !== roleId) : [...m.roles, roleId],
                    }))}
                  />
                </div>
              </div>
            </div>
            <div className="px-6 py-4 bg-canvas rounded-b-lg flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setCreateModal(m => ({ ...m, open: false, error: null }))}>
                {t.cancel}
              </Button>
              <Button onClick={handleCreate} loading={createModal.saving} loadingLabel={t.creating}>
                {t.createInvite}
              </Button>
            </div>
        </Modal>
      )}

      <ConfirmDialog
        open={revokeConfirm !== null}
        title={t.revokeTitle}
        message={t.revokeMessage}
        confirmLabel={t.revoke}
        variant="danger"
        onConfirm={() => revokeConfirm && handleRevoke(revokeConfirm)}
        onCancel={() => setRevokeConfirm(null)}
      />
    </AuthenticatedLayout>
  );
}
