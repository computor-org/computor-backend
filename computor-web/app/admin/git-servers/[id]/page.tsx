'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import type { GitServerGet } from '@/src/generated/types/common';

export default function GitServerDetailPage() {
  const serverId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: server, loading, error } = useResource(
    () => api.get<GitServerGet>(`/git-servers/${serverId}`),
    [serverId],
    { enabled: canManage },
  );

  async function doDelete() {
    await api.del(`/git-servers/${serverId}`);
    router.push('/admin/git-servers');
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or organization-manager access is required." backLink="/admin/git-servers" backText="Back" />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Git Servers', href: '/admin/git-servers' }, { label: server?.name || server?.base_url || 'Git Server' }]}
          title={server?.name || server?.base_url || 'Git Server'}
          subtitle={server && <span className="font-mono text-sm text-gray-500">{server.type} · {server.base_url}</span>}
          actions={
            server ? (
              <>
                <Link href={`/admin/git-servers/${server.id}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">Edit</Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Delete</button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : server ? (
          <ScrollArea className="space-y-6">
            <div className="bg-white border border-gray-200 rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div><dt className="text-gray-500">Managed</dt><dd className="text-gray-900">{server.managed ? 'Yes — Computor operates it' : 'No (external)'}</dd></div>
              <div><dt className="text-gray-500">Service token</dt><dd className="text-gray-900">{server.has_token ? 'Set (encrypted)' : 'None'}</dd></div>
              {server.created_at && (
                <div><dt className="text-gray-500">Registered</dt><dd className="text-gray-900">{new Date(server.created_at).toLocaleString()}</dd></div>
              )}
            </div>
            {server.managed && (
              <p className="text-xs text-gray-400">
                Managed Forgejo instances are auto-registered at startup. Removing one is blocked while any course binding still references it.
              </p>
            )}
          </ScrollArea>
        ) : null}
      </ListPageLayout>

      {confirmDelete && server && (
        <ConfirmDeleteDialog
          title={`Delete git server “${server.name || server.base_url}”?`}
          message="Removes this server from the registry. Blocked while any course binding still references it."
          confirmWord={server.name || server.base_url}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
