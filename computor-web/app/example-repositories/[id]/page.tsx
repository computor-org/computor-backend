'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { ExampleRepositoriesClient } from '@/src/generated/clients/ExampleRepositoriesClient';
import { ExamplesClient } from '@/src/generated/clients/ExamplesClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
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

const COPY = {
  de: {
    forbidden: 'Du hast keinen Zugriff auf Beispiel-Repositories.',
    back: 'Zurück',
    crumb: 'Beispiel-Repositories',
    repository: 'Repository',
    upload: 'Beispiele hochladen',
    edit: 'Bearbeiten',
    delete: 'Löschen',
    loading: 'Wird geladen …',
    examples: 'Beispiele',
    noExamples: 'Noch keine Beispiele.',
    noExamplesUpload: ' Lade ein ZIP-Archiv mit einem oder mehreren Beispielen hoch (jeweils mit einer meta.yaml).',
    deleteTitle: (name: string) => `Repository „${name}“ löschen?`,
    deleteMessage: 'Entfernt das Beispiel-Repository. Es darf vorher keine Beispiele mehr enthalten.',
  },
  en: {
    forbidden: 'You do not have access to example repositories.',
    back: 'Back',
    crumb: 'Example repositories',
    repository: 'Repository',
    upload: 'Upload examples',
    edit: 'Edit',
    delete: 'Delete',
    loading: 'Loading…',
    examples: 'Examples',
    noExamples: 'No examples yet.',
    noExamplesUpload: ' Upload a zip containing one or more examples (each with a meta.yaml).',
    deleteTitle: (name: string) => `Delete repository “${name}”?`,
    deleteMessage: 'Removes the example repository. It must contain no examples first.',
  },
};

export default function ExampleRepositoryDetailPage() {
  const language = useUiLanguage();
  const t = COPY[language];
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
    return <Forbidden message={t.forbidden} backLink="/example-repositories" backText={t.back} />;
  }

  const uploadable = repo?.source_type === 'minio' || repo?.source_type === 's3';

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: t.crumb, href: '/example-repositories' }, { label: repo?.name || t.repository }]}
          title={repo?.name || t.repository}
          subtitle={repo && <span className="font-mono text-sm text-muted">{repo.source_type} · {repo.source_url}</span>}
          actions={
            repo && canManageExamples ? (
              <>
                {uploadable && (
                  <Link href={`/examples/upload?repository=${repo.id}`} className="px-3 py-2 text-sm font-medium text-on-accent bg-accent rounded-lg hover:bg-accent-hover">{t.upload}</Link>
                )}
                <Link href={`/example-repositories/${repo.id}/edit`} className="px-3 py-2 text-sm font-medium text-body border border-rule-strong rounded-lg hover:bg-canvas">{t.edit}</Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-danger-text border border-danger-line rounded-lg hover:bg-danger-wash">{t.delete}</button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : repo ? (
          <ScrollArea>
            {repo.description && (
              <div className="bg-surface border border-rule rounded-lg p-5">
                <p className="text-body">{repo.description}</p>
              </div>
            )}

            <div>
              <h2 className="text-xl font-semibold text-fg mb-3">
                {t.examples} <span className="text-subtle font-normal">({examples.length})</span>
              </h2>
              {examples.length === 0 ? (
                <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
                  {t.noExamples}{uploadable ? t.noExamplesUpload : ''}
                </div>
              ) : (
                <div className="bg-surface border border-rule rounded-lg divide-y divide-rule">
                  {examples.map((ex) => (
                    <Link key={ex.id} href={`/examples/${ex.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-canvas">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-fg truncate">{ex.title || ex.directory}</div>
                        <div className="text-xs text-subtle font-mono truncate">{ex.identifier}</div>
                      </div>
                      <span className="text-faint">›</span>
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
          title={t.deleteTitle(repo.name)}
          message={t.deleteMessage}
          confirmWord={repo.name}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
