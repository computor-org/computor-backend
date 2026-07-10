'use client';

import { Suspense } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import Tabs from '@/src/components/ui/Tabs';
import WorkspaceUsersPanel from '@/src/components/workspaces/WorkspaceUsersPanel';
import WorkspaceFleetPanel from '@/src/components/workspaces/WorkspaceFleetPanel';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';

type AdminTab = 'users' | 'fleet';

function WorkspaceAdminContent() {
  const router = useRouter();
  const pathname = usePathname();
  // URL-backed tabs (?tab=fleet) so both are deep-linkable.
  const tab: AdminTab = useSearchParam('tab') === 'fleet' ? 'fleet' : 'users';

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={[{ label: 'Workspaces', href: '/workspaces' }, { label: 'Administration' }]}
        title="Workspace Administration"
        subtitle="Workspace roles, per-user access, and fleet-wide image rollouts"
      />

      <Tabs<AdminTab>
        tabs={[
          { id: 'users', label: 'Users & roles' },
          { id: 'fleet', label: 'Fleet' },
        ]}
        active={tab}
        onSelect={(id) => router.replace(id === 'users' ? pathname : `${pathname}?tab=${id}`)}
      />

      {tab === 'users' ? <WorkspaceUsersPanel /> : <WorkspaceFleetPanel />}
    </ListPageLayout>
  );
}

export default function WorkspaceAdminPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isWorkspaceMaintainer } = usePermissions();

  if (!authLoading && isAuthenticated && !isWorkspaceMaintainer) {
    return (
      <Forbidden
        message="Workspace administration requires the workspace maintainer role."
        backLink="/workspaces"
        backText="Back to workspaces"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <Suspense>
        <WorkspaceAdminContent />
      </Suspense>
    </AuthenticatedLayout>
  );
}
