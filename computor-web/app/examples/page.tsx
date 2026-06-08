'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import type { ExampleList, ExampleRepositoryList } from 'types/generated';

export default function ExamplesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();
  const [repoFilter, setRepoFilter] = useState('');

  const { data, loading, error } = useResource(
    async () => ({
      examples: await api.get<ExampleList[]>('/examples?limit=1000'),
      repos: await api.get<ExampleRepositoryList[]>('/example-repositories?limit=200').catch(() => [] as ExampleRepositoryList[]),
    }),
    [],
    { enabled: canManage },
  );
  const examples = data?.examples ?? [];
  const repos = data?.repos ?? [];

  const repoName = useMemo(() => {
    const m: Record<string, string> = {};
    for (const r of repos) m[r.id] = r.name;
    return m;
  }, [repos]);
  const visible = repoFilter ? examples.filter((e) => e.example_repository_id === repoFilter) : examples;

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You do not have access to examples." />;
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[{ label: 'Examples' }]}
          title="Examples"
          subtitle={
            <>Reusable assignment content. <Link href="/example-repositories" className="text-blue-600 hover:underline">Manage repositories</Link>.</>
          }
          actions={
            <>
              <select value={repoFilter} onChange={(e) => setRepoFilter(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
                <option value="">All repositories</option>
                {repos.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
              <Link href="/examples/upload" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 whitespace-nowrap">Upload examples</Link>
            </>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : visible.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            {examples.length === 0 ? 'No examples yet. Upload a zip of one or more examples to get started.' : 'No examples in this repository.'}
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {visible.map((ex) => (
              <Link key={ex.id} href={`/examples/${ex.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{ex.title || ex.directory}</div>
                  <div className="text-xs text-gray-400 font-mono truncate">{ex.identifier}</div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {(ex.tags || []).slice(0, 2).map((t) => (
                    <span key={t} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{t}</span>
                  ))}
                  <span className="text-xs text-gray-400">{repoName[ex.example_repository_id] || ''}</span>
                  <span className="text-gray-300">›</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
