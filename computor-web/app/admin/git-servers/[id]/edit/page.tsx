'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';
import type { GitServerUpdate } from '@/src/generated/types/common';

const gitServersClient = new GitServersClient();

export default function GitServerEditPage() {
  const serverId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const [name, setName] = useState('');
  const [managed, setManaged] = useState(false);
  const [token, setToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: server, loading, error: loadError } = useResource(
    () => gitServersClient.getGitServerEndpointGitServersServerIdGet({ serverId }),
    [serverId],
    { enabled: canManage },
  );

  // Seed the form once server loads. Adjusting state during render (instead of in
  // an effect) is React's documented way to derive state from changed data: it
  // re-renders before committing, so there is no cascading render.
  const [seeded, setSeeded] = useState(server);
  if (server && server !== seeded) {
    setSeeded(server);
    setName(server.name || '');
    setManaged(!!server.managed);
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      // Only send token when touched: undefined keeps the existing one; "" would clear it.
      const body: GitServerUpdate = { name: name.trim() || null, managed };
      if (token.length > 0) body.token = token.trim();
      await gitServersClient.updateGitServerEndpointGitServersServerIdPatch({ serverId, body });
      router.push(`/admin/git-servers/${serverId}`);
    } catch (e) {
      setSaving(false);
      setSaveError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or organization-manager access is required." />;
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <PageLoading />
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: 'Git Servers', href: '/admin/git-servers' },
            { label: server?.name || server?.base_url || 'Git Server', href: `/admin/git-servers/${serverId}` },
            { label: 'Edit' },
          ]}
          title={`Edit ${server?.name || server?.base_url || 'git server'}`}
          error={loadError ?? saveError}
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
