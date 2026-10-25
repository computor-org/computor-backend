'use client';

import { Suspense } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import Tabs from '@/src/components/ui/Tabs';
import { ButtonLink } from '@/src/components/ui/Button';
import WorkspaceUsersPanel from '@/src/components/workspaces/WorkspaceUsersPanel';
import WorkspaceFleetPanel from '@/src/components/workspaces/WorkspaceFleetPanel';
import WorkspaceTemplatesPanel from '@/src/components/workspaces/WorkspaceTemplatesPanel';
import WorkspaceVolumesPanel from '@/src/components/workspaces/WorkspaceVolumesPanel';
import WorkspaceCoursesPanel from '@/src/components/workspaces/WorkspaceCoursesPanel';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

type AdminTab = 'users' | 'fleet' | 'templates' | 'courses' | 'volumes';

const COPY = {
  de: {
    workspaces: 'Arbeitsumgebungen',
    administration: 'Administration',
    title: 'Administration der Arbeitsumgebungen',
    subtitle: 'Rollen für Arbeitsumgebungen, Zugriff pro Person, verfügbare Vorlagen und Image-Rollouts für die gesamte Flotte',
    newTemplate: 'Neue Vorlage',
    tabUsers: 'Personen & Rollen',
    tabFleet: 'Flotte',
    tabTemplates: 'Vorlagen',
    tabCourses: 'Kurse',
    tabVolumes: 'Volumes',
    forbidden: 'Die Administration der Arbeitsumgebungen erfordert die Rolle „Workspace-Maintainer“.',
    back: 'Zurück zu den Arbeitsumgebungen',
  },
  en: {
    workspaces: 'Workspaces',
    administration: 'Administration',
    title: 'Workspace administration',
    subtitle: 'Workspace roles, per-user access, which templates are available, and fleet-wide image rollouts',
    newTemplate: 'New template',
    tabUsers: 'Users & roles',
    tabFleet: 'Fleet',
    tabTemplates: 'Templates',
    tabCourses: 'Courses',
    tabVolumes: 'Volumes',
    forbidden: 'Workspace administration requires the workspace maintainer role.',
    back: 'Back to workspaces',
  },
};

function WorkspaceAdminContent() {
  const router = useRouter();
  const t = COPY[useUiLanguage()];
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
        breadcrumbs={[{ label: t.workspaces, href: '/workspaces' }, { label: t.administration }]}
        title={t.title}
        subtitle={t.subtitle}
        actions={
          tab === 'templates' ? (
            <ButtonLink href="/workspaces/admin/templates/create">{t.newTemplate}</ButtonLink>
          ) : undefined
        }
      />

      <Tabs<AdminTab>
        tabs={[
          { id: 'users', label: t.tabUsers },
          { id: 'fleet', label: t.tabFleet },
          { id: 'templates', label: t.tabTemplates },
          { id: 'courses', label: t.tabCourses },
          { id: 'volumes', label: t.tabVolumes },
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
  const t = COPY[useUiLanguage()];

  if (!authLoading && isAuthenticated && !isWorkspaceMaintainer) {
    return (
      <Forbidden
        message={t.forbidden}
        backLink="/workspaces"
        backText={t.back}
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
