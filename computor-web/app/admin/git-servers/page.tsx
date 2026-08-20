'use client';

import Link from 'next/link';
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

export default function GitServersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const { data, loading, error } = useResource(() => gitServersClient.listGitServersEndpointGitServersGet({}), [], { enabled: canManage });
  const servers = data ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or organization-manager access is required to manage git servers." />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Git servers' }]}
          title="Git servers"
          subtitle="The registry of git instances courses can bind to. Managed instances hold a service token used for babysat student-repo provisioning."
          actions={
            <Link href="/admin/git-servers/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
              Register Server
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : servers.length === 0 ? (
          <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
            No git servers registered yet — register one (e.g. your Forgejo) to enable babysat provisioning.
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
                  {s.managed && <Badge color="green">managed</Badge>}
                  <Badge color={s.has_token ? 'blue' : 'gray'}>{s.has_token ? 'token set' : 'no token'}</Badge>
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
