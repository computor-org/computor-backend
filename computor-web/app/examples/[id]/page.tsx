'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { ExamplesClient } from '@/src/generated/clients/ExamplesClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import type { ExampleVersionList } from 'types/generated';

const examplesClient = new ExamplesClient();

export default function ExampleDetailPage() {
  const exampleId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canViewExamples, canManageExamples } = usePermissions();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data, loading, error } = useResource(
    async () => ({
      example: await examplesClient.getExampleExamplesExampleIdGet({ exampleId }),
      versions: await examplesClient.listVersionsExamplesExampleIdVersionsGet({ exampleId, limit: 200 }).catch(() => [] as ExampleVersionList[]),
    }),
    [exampleId],
    { enabled: canViewExamples },
  );
  const example = data?.example ?? null;
  const versions = data?.versions ?? [];

  async function doDelete() {
    await api.del(`/examples/${exampleId}`);
    router.push('/examples');
  }

  if (!authLoading && isAuthenticated && !canViewExamples) {
    return <Forbidden message="You do not have access to examples." backLink="/examples" backText="Back" />;
  }

  const repoId = example?.example_repository_id;
  const uploadHref = example
    ? `/examples/upload?repository=${repoId ?? ''}&directory=${encodeURIComponent(example.directory)}`
    : '/examples/upload';

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Examples', href: '/examples' }, { label: example?.title || example?.directory || 'Example' }]}
          title={example?.title || example?.directory || 'Example'}
          subtitle={example && <span className="font-mono text-sm text-subtle">{example.identifier}</span>}
          actions={
            example && canManageExamples ? (
              <>
                <Link href={uploadHref} className="px-3 py-2 text-sm font-medium text-on-accent bg-blue-600 rounded-lg hover:bg-blue-700">Upload new version</Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Delete</button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : example ? (
          <ScrollArea>
            <div className="bg-surface border border-rule rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div>
                <dt className="text-muted">Directory</dt>
                <dd className="text-fg font-mono">{example.directory}</dd>
              </div>
              <div>
                <dt className="text-muted">Repository</dt>
                <dd className="text-fg">
                  {repoId ? <Link href={`/example-repositories/${repoId}`} className="text-blue-600 hover:underline">View repository</Link> : '—'}
                </dd>
              </div>
              {example.description && (
                <div className="sm:col-span-2">
                  <dt className="text-muted">Description</dt>
                  <dd className="text-fg">{example.description}</dd>
                </div>
              )}
              {(example.tags || []).length > 0 && (
                <div className="sm:col-span-2">
                  <dt className="text-muted">Tags</dt>
                  <dd className="flex flex-wrap gap-1.5 mt-1">
                    {(example.tags || []).map((t) => (
                      <span key={t} className="px-2 py-0.5 text-xs bg-sunken text-muted rounded">{t}</span>
                    ))}
                  </dd>
                </div>
              )}
            </div>

            <div>
              <h2 className="text-xl font-semibold text-fg mb-3">
                Versions <span className="text-subtle font-normal">({versions.length})</span>
              </h2>
              {versions.length === 0 ? (
                <div className="text-muted border border-dashed border-rule-strong rounded-lg p-6 text-center">No versions.</div>
              ) : (
                <div className="bg-surface border border-rule rounded-lg divide-y">
                  {versions.map((v) => (
                    <div key={v.id} className="flex items-center justify-between px-4 py-3">
                      <div className="font-mono text-sm text-fg">v{v.version_tag}</div>
                      <div className="text-sm text-muted truncate flex-1 px-4">{v.title || ''}</div>
                      <div className="text-xs text-subtle">{v.created_at ? new Date(v.created_at).toLocaleDateString() : ''}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        ) : null}
      </ListPageLayout>

      {confirmDelete && example && (
        <ConfirmDeleteDialog
          title={`Delete example “${example.title || example.directory}”?`}
          message="This permanently deletes the example and all its versions."
          confirmWord={example.directory}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
