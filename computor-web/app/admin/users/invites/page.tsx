'use client';

import { useEffect, useState, useCallback } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Forbidden from '@/src/components/Forbidden';
import Modal from '@/src/components/Modal';
import SystemRoleCheckboxes from '@/src/components/SystemRoleCheckboxes';
import { useSystemRoles } from '@/src/hooks/useSystemRoles';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { InviteLinkClient } from '@/src/generated/clients/InviteLinkClient';
import type { InviteLinkList, InviteLinkCreate } from 'types/generated';

const invitesClient = new InviteLinkClient();

const BASE_URL = typeof window !== 'undefined' ? window.location.origin : '';

function StatusBadge({ invite }: { invite: InviteLinkList }) {
  const now = new Date();
  const expired = new Date(invite.expires_at) < now;
  const revoked = !!invite.revoked_at;
  const exhausted = invite.use_count >= invite.max_uses;

  if (revoked) return <Badge color="red">Revoked</Badge>;
  if (expired) return <Badge color="gray">Expired</Badge>;
  if (exhausted) return <Badge color="gray">Used</Badge>;
  return <Badge color="green">Active</Badge>;
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
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [invites, setInvites] = useState<InviteLinkList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

  const fetchInvites = useCallback(async () => {
    setLoading(true);
    try {
      const data = await invitesClient.list();
      setInvites(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load invites');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !isUserManager) return;
    fetchInvites();
  }, [authLoading, isAuthenticated, isUserManager, fetchInvites]);

  if (authLoading) return <AuthenticatedLayout><div className="p-8 text-gray-500">Loading…</div></AuthenticatedLayout>;
  if (!isAuthenticated || !isUserManager) {
    return <Forbidden message="Requires admin or _user_manager role." backLink="/dashboard" backText="Back to Dashboard" />;
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
      notify('Invite link created', 'success');
      fetchInvites();
    } catch (e) {
      setCreateModal(m => ({ ...m, error: e instanceof Error ? e.message : 'Failed to create invite', saving: false }));
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await invitesClient.delete(id);
      notify('Invite revoked', 'success');
      fetchInvites();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to revoke invite', 'error');
    }
    setRevokeConfirm(null);
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Users', href: '/admin/users' }, { label: 'Invite Links' }]}
          title="Invite Links"
          subtitle="Create one-time links to onboard new users without GitLab PAT"
          actions={
            <button
              onClick={() => setCreateModal(m => ({ ...m, open: true }))}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              + New Invite
            </button>
          }
        />

        {loading ? (
          <ListLoading />
        ) : error ? (
          <ErrorBanner>{error}</ErrorBanner>
        ) : (
          <ScrollPanel>
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Note / Email</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Uses</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expires</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Roles</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invites.map(inv => (
                  <tr key={inv.id}>
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900">{inv.note || <span className="text-gray-400 italic">No note</span>}</div>
                      {inv.email && <div className="text-xs text-gray-500">Restricted to: {inv.email}</div>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{inv.use_count} / {inv.max_uses}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{new Date(inv.expires_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {inv.roles && inv.roles.length > 0
                          ? inv.roles.map(r => (
                              <Badge key={r} color="blue">{roleLabel(r)}</Badge>
                            ))
                          : <span className="text-xs text-gray-400">None</span>
                        }
                      </div>
                    </td>
                    <td className="px-4 py-3"><StatusBadge invite={inv} /></td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => handleCopy(inv.id, inv.token)}
                          className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        >
                          {copiedId === inv.id ? 'Copied!' : 'Copy Link'}
                        </button>
                        {!inv.revoked_at && (
                          <button
                            onClick={() => setRevokeConfirm(inv.id)}
                            className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
                          >
                            Revoke
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {invites.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">No invite links yet. Create one to get started.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </ScrollPanel>
        )}
      </ListPageLayout>

      {/* Create Modal */}
      {createModal.open && (
        <Modal title="New Invite Link" onClose={() => setCreateModal(m => ({ ...m, open: false, error: null }))}>
            <div className="p-6 pt-4">
              {createModal.error && (
                <div className="mb-3"><ErrorBanner>{createModal.error}</ErrorBanner></div>
              )}
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Restrict to email <span className="text-gray-400 font-normal">(optional — leave empty to allow any email)</span>
                  </label>
                  <input
                    type="email"
                    placeholder="student@example.com"
                    value={createModal.email}
                    onChange={e => setCreateModal(m => ({ ...m, email: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Expires in (days)</label>
                    <input
                      type="number"
                      min={1}
                      max={365}
                      value={createModal.expiresInDays}
                      onChange={e => setCreateModal(m => ({ ...m, expiresInDays: parseInt(e.target.value) || 7 }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Max uses</label>
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={createModal.maxUses}
                      onChange={e => setCreateModal(m => ({ ...m, maxUses: parseInt(e.target.value) || 1 }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Note <span className="text-gray-400 font-normal">(optional)</span></label>
                  <input
                    type="text"
                    placeholder="e.g. WS2024 students"
                    value={createModal.note}
                    onChange={e => setCreateModal(m => ({ ...m, note: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">Auto-assign roles on acceptance</label>
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
            <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex justify-end gap-2">
              <button
                onClick={() => setCreateModal(m => ({ ...m, open: false, error: null }))}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={createModal.saving}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {createModal.saving ? 'Creating…' : 'Create Invite'}
              </button>
            </div>
        </Modal>
      )}

      <ConfirmDialog
        open={revokeConfirm !== null}
        title="Revoke Invite?"
        message="This link will immediately stop working."
        confirmLabel="Revoke"
        variant="danger"
        onConfirm={() => revokeConfirm && handleRevoke(revokeConfirm)}
        onCancel={() => setRevokeConfirm(null)}
      />
    </AuthenticatedLayout>
  );
}
