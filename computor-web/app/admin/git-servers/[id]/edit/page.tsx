'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls, readOnlyInputCls } from '@/src/components/ui/tokens';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';
import type { GitServerUpdate } from '@/src/generated/types/common';

const gitServersClient = new GitServersClient();

const COPY = {
  de: {
    forbidden: 'Admin- oder Organisationsverwaltungsrechte sind erforderlich.',
    saveFailed: 'Speichern fehlgeschlagen',
    crumb: 'Git-Server',
    server: 'Git-Server',
    edit: 'Bearbeiten',
    editTitle: (name: string) => `${name} bearbeiten`,
    name: 'Name',
    typeUrl: 'Typ und URL (unveränderlich)',
    managed: 'Verwaltet (Computor betreibt ihn und hält ein Dienst-Token)',
    token: 'Dienst-Token',
    tokenHint: (hasToken: boolean) =>
      `Leer lassen, um das aktuelle Token zu behalten${hasToken ? ' (es ist eines gesetzt)' : ''}. Wird verschlüsselt gespeichert und nie zurückgegeben.`,
    tokenPlaceholder: 'leer lassen, um das vorhandene zu behalten',
  },
  en: {
    forbidden: 'Admin or organization-manager access is required.',
    saveFailed: 'Save failed',
    crumb: 'Git servers',
    server: 'Git Server',
    edit: 'Edit',
    editTitle: (name: string) => `Edit ${name}`,
    name: 'Name',
    typeUrl: 'Type & URL (immutable)',
    managed: 'Managed (Computor operates it and holds a service token)',
    token: 'Service token',
    tokenHint: (hasToken: boolean) =>
      `Leave blank to keep the current token${hasToken ? ' (one is set)' : ''}. Stored encrypted, never returned.`,
    tokenPlaceholder: 'leave blank to keep existing',
  },
};

export default function GitServerEditPage() {
  const language = useUiLanguage();
  const t = COPY[language];
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
      setSaveError(e instanceof Error ? e.message : t.saveFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <PageLoading />
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: t.crumb, href: '/admin/git-servers' },
            { label: server?.name || server?.base_url || t.server, href: `/admin/git-servers/${serverId}` },
            { label: t.edit },
          ]}
          title={t.editTitle(server?.name || server?.base_url || (language === 'de' ? 'Git-Server' : 'git server'))}
          error={loadError ?? saveError}
          submitting={saving}
          onCancel={() => router.push(`/admin/git-servers/${serverId}`)}
          onSubmit={save}
        >
          <Field label={t.name}>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
          </Field>
          <Field label={t.typeUrl}>
            <input value={`${server?.type ?? ''} · ${server?.base_url ?? ''}`} readOnly className={readOnlyInputCls} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-body">
            <input type="checkbox" checked={managed} onChange={(e) => setManaged(e.target.checked)} />
            {t.managed}
          </label>
          <Field label={t.token} hint={t.tokenHint(!!server?.has_token)}>
            <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={t.tokenPlaceholder} className={inputCls} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
