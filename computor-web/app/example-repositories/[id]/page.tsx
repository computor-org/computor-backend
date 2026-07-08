'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { ExampleRepositoriesClient } from '@/src/generated/clients/ExampleRepositoriesClient';
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
import type { ExampleList } from 'types/generated';

const exampleRepositoriesClient = new ExampleRepositoriesClient();
const examplesClient = new ExamplesClient();

export default function ExampleRepositoryDetailPage() {
  const repoId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canViewExamples, canManageExamples } = usePermissions();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data, loading, error } = useResource(
    async () => ({
      repo: await exampleRepositoriesClient.getExampleRepositoriesExampleRepositoriesIdGet({ id: repoId }),
      examples: await examplesClient.listExamplesExamplesGet({ repositoryId: repoId, limit: 500 }).catch(() => [] as ExampleList[]),
    }),
    [repoId],
    { enabled: canViewExamples },
  );
  const repo = data?.repo ?? null;
  const examples = data?.examples ?? [];

  async function doDelete() {
    await exampleRepositoriesClient.deleteExampleRepositoriesExampleRepositoriesIdDelete({ id: repoId });
    router.push('/example-repositories');
  }

  if (!authLoading && isAuthenticated && !canViewExamples) {
    return <Forbidden message="You do not have access to example repositories." backLink="/example-repositories" backText="Back" />;
  }

  const uploadable = repo?.source_type === 'minio' || repo?.source_type === 's3';

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Example Repositories', href: '/example-repositories' }, { label: repo?.name || 'Repository' }]}
          title={repo?.name || 'Repository'}
          subtitle={repo && <span className="font-mono text-sm text-gray-500">{repo.source_type} · {repo.source_url}</span>}
          actions={
            repo && canManageExamples ? (
              <>
                {uploadable && (
                  <Link href={`/examples/upload?repository=${repo.id}`} className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">Upload examples</Link>
                )}
                <Link href={`/example-repositories/${repo.id}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">Edit</Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Delete</button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : repo ? (
          <ScrollArea className="space-y-6">
            {repo.description && (
              <div className="bg-white border border-gray-200 rounded-lg p-5">
                <p className="text-gray-700">{repo.description}</p>
              </div>
            )}

            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">
                Examples <span className="text-gray-400 font-normal">({examples.length})</span>
              </h2>
              {examples.length === 0 ? (
                <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
                  No examples yet.{uploadable ? ' Upload a zip containing one or more examples (each with a meta.yaml).' : ''}
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-lg divide-y">
                  {examples.map((ex) => (
                    <Link key={ex.id} href={`/examples/${ex.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">{ex.title || ex.directory}</div>
                        <div className="text-xs text-gray-400 font-mono truncate">{ex.identifier}</div>
                      </div>
                      <span className="text-gray-300">›</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        ) : null}
      </ListPageLayout>

      {confirmDelete && repo && (
        <ConfirmDeleteDialog
          title={`Delete repository “${repo.name}”?`}
          message="Removes the example repository. It must contain no examples first."
          confirmWord={repo.name}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
