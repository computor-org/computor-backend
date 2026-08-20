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
import WorkspaceVolumesPanel from '@/src/components/workspaces/WorkspaceVolumesPanel';
import WorkspaceCoursesPanel from '@/src/components/workspaces/WorkspaceCoursesPanel';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';

type AdminTab = 'users' | 'fleet' | 'templates' | 'courses' | 'volumes';

function WorkspaceAdminContent() {
  const router = useRouter();
  const pathname = usePathname();
  // URL-backed tabs (?tab=fleet) so all are deep-linkable.
  const rawTab = useSearchParam('tab');
  const tab: AdminTab =
    rawTab === 'fleet' ? 'fleet'
    : rawTab === 'templates' ? 'templates'
    : rawTab === 'courses' ? 'courses'
    : rawTab === 'volumes' ? 'volumes'
    : 'users';

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={[{ label: 'Workspaces', href: '/workspaces' }, { label: 'Administration' }]}
        title="Workspace administration"
        subtitle="Workspace roles, per-user access, which templates are available, and fleet-wide image rollouts"
      />

      <Tabs<AdminTab>
        tabs={[
          { id: 'users', label: 'Users & roles' },
          { id: 'fleet', label: 'Fleet' },
          { id: 'templates', label: 'Templates' },
          { id: 'courses', label: 'Courses' },
          { id: 'volumes', label: 'Volumes' },
        ]}
        active={tab}
        onSelect={(id) => router.replace(id === 'users' ? pathname : `${pathname}?tab=${id}`)}
      />

      {/*
        Single-table panels are flex-column children, like the users panel
        above: their chrome is `shrink-0` and the table claims the rest of the
        height. The fleet panel is the exception — it stacks TWO tables, which
        in a flex column would halve each into a couple of visible rows, so it
        keeps a scrolling page with its own bounded tables instead.
      */}
      {tab === 'users' ? (
        <WorkspaceUsersPanel />
      ) : tab === 'fleet' ? (
        <ScrollArea>
          <WorkspaceFleetPanel />
        </ScrollArea>
      ) : tab === 'templates' ? (
        <div className="flex-1 min-h-0 flex flex-col gap-6">
          <WorkspaceTemplatesPanel />
        </div>
      ) : tab === 'volumes' ? (
        <div className="flex-1 min-h-0 flex flex-col gap-6">
          <WorkspaceVolumesPanel />
        </div>
      ) : (
        <div className="flex-1 min-h-0 flex flex-col gap-6">
          <WorkspaceCoursesPanel />
        </div>
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
