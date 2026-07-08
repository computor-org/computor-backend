'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ExampleRepositoriesClient } from '@/src/generated/clients/ExampleRepositoriesClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { ExampleRepositoryGet } from 'types/generated';

const exampleRepositoriesClient = new ExampleRepositoriesClient();

export default function ExampleRepositoryEditPage() {
  const repoId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageExamples: canManage } = usePermissions();

  const [repo, setRepo] = useState<ExampleRepositoryGet | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    let cancelled = false;
    exampleRepositoriesClient
      .getExampleRepositoriesExampleRepositoriesIdGet({ id: repoId })
      .then((r) => {
        if (cancelled) return;
        setRepo(r);
        setName(r.name || '');
        setDescription(r.description || '');
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'An error occurred'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [repoId, authLoading, isAuthenticated, canManage]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await exampleRepositoriesClient.updateExampleRepositoriesExampleRepositoriesIdPatch({ id: repoId, body: { name: name.trim(), description: description.trim() || null } });
      router.push(`/example-repositories/${repoId}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You do not have access to example repositories." />;
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <div className="p-6 text-gray-500">Loading…</div>
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: 'Example Repositories', href: '/example-repositories' },
            { label: repo?.name || 'Repository', href: `/example-repositories/${repoId}` },
            { label: 'Edit' },
          ]}
          title={`Edit ${repo?.name || 'repository'}`}
          error={error}
          submitting={saving}
          disabled={!name.trim()}
          onCancel={() => router.push(`/example-repositories/${repoId}`)}
          onSubmit={save}
        >
          <Field label="Name" required>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Description">
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
          </Field>
          <Field label="Storage (immutable)" hint="Source type and URL are fixed once a repository exists.">
            <input value={`${repo?.source_type ?? ''} · ${repo?.source_url ?? ''}`} readOnly className={`${inputCls} bg-gray-50 text-gray-500`} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
