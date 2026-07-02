'use client';

import Link from 'next/link';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import type { GitServerGet } from '@/src/generated/types/common';

export default function GitServersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const { data, loading, error } = useResource(() => api.get<GitServerGet[]>('/git-servers'), [], { enabled: canManage });
  const servers = data ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or organization-manager access is required to manage git servers." />;
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[{ label: 'Git Servers' }]}
          title="Git Servers"
          subtitle="The registry of git instances courses can bind to. Managed instances hold a service token used for babysat student-repo provisioning."
          actions={
            <Link href="/admin/git-servers/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              Register Server
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : servers.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No git servers registered yet — register one (e.g. your Forgejo) to enable babysat provisioning.
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {servers.map((s) => (
              <Link key={s.id} href={`/admin/git-servers/${s.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{s.name || s.base_url}</div>
                  <div className="text-xs text-gray-500">{s.type} · {s.base_url}</div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {s.managed && <Badge color="green">managed</Badge>}
                  <Badge color={s.has_token ? 'blue' : 'gray'}>{s.has_token ? 'token set' : 'no token'}</Badge>
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
