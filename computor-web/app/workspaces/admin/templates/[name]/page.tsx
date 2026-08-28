'use client';

import { Suspense, useState } from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import Tabs from '@/src/components/ui/Tabs';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import TemplateSettingsPanel from '@/src/components/workspaces/TemplateSettingsPanel';
import TemplateDetailsPanel from '@/src/components/workspaces/TemplateDetailsPanel';
import TemplateFilesPanel from '@/src/components/workspaces/TemplateFilesPanel';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import { CoderClient } from '@/src/clients/CoderClient';

const coderClient = new CoderClient();

type TemplateTab = 'settings' | 'details' | 'files';

function TemplateAdminContent() {
  const router = useRouter();
  const pathname = usePathname();
  const notify = useNotify();
  const params = useParams<{ name: string }>();
  const templateName = decodeURIComponent(params.name);
  const rawTab = useSearchParam('tab');
  const tab: TemplateTab =
    rawTab === 'files' ? 'files' : rawTab === 'details' ? 'details' : 'settings';
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Manifest-only (answers while Coder is down). Drives the provenance badge
  // and the Delete action, which exists for clones alone: a repo-shipped
  // template would only be seeded again on the next startup.
  const { data: meta, reload: reloadMeta } = useResource(
    () => coderClient.getTemplateMetadata({ templateName }),
    [templateName],
  );
  const clonedFrom = meta?.cloned_from ?? null;

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={[
          { label: 'Workspaces', href: '/workspaces' },
          { label: 'Administration', href: '/workspaces/admin?tab=templates' },
          { label: templateName },
        ]}
        title={templateName}
        subtitle={
          <span className="inline-flex flex-wrap items-center gap-2">
            {clonedFrom && (
              <Badge tone="info" title="Created here; the repository sync never touches it">
                cloned from {clonedFrom}
              </Badge>
            )}
            <span>
              Resource limits, seat quota, display details, Terraform configuration, and template
              files
            </span>
          </span>
        }
        actions={
          clonedFrom ? (
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              Delete template
            </Button>
          ) : undefined
        }
      />

      <Tabs<TemplateTab>
        tabs={[
          { id: 'settings', label: 'Limits & settings' },
          { id: 'details', label: 'Details' },
          { id: 'files', label: 'Files (raw)' },
        ]}
        active={tab}
        onSelect={(id) => router.replace(id === 'settings' ? pathname : `${pathname}?tab=${id}`)}
      />

      {/*
        Every panel fills the page and scrolls its own body, so the thing each
        one commits with — Save settings, Save details, Save <file> — stays
        pinned instead of sitting at the bottom of a page-length scroll. Same
        arrangement as the tabs on /workspaces/admin.
      */}
      <div className="flex-1 min-h-0 flex flex-col">
        {tab === 'settings' ? (
          <TemplateSettingsPanel templateName={templateName} />
        ) : tab === 'details' ? (
          <TemplateDetailsPanel templateName={templateName} onSaved={() => void reloadMeta()} />
        ) : (
          <TemplateFilesPanel templateName={templateName} />
        )}
      </div>

      {confirmDelete && meta && (
        <ConfirmDeleteDialog
          title="Delete template?"
          message={
            `Removes the template directory '${meta.dir_name}', its Coder template (only ` +
            'possible while no workspace uses it), and its settings and course assignments. ' +
            'Built images stay in the registry. This cannot be undone.'
          }
          confirmWord={templateName}
          onConfirm={async () => {
            const result = await coderClient.deleteTemplate({ templateName });
            notify(result.message, 'success');
            router.push('/workspaces/admin?tab=templates');
          }}
          onClose={() => setConfirmDelete(false)}
        />
      )}
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
