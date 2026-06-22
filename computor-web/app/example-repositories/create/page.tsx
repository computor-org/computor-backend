'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { ExampleRepositoryGet } from 'types/generated';

export default function ExampleRepositoryCreatePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

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
      const repo = await api.post<ExampleRepositoryGet>('/example-repositories', {
        name: name.trim(),
        description: description.trim() || null,
        source_type: sourceType,
        source_url: sourceUrl.trim(),
      });
      router.push(`/example-repositories/${repo.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You do not have access to example repositories." />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Example Repositories', href: '/example-repositories' }, { label: 'New' }]}
        title="New example repository"
        description="An example repository is a storage backend that holds reusable example content. Courses draw their assignments from these."
        error={error}
        submitting={saving}
        disabled={!name.trim() || !sourceUrl.trim()}
        submitLabel="Create"
        onCancel={() => router.push('/example-repositories')}
        onSubmit={save}
      >
        <Field label="Name" required>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Course examples" className={inputCls} />
        </Field>
        <Field label="Storage">
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value as typeof sourceType)} className={inputCls}>
            <option value="minio">MinIO (uploadable)</option>
            <option value="s3">S3 (uploadable)</option>
            <option value="git">Git (read-only — synced via push)</option>
          </select>
        </Field>
        <Field
          label={sourceType === 'git' ? 'Git URL' : 'Bucket (source URL)'}
          required
          hint={sourceType !== 'git' ? 'First path segment is the bucket (default: computor-storage). Must be unique across repositories.' : undefined}
        >
          <input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} className={inputCls} />
        </Field>
        <Field label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
