'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ExampleRepositoriesClient } from '@/src/generated/clients/ExampleRepositoriesClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';

const exampleRepositoriesClient = new ExampleRepositoriesClient();

const COPY = {
  de: {
    forbidden: 'Du hast keinen Zugriff auf Beispiel-Repositories.',
    saveFailed: 'Speichern fehlgeschlagen',
    crumb: 'Beispiel-Repositories',
    repository: 'Repository',
    edit: 'Bearbeiten',
    editTitle: (name: string) => `${name} bearbeiten`,
    name: 'Name',
    description: 'Beschreibung',
    storage: 'Speicher (unveränderlich)',
    storageHint: 'Quelltyp und URL stehen fest, sobald das Repository existiert.',
  },
  en: {
    forbidden: 'You do not have access to example repositories.',
    saveFailed: 'Save failed',
    crumb: 'Example repositories',
    repository: 'Repository',
    edit: 'Edit',
    editTitle: (name: string) => `Edit ${name}`,
    name: 'Name',
    description: 'Description',
    storage: 'Storage (immutable)',
    storageHint: 'Source type and URL are fixed once a repository exists.',
  },
};

export default function ExampleRepositoryEditPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const repoId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageExamples: canManage } = usePermissions();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: repo, loading, error: loadError } = useResource(
    () => exampleRepositoriesClient.getExampleRepositoriesExampleRepositoriesIdGet({ id: repoId }),
    [repoId],
    { enabled: canManage },
  );

  // Seed the form once repo loads. Adjusting state during render (instead of in
  // an effect) is React's documented way to derive state from changed data: it
  // re-renders before committing, so there is no cascading render.
  const [seeded, setSeeded] = useState(repo);
  if (repo && repo !== seeded) {
    setSeeded(repo);
    setName(repo.name || '');
    setDescription(repo.description || '');
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await exampleRepositoriesClient.updateExampleRepositoriesExampleRepositoriesIdPatch({ id: repoId, body: { name: name.trim(), description: description.trim() || null } });
      router.push(`/example-repositories/${repoId}`);
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
            { label: t.crumb, href: '/example-repositories' },
            { label: repo?.name || t.repository, href: `/example-repositories/${repoId}` },
            { label: t.edit },
          ]}
          title={t.editTitle(repo?.name || (language === 'de' ? 'Repository' : 'repository'))}
          error={loadError ?? saveError}
          submitting={saving}
          disabled={!name.trim()}
          onCancel={() => router.push(`/example-repositories/${repoId}`)}
          onSubmit={save}
        >
          <Field label={t.name} required>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
          </Field>
          <Field label={t.description}>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
          </Field>
          <Field label={t.storage} hint={t.storageHint}>
            <input value={`${repo?.source_type ?? ''} · ${repo?.source_url ?? ''}`} readOnly className={`${inputCls} bg-canvas text-muted`} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
