'use client';

import Link from 'next/link';
import { ExampleRepositoriesClient } from '@/src/generated/clients/ExampleRepositoriesClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import Badge from '@/src/components/Badge';

const exampleRepositoriesClient = new ExampleRepositoriesClient();

const COPY = {
  de: {
    forbidden: 'Du hast keinen Zugriff auf Beispiel-Repositories.',
    title: 'Beispiel-Repositories',
    subtitle: 'Speicher-Backends, die Beispiele enthalten. Lade Beispiele in ein MinIO-Repository hoch.',
    newRepo: 'Neues Repository',
    loading: 'Wird geladen …',
    empty: 'Noch keine Beispiel-Repositories. Erstelle ein MinIO-Repository, um Beispiele hochzuladen.',
  },
  en: {
    forbidden: 'You do not have access to example repositories.',
    title: 'Example repositories',
    subtitle: 'Storage backends that hold examples. Upload examples into a MinIO repository.',
    newRepo: 'New repository',
    loading: 'Loading…',
    empty: 'No example repositories yet. Create a MinIO repository to upload examples into.',
  },
};

export default function ExampleRepositoriesPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canViewExamples, canManageExamples } = usePermissions();

  const { data, loading, error } = useResource(() => exampleRepositoriesClient.listExampleRepositoriesExampleRepositoriesGet({ limit: 200 }), [], { enabled: canViewExamples });
  const repos = data ?? [];

  if (!authLoading && isAuthenticated && !canViewExamples) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.title }]}
          title={t.title}
          subtitle={t.subtitle}
          actions={
            canManageExamples ? (
              <Link href="/example-repositories/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
                {t.newRepo}
              </Link>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : repos.length === 0 ? (
          <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
            {t.empty}
          </div>
        ) : (
          <ScrollArea spacing="none" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 content-start">
            {repos.map((r) => {
              const uploadable = r.source_type === 'minio' || r.source_type === 's3';
              return (
                <Link key={r.id} href={`/example-repositories/${r.id}`} className="bg-surface border border-rule rounded-lg p-5 hover:shadow-md transition-all">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-lg font-semibold text-fg truncate">{r.name}</h3>
                    <Badge color={uploadable ? 'green' : 'gray'} className="shrink-0">
                      {r.source_type}
                    </Badge>
                  </div>
                  {r.description && <p className="mt-1 text-sm text-muted line-clamp-2">{r.description}</p>}
                  <p className="mt-3 text-xs text-subtle font-mono truncate">{r.source_url}</p>
                </Link>
              );
            })}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
