'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import FormPanel, { Field } from '@/src/components/FormPanel';
import Forbidden from '@/src/components/Forbidden';
import TemplatePicker from '@/src/components/workspaces/TemplatePicker';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCoderTemplates } from '@/src/hooks/useCoderTemplates';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import { useNotify } from '@/src/contexts/NotificationContext';
import { CoderClient } from '@/src/clients/CoderClient';
import { workspaceLaunchUrl } from '@/src/utils/workspaceLaunch';
import { inputCls } from '@/src/components/ui/tokens';

const coderClient = new CoderClient();

/** Mirror of the backend's default-name rule — display only, the server decides. */
function derivedName(template: string): string {
  return template.replace(/-workspace$/, '').replace(/[^a-z0-9-]/g, '') || 'workspace';
}

function CreateWorkspaceForm({ allowCustomName }: { allowCustomName: boolean }) {
  const router = useRouter();
  const notify = useNotify();
  const preselected = useSearchParam('template');

  const { templates, loading: templatesLoading, error: templatesError } = useCoderTemplates();

  const [template, setTemplate] = useState('');
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Preselect from ?template= (raw name) once templates arrive; else first one.
  useEffect(() => {
    if (template || templates.length === 0) return;
    const match = preselected && templates.find((t) => t.name === preselected);
    setTemplate(match ? match.name : templates[0].name);
  }, [templates, preselected, template]);

  const handleSubmit = async () => {
    if (!template) {
      setError('Choose a template.');
      return;
    }
    setSubmitting(true);
    setError(null);

    // Open the tab NOW, while we are still inside the click. Provisioning is a
    // round-trip, and a window.open() after an await is no longer tied to the
    // user gesture — popup blockers eat it. The tab parks on about:blank for the
    // moment it takes to get the workspace's name back.
    const tab = window.open('about:blank', '_blank');

    try {
      const result = await coderClient.provisionWorkspace({
        body: { template, workspace_name: allowCustomName ? name.trim() || null : null },
      });

      // Always the server's name, never the derivedName() mirror: self-provisioners
      // have workspace_name nulled and re-derived server-side.
      const workspaceName = result.workspace?.name;
      if (!workspaceName) {
        throw new Error('The workspace was not created.');
      }

      const launchUrl = workspaceLaunchUrl(result.user.username, workspaceName);

      if (tab) {
        tab.location.replace(launchUrl);
        notify('Workspace created — opening in a new tab', 'success');
        router.push('/workspaces');
      } else {
        // Popup blocked: fall back to launching in this tab.
        router.push(launchUrl);
      }
    } catch (err) {
      tab?.close();
      // e.g. 409: name already taken by a workspace of a different template
      setError(err instanceof Error ? err.message : 'Failed to create workspace');
      setSubmitting(false);
    }
  };

  return (
    <FormPanel
      breadcrumbs={[{ label: 'Workspaces', href: '/workspaces' }, { label: 'Create' }]}
      title="New workspace"
      description={
        allowCustomName
          ? 'Pick a workspace type. All your workspaces share one home directory, so your files and user-space installs follow you.'
          : 'Pick a workspace type — you get one workspace per type. All your workspaces share one home directory, so your files and user-space installs follow you.'
      }
      error={error ?? templatesError}
      onSubmit={handleSubmit}
      onCancel={() => router.push('/workspaces')}
      submitting={submitting}
      submitLabel="Create"
      disabled={templatesLoading || !template}
    >
      <Field label="Template" required>
        {templatesLoading ? (
          <p className="text-sm text-gray-400">Loading templates…</p>
        ) : (
          <TemplatePicker templates={templates} value={template} onChange={setTemplate} />
        )}
      </Field>

      {allowCustomName && (
        <Field
          label="Workspace name"
          hint={
            template
              ? `Optional — defaults to "${derivedName(template)}". Lowercase letters, digits and hyphens.`
              : 'Optional — defaults to a name derived from the template.'
          }
        >
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls}
            placeholder={template ? derivedName(template) : ''}
            maxLength={32}
          />
        </Field>
      )}
    </FormPanel>
  );
}

export default function CreateWorkspacePage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canProvisionWorkspace, isWorkspaceMaintainer } = usePermissions();

  if (!authLoading && isAuthenticated && !canProvisionWorkspace) {
    return (
      <Forbidden
        message="Creating workspaces requires a workspace role."
        backLink="/workspaces"
        backText="Back to workspaces"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <Suspense>
        <CreateWorkspaceForm allowCustomName={isWorkspaceMaintainer} />
      </Suspense>
    </AuthenticatedLayout>
  );
}
