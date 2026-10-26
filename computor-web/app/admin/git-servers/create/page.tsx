'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';

const gitServersClient = new GitServersClient();

type GitServerType = 'forgejo' | 'gitlab';

const COPY = {
  de: {
    forbidden: 'Admin- oder Organisationsverwaltungsrechte sind erforderlich.',
    createFailed: 'Erstellen fehlgeschlagen',
    crumb: 'Git-Server',
    crumbRegister: 'Registrieren',
    title: 'Neuer Git-Server',
    description:
      'Ein Git-Server ist eine Git-Instanz (Forgejo oder GitLab), an die Kurse gebunden werden, um Referenz- und Studierenden-Repositories zu hosten. Bei verwalteten Instanzen kann Computor Studierenden-Repositories automatisch bereitstellen.',
    submit: 'Registrieren',
    type: 'Typ',
    baseUrl: 'Basis-URL',
    name: 'Name',
    namePlaceholder: 'Unser Forgejo',
    managed: 'Verwaltet (Computor betreibt ihn und hält ein Dienst-Token)',
    token: 'Dienst-Token',
    tokenHintManaged: 'Für die automatische Bereitstellung erforderlich. Wird verschlüsselt gespeichert und nie zurückgegeben.',
    tokenHint: 'Wird verschlüsselt gespeichert und nie zurückgegeben.',
    tokenPlaceholder: 'Dienst-Token einfügen',
  },
  en: {
    forbidden: 'Admin or organization-manager access is required.',
    createFailed: 'Create failed',
    crumb: 'Git servers',
    crumbRegister: 'Register',
    title: 'New Git server',
    description:
      'A git server is a Git instance (Forgejo or GitLab) that courses bind to for hosting reference and student repositories. Managed instances let Computor provision student repos automatically.',
    submit: 'Register',
    type: 'Type',
    baseUrl: 'Base URL',
    name: 'Name',
    namePlaceholder: 'Our Forgejo',
    managed: 'Managed (Computor operates it and holds a service token)',
    token: 'Service token',
    tokenHintManaged: 'Needed for babysat provisioning. Stored encrypted, never returned.',
    tokenHint: 'Stored encrypted, never returned.',
    tokenPlaceholder: 'paste a service token',
  },
};

export default function GitServerCreatePage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const [type, setType] = useState<GitServerType>('forgejo');
  const [baseUrl, setBaseUrl] = useState('');
  const [name, setName] = useState('');
  const [managed, setManaged] = useState(true);
  const [token, setToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const server = await gitServersClient.createGitServerEndpointGitServersPost({
        body: {
          type,
          base_url: baseUrl.trim(),
          name: name.trim() || null,
          managed,
          token: token.trim() || null,
        },
      });
      router.push(`/admin/git-servers/${server.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : t.createFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: t.crumb, href: '/admin/git-servers' }, { label: t.crumbRegister }]}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving}
        disabled={!baseUrl.trim()}
        submitLabel={t.submit}
        onCancel={() => router.push('/admin/git-servers')}
        onSubmit={save}
      >
        <Field label={t.type}>
          <select value={type} onChange={(e) => setType(e.target.value as GitServerType)} className={inputCls}>
            <option value="forgejo">forgejo</option>
            <option value="gitlab">gitlab</option>
          </select>
        </Field>
        <Field label={t.baseUrl} required>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:3030" className={inputCls} />
        </Field>
        <Field label={t.name}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t.namePlaceholder} className={inputCls} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-body">
          <input type="checkbox" checked={managed} onChange={(e) => setManaged(e.target.checked)} />
          {t.managed}
        </label>
        <Field label={t.token} hint={managed ? t.tokenHintManaged : t.tokenHint}>
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={t.tokenPlaceholder} className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
