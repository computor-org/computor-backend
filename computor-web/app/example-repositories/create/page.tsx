'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ExampleRepositoriesClient } from '@/src/generated/clients/ExampleRepositoriesClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';

const exampleRepositoriesClient = new ExampleRepositoriesClient();

const COPY = {
  de: {
    forbidden: 'Du hast keinen Zugriff auf Beispiel-Repositories.',
    createFailed: 'Erstellen fehlgeschlagen',
    crumb: 'Beispiel-Repositories',
    crumbNew: 'Neu',
    title: 'Neues Beispiel-Repository',
    description:
      'Ein Beispiel-Repository ist ein Speicher-Backend für wiederverwendbare Beispielinhalte. Kurse beziehen ihre Aufgaben daraus.',
    submit: 'Erstellen',
    name: 'Name',
    namePlaceholder: 'Kursbeispiele',
    storage: 'Speicher',
    minio: 'MinIO (Upload möglich)',
    s3: 'S3 (Upload möglich)',
    git: 'Git (schreibgeschützt – Synchronisierung per Push)',
    gitUrl: 'Git-URL',
    bucket: 'Bucket (Quell-URL)',
    bucketHint:
      'Das erste Pfadsegment ist der Bucket (Standard: computor-storage). Muss über alle Repositories hinweg eindeutig sein.',
    description2: 'Beschreibung',
  },
  en: {
    forbidden: 'You do not have access to example repositories.',
    createFailed: 'Create failed',
    crumb: 'Example repositories',
    crumbNew: 'New',
    title: 'New example repository',
    description:
      'An example repository is a storage backend that holds reusable example content. Courses draw their assignments from these.',
    submit: 'Create',
    name: 'Name',
    namePlaceholder: 'Course examples',
    storage: 'Storage',
    minio: 'MinIO (uploadable)',
    s3: 'S3 (uploadable)',
    git: 'Git (read-only — synced via push)',
    gitUrl: 'Git URL',
    bucket: 'Bucket (source URL)',
    bucketHint:
      'First path segment is the bucket (default: computor-storage). Must be unique across repositories.',
    description2: 'Description',
  },
};

export default function ExampleRepositoryCreatePage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageExamples: canManage } = usePermissions();

  const [name, setName] = useState('');
  const [sourceType, setSourceType] = useState<'minio' | 's3' | 'git'>('minio');
  const [sourceUrl, setSourceUrl] = useState('computor-storage');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const repo = await exampleRepositoriesClient.createExampleRepositoriesExampleRepositoriesPost({
        body: {
          name: name.trim(),
          description: description.trim() || null,
          source_type: sourceType,
          source_url: sourceUrl.trim(),
        },
      });
      router.push(`/example-repositories/${repo.id}`);
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
        breadcrumbs={[{ label: t.crumb, href: '/example-repositories' }, { label: t.crumbNew }]}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving}
        disabled={!name.trim() || !sourceUrl.trim()}
        submitLabel={t.submit}
        onCancel={() => router.push('/example-repositories')}
        onSubmit={save}
      >
        <Field label={t.name} required>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t.namePlaceholder} className={inputCls} />
        </Field>
        <Field label={t.storage}>
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value as typeof sourceType)} className={inputCls}>
            <option value="minio">{t.minio}</option>
            <option value="s3">{t.s3}</option>
            <option value="git">{t.git}</option>
          </select>
        </Field>
        <Field
          label={sourceType === 'git' ? t.gitUrl : t.bucket}
          required
          hint={sourceType !== 'git' ? t.bucketHint : undefined}
        >
          <input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} className={inputCls} />
        </Field>
        <Field label={t.description2}>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
