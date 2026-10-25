'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';
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

const COPY = {
  de: {
    forbidden: 'Admin- oder Organisationsverwaltungsrechte sind erforderlich.',
    back: 'Zurück',
    crumb: 'Git-Server',
    server: 'Git-Server',
    edit: 'Bearbeiten',
    delete: 'Löschen',
    loading: 'Wird geladen …',
    managed: 'Verwaltet',
    managedYes: 'Ja – Computor betreibt ihn',
    managedNo: 'Nein (extern)',
    token: 'Dienst-Token',
    tokenSet: 'Gesetzt (verschlüsselt)',
    tokenNone: 'Keins',
    registered: 'Registriert',
    managedNote:
      'Verwaltete Forgejo-Instanzen werden beim Start automatisch registriert. Das Entfernen ist gesperrt, solange noch eine Kursbindung darauf verweist.',
    deleteTitle: (name: string) => `Git-Server „${name}“ löschen?`,
    deleteMessage:
      'Entfernt diesen Server aus dem Verzeichnis. Gesperrt, solange noch eine Kursbindung darauf verweist.',
  },
  en: {
    forbidden: 'Admin or organization-manager access is required.',
    back: 'Back',
    crumb: 'Git servers',
    server: 'Git Server',
    edit: 'Edit',
    delete: 'Delete',
    loading: 'Loading…',
    managed: 'Managed',
    managedYes: 'Yes — Computor operates it',
    managedNo: 'No (external)',
    token: 'Service token',
    tokenSet: 'Set (encrypted)',
    tokenNone: 'None',
    registered: 'Registered',
    managedNote:
      'Managed Forgejo instances are auto-registered at startup. Removing one is blocked while any course binding still references it.',
    deleteTitle: (name: string) => `Delete git server “${name}”?`,
    deleteMessage: 'Removes this server from the registry. Blocked while any course binding still references it.',
  },
};

export default function GitServerDetailPage() {
  const language = useUiLanguage();
  const t = COPY[language];
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
    return <Forbidden message={t.forbidden} backLink="/admin/git-servers" backText={t.back} />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: t.crumb, href: '/admin/git-servers' }, { label: server?.name || server?.base_url || t.server }]}
          title={server?.name || server?.base_url || t.server}
          subtitle={server && <span className="font-mono text-sm text-muted">{server.type} · {server.base_url}</span>}
          actions={
            server ? (
              <>
                <Link href={`/admin/git-servers/${server.id}/edit`} className="px-3 py-2 text-sm font-medium text-body border border-rule-strong rounded-lg hover:bg-canvas">{t.edit}</Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-danger-text border border-danger-line rounded-lg hover:bg-danger-wash">{t.delete}</button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : server ? (
          <ScrollArea>
            <div className="bg-surface border border-rule rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div><dt className="text-muted">{t.managed}</dt><dd className="text-fg">{server.managed ? t.managedYes : t.managedNo}</dd></div>
              <div><dt className="text-muted">{t.token}</dt><dd className="text-fg">{server.has_token ? t.tokenSet : t.tokenNone}</dd></div>
              {server.created_at && (
                <div><dt className="text-muted">{t.registered}</dt><dd className="text-fg">{formatDateTime(server.created_at, language)}</dd></div>
              )}
            </div>
            {server.managed && (
              <p className="text-xs text-subtle">
                {t.managedNote}
              </p>
            )}
          </ScrollArea>
        ) : null}
      </ListPageLayout>

      {confirmDelete && server && (
        <ConfirmDeleteDialog
          title={t.deleteTitle(server.name || server.base_url)}
          message={t.deleteMessage}
          confirmWord={server.name || server.base_url}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
