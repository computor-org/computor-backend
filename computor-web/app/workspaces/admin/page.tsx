'use client';

import { Suspense } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import Tabs from '@/src/components/ui/Tabs';
import WorkspaceUsersPanel from '@/src/components/workspaces/WorkspaceUsersPanel';
import WorkspaceFleetPanel from '@/src/components/workspaces/WorkspaceFleetPanel';
import WorkspaceTemplatesPanel from '@/src/components/workspaces/WorkspaceTemplatesPanel';
import WorkspaceCoursesPanel from '@/src/components/workspaces/WorkspaceCoursesPanel';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';

type AdminTab = 'users' | 'fleet' | 'templates' | 'courses';

function WorkspaceAdminContent() {
  const router = useRouter();
  const pathname = usePathname();
  // URL-backed tabs (?tab=fleet) so all are deep-linkable.
  const rawTab = useSearchParam('tab');
  const tab: AdminTab =
    rawTab === 'fleet' ? 'fleet'
    : rawTab === 'templates' ? 'templates'
    : rawTab === 'courses' ? 'courses'
    : 'users';

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={[{ label: 'Workspaces', href: '/workspaces' }, { label: 'Administration' }]}
        title="Workspace Administration"
        subtitle="Workspace roles, per-user access, template configuration, and fleet-wide image rollouts"
      />

      <Tabs<AdminTab>
        tabs={[
          { id: 'users', label: 'Users & roles' },
          { id: 'fleet', label: 'Fleet' },
          { id: 'templates', label: 'Templates' },
          { id: 'courses', label: 'Courses' },
        ]}
        active={tab}
        onSelect={(id) => router.replace(id === 'users' ? pathname : `${pathname}?tab=${id}`)}
      />

      {tab === 'users' ? (
        <WorkspaceUsersPanel />
      ) : tab === 'fleet' ? (
        <ScrollArea className="space-y-6 pr-1">
          <WorkspaceFleetPanel />
        </ScrollArea>
      ) : tab === 'templates' ? (
        <ScrollArea className="space-y-6 pr-1">
          <WorkspaceTemplatesPanel />
        </ScrollArea>
      ) : (
        <ScrollArea className="space-y-6 pr-1">
          <WorkspaceCoursesPanel />
        </ScrollArea>
      )}
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
