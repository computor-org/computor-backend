'use client';

import Link from 'next/link';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';

const gitServersClient = new GitServersClient();

const COPY = {
  de: {
    forbidden: 'Zum Verwalten von Git-Servern sind Admin- oder Organisationsverwaltungsrechte nötig.',
    crumb: 'Git-Server',
    subtitle:
      'Das Verzeichnis der Git-Instanzen, an die Kurse gebunden werden können. Verwaltete Instanzen halten ein Dienst-Token für die automatische Bereitstellung von Studierenden-Repositories.',
    register: 'Server registrieren',
    loading: 'Wird geladen …',
    empty:
      'Noch keine Git-Server registriert – registriere einen (z. B. dein Forgejo), um die automatische Bereitstellung zu aktivieren.',
    managed: 'verwaltet',
    tokenSet: 'Token gesetzt',
    noToken: 'kein Token',
  },
  en: {
    forbidden: 'Admin or organization-manager access is required to manage git servers.',
    crumb: 'Git servers',
    subtitle:
      'The registry of git instances courses can bind to. Managed instances hold a service token used for babysat student-repo provisioning.',
    register: 'Register Server',
    loading: 'Loading…',
    empty: 'No git servers registered yet — register one (e.g. your Forgejo) to enable babysat provisioning.',
    managed: 'managed',
    tokenSet: 'token set',
    noToken: 'no token',
  },
};

export default function GitServersPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const { data, loading, error } = useResource(() => gitServersClient.listGitServersEndpointGitServersGet({}), [], { enabled: canManage });
  const servers = data ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.crumb }]}
          title={t.crumb}
          subtitle={t.subtitle}
          actions={
            <Link href="/admin/git-servers/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
              {t.register}
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : servers.length === 0 ? (
          <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
            {t.empty}
          </div>
        ) : (
          <ScrollArea spacing="rows">
            {servers.map((s) => (
              <Link key={s.id} href={`/admin/git-servers/${s.id}`} className="flex items-center justify-between bg-surface border border-rule rounded-lg p-4 hover:border-accent-line hover:shadow-sm transition-all">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-fg truncate">{s.name || s.base_url}</div>
                  <div className="text-xs text-muted">{s.type} · {s.base_url}</div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {s.managed && <Badge color="green">{t.managed}</Badge>}
                  <Badge color={s.has_token ? 'blue' : 'gray'}>{s.has_token ? t.tokenSet : t.noToken}</Badge>
                  <span className="text-faint">›</span>
                </div>
              </Link>
            ))}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
