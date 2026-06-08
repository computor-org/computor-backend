'use client';

import { useEffect, useState, useCallback } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import { useAuth } from '@/src/contexts/AuthContext';
import { InviteLinkClient } from '@/src/generated/clients/InviteLinkClient';
import type { InviteLinkList, InviteLinkCreate } from 'types/generated';

const invitesClient = new InviteLinkClient();

const SYSTEM_ROLES = ['_admin', '_user_manager', '_organization_manager', '_workspace_user', '_workspace_maintainer'];

const BASE_URL = typeof window !== 'undefined' ? window.location.origin : '';

function StatusBadge({ invite }: { invite: InviteLinkList }) {
  const now = new Date();
  const expired = new Date(invite.expires_at) < now;
  const revoked = !!invite.revoked_at;
  const exhausted = invite.use_count >= invite.max_uses;

  if (revoked) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">Revoked</span>;
  if (expired) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">Expired</span>;
  if (exhausted) return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">Used</span>;
  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">Active</span>;
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
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [invites, setInvites] = useState<InviteLinkList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [revokeConfirm, setRevokeConfirm] = useState<string | null>(null);

  const [createModal, setCreateModal] = useState<CreateModal>({
    open: false, email: '', maxUses: 1, expiresInDays: 7, roles: [], note: '', saving: false, error: null,
  });

  const isAdmin = user?.role === 'admin';
  const isUserManager = isAdmin || (user?.systemRoles?.includes('_user_manager') ?? false);

  const notify = (message: string, type: 'success' | 'error') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

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
    return (
      <AuthenticatedLayout>
        <div className="p-8 text-red-600 font-medium">Access denied. Requires admin or _user_manager role.</div>
      </AuthenticatedLayout>
    );
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
      <div className="p-6">
        <Breadcrumbs items={[{ label: 'Users', href: '/admin/users' }, { label: 'Invite Links' }]} />
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Invite Links</h1>
            <p className="text-sm text-gray-500 mt-1">Create one-time links to onboard new users without GitLab PAT</p>
          </div>
          <button
            onClick={() => setCreateModal(m => ({ ...m, open: true }))}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            + New Invite
          </button>
        </div>

        {notification && (
          <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${notification.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
            {notification.message}
          </div>
        )}

        {loading ? (
          <div className="text-gray-500 py-8 text-center">Loading…</div>
        ) : error ? (
          <div className="text-red-600 py-8 text-center">{error}</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
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
                              <span key={r} className="px-1.5 py-0.5 rounded text-xs bg-blue-50 text-blue-700">{r}</span>
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
          </div>
        )}
      </div>

      {/* Create Modal */}
      {createModal.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">New Invite Link</h2>
              {createModal.error && (
                <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{createModal.error}</div>
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
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
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
          </div>
        </div>
      )}

      {/* Revoke Confirm */}
      {revokeConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Revoke Invite?</h2>
            <p className="text-sm text-gray-600 mb-4">This link will immediately stop working.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setRevokeConfirm(null)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
              <button onClick={() => handleRevoke(revokeConfirm)} className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700">Revoke</button>
            </div>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}
