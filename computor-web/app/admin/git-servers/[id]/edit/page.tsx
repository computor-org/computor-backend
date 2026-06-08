'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { GitServerGet } from '@/src/generated/types/common';

export default function GitServerEditPage() {
  const serverId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [server, setServer] = useState<GitServerGet | null>(null);
  const [name, setName] = useState('');
  const [managed, setManaged] = useState(false);
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`${API_BASE_URL}/git-servers/${serverId}`);
        if (!res.ok) throw new Error('Failed to load git server');
        const s: GitServerGet = await res.json();
        if (cancelled) return;
        setServer(s);
        setName(s.name || '');
        setManaged(!!s.managed);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'An error occurred');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [serverId, authLoading, isAuthenticated, canManage]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      // Only send token when the field was touched: undefined keeps the existing
      // token; an empty string would clear it on the backend.
      const body: Record<string, unknown> = { name: name.trim() || null, managed };
      if (token.length > 0) body.token = token.trim();
      const res = await apiFetch(`${API_BASE_URL}/git-servers/${serverId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.text()) || `Save failed (${res.status})`);
      router.push(`/admin/git-servers/${serverId}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="Admin or organization-manager access is required." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <div className="p-6 text-gray-500">Loading…</div>
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: 'Git Servers', href: '/admin/git-servers' },
            { label: server?.name || server?.base_url || 'Git Server', href: `/admin/git-servers/${serverId}` },
            { label: 'Edit' },
          ]}
          title={`Edit ${server?.name || server?.base_url || 'git server'}`}
          error={error}
          submitting={saving}
          onCancel={() => router.push(`/admin/git-servers/${serverId}`)}
          onSubmit={save}
        >
          <Field label="Name">
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Type & URL (immutable)">
            <input value={`${server?.type ?? ''} · ${server?.base_url ?? ''}`} readOnly className={`${inputCls} bg-gray-50 text-gray-500`} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={managed} onChange={(e) => setManaged(e.target.checked)} />
            Managed (Computor operates it and holds a service token)
          </label>
          <Field label="Service token" hint={`Leave blank to keep the current token${server?.has_token ? ' (one is set)' : ''}. Stored encrypted, never returned.`}>
            <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="leave blank to keep existing" className={inputCls} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
