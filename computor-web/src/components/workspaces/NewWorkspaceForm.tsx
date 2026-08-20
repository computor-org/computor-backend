'use client';

import { useState } from 'react';
import Button from '@/src/components/ui/Button';
import ErrorBanner from '@/src/components/ErrorBanner';
import { inputCls } from '@/src/components/ui/tokens';
import { useNotify } from '@/src/contexts/NotificationContext';
import { CoderClient } from '@/src/clients/CoderClient';
import {
  derivedWorkspaceName,
  workspaceCreatingUrl,
  workspaceLaunchUrl,
} from '@/src/utils/workspaceLaunch';
import { templateLabel, type TemplateOption } from './templateOptions';

const coderClient = new CoderClient();

/**
 * Create a workspace with a name of your own.
 *
 * The one thing the type cards cannot express. A self-provisioner has their
 * workspace name forced by the server and gets one per type, so a card is the
 * whole interaction for them; a maintainer can have several on one template
 * and needs to say which is which. That is a second field, not a second page —
 * so it lives here, folded away until asked for.
 */
export default function NewWorkspaceForm({
  options,
  onClose,
  onCreated,
}: {
  /** Usable types only — creating on a template Coder lacks just 503s. */
  options: TemplateOption[];
  onClose: () => void;
  /** Refresh the list behind the form. */
  onCreated: () => void;
}) {
  const notify = useNotify();
  const [template, setTemplate] = useState(options[0]?.name ?? '');
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!template) {
      setError('Choose a workspace type.');
      return;
    }
    setSubmitting(true);
    setError(null);

    // Open the tab NOW, inside the click. Provisioning is a round-trip, and a
    // window.open() after an await is no longer tied to the user gesture —
    // popup blockers eat it. The tab parks on the launch page's spinner until
    // the server tells us the workspace's real name.
    const tab = window.open(workspaceCreatingUrl, '_blank');
    try {
      const result = await coderClient.provisionWorkspace({
        body: { template, workspace_name: name.trim() || null },
      });
      const workspaceName = result.workspace?.name;
      if (!workspaceName) throw new Error('The workspace was not created.');

      const launchUrl = workspaceLaunchUrl(result.user.username, workspaceName);
      if (tab) {
        tab.location.replace(launchUrl);
        notify('Workspace created — opening in a new tab', 'success');
      } else {
        // Popup blocked: this tab goes instead.
        window.location.href = launchUrl;
        return;
      }
      onCreated();
      onClose();
    } catch (err) {
      tab?.close();
      // e.g. 409: that name is already taken by a workspace of another type
      setError(err instanceof Error ? err.message : 'Failed to create workspace');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <h3 className="text-sm font-semibold text-fg">New workspace with a custom name</h3>
      <ErrorBanner>{error}</ErrorBanner>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="min-w-[14rem] flex-1">
          <span className="mb-1 block text-xs font-medium text-body">Type</span>
          <select
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            className={inputCls}
          >
            {options.map((option) => (
              <option key={option.name} value={option.name}>
                {templateLabel(option)}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-[14rem] flex-1">
          <span className="mb-1 block text-xs font-medium text-body">
            Name <span className="font-normal text-subtle">(optional)</span>
          </span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls}
            placeholder={template ? derivedWorkspaceName(template) : ''}
            maxLength={32}
          />
        </label>
        <div className="flex gap-2 pb-0.5">
          <Button onClick={handleSubmit} loading={submitting} loadingLabel="Creating…">
            Create
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">
        Lowercase letters, digits and hyphens. Defaults to a name derived from the type
        {template ? ` ("${derivedWorkspaceName(template)}")` : ''}.
      </p>
    </div>
  );
}
