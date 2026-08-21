'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';

const gitServersClient = new GitServersClient();

export default function GitServerDetailPage() {
  const serverId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: server, loading, error } = useResource(
    () => gitServersClient.getGitServerEndpointGitServersServerIdGet({ serverId }),
    [serverId],
    { enabled: canManage },
  );

  async function doDelete() {
    await gitServersClient.deleteGitServerEndpointGitServersServerIdDelete({ serverId });
    router.push('/admin/git-servers');
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or organization-manager access is required." backLink="/admin/git-servers" backText="Back" />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: 'Git servers', href: '/admin/git-servers' }, { label: server?.name || server?.base_url || 'Git Server' }]}
          title={server?.name || server?.base_url || 'Git Server'}
          subtitle={server && <span className="font-mono text-sm text-muted">{server.type} · {server.base_url}</span>}
          actions={
            server ? (
              <>
                <Link href={`/admin/git-servers/${server.id}/edit`} className="px-3 py-2 text-sm font-medium text-body border border-rule-strong rounded-lg hover:bg-canvas">Edit</Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-danger-text border border-danger-line rounded-lg hover:bg-danger-wash">Delete</button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : server ? (
          <ScrollArea>
            <div className="bg-surface border border-rule rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div><dt className="text-muted">Managed</dt><dd className="text-fg">{server.managed ? 'Yes — Computor operates it' : 'No (external)'}</dd></div>
              <div><dt className="text-muted">Service token</dt><dd className="text-fg">{server.has_token ? 'Set (encrypted)' : 'None'}</dd></div>
              {server.created_at && (
                <div><dt className="text-muted">Registered</dt><dd className="text-fg">{new Date(server.created_at).toLocaleString()}</dd></div>
              )}
            </div>
            {server.managed && (
              <p className="text-xs text-subtle">
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
