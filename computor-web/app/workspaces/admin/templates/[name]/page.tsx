'use client';

import { Suspense } from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import Tabs from '@/src/components/ui/Tabs';
import TemplateSettingsPanel from '@/src/components/workspaces/TemplateSettingsPanel';
import TemplateFilesPanel from '@/src/components/workspaces/TemplateFilesPanel';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';

type TemplateTab = 'settings' | 'files';

function TemplateAdminContent() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams<{ name: string }>();
  const templateName = decodeURIComponent(params.name);
  const rawTab = useSearchParam('tab');
  const tab: TemplateTab = rawTab === 'files' ? 'files' : 'settings';

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspaces' },
          { label: 'Administration', href: '/workspaces/admin?tab=templates' },
          { label: templateName },
        ]}
        title={templateName}
        subtitle="Resource limits, seat quota, Terraform configuration, and template files"
      />

      <Tabs<TemplateTab>
        tabs={[
          { id: 'settings', label: 'Limits & settings' },
          { id: 'files', label: 'Files (raw)' },
        ]}
        active={tab}
        onSelect={(id) => router.replace(id === 'settings' ? pathname : `${pathname}?tab=${id}`)}
      />

      {/*
        Both panels fill the page and scroll their own body, so the thing each
        one commits with — Save settings, Save <file> — stays pinned instead of
        sitting at the bottom of a page-length scroll. Same arrangement as the
        tabs on /workspaces/admin.
      */}
      <div className="flex-1 min-h-0 flex flex-col">
        {tab === 'settings' ? (
          <TemplateSettingsPanel templateName={templateName} />
        ) : (
          <TemplateFilesPanel templateName={templateName} />
        )}
      </div>
    </ListPageLayout>
  );
}

export default function TemplateAdminPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isWorkspaceMaintainer } = usePermissions();

  if (!authLoading && isAuthenticated && !isWorkspaceMaintainer) {
    return (
      <Forbidden
        message="Template administration requires the workspace maintainer role."
        backLink="/workspaces"
        backText="Back to workspaces"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <Suspense>
        <TemplateAdminContent />
      </Suspense>
    </AuthenticatedLayout>
  );
}
