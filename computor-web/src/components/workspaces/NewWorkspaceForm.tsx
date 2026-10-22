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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    chooseType: 'Wähle eine Art von Arbeitsumgebung.',
    notCreated: 'Die Arbeitsumgebung wurde nicht erstellt.',
    created: 'Arbeitsumgebung erstellt, sie öffnet sich in einem neuen Tab',
    createFailed: 'Die Arbeitsumgebung konnte nicht erstellt werden',
    heading: 'Neue Arbeitsumgebung mit eigenem Namen',
    type: 'Art',
    name: 'Name',
    optional: '(optional)',
    create: 'Erstellen',
    creating: 'Wird erstellt …',
    cancel: 'Abbrechen',
    hint: 'Kleinbuchstaben, Ziffern und Bindestriche. Standardmäßig wird ein Name aus der Art abgeleitet',
  },
  en: {
    chooseType: 'Choose a workspace type.',
    notCreated: 'The workspace was not created.',
    created: 'Workspace created — opening in a new tab',
    createFailed: 'Failed to create workspace',
    heading: 'New workspace with a custom name',
    type: 'Type',
    name: 'Name',
    optional: '(optional)',
    create: 'Create',
    creating: 'Creating…',
    cancel: 'Cancel',
    hint: 'Lowercase letters, digits and hyphens. Defaults to a name derived from the type',
  },
};

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
  const t = COPY[useUiLanguage()];
  const [template, setTemplate] = useState(options[0]?.name ?? '');
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!template) {
      setError(t.chooseType);
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
      if (!workspaceName) throw new Error(t.notCreated);

      const launchUrl = workspaceLaunchUrl(result.user.username, workspaceName);
      if (tab) {
        tab.location.replace(launchUrl);
        notify(t.created, 'success');
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
      setError(err instanceof Error ? err.message : t.createFailed);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <h3 className="text-sm font-semibold text-fg">{t.heading}</h3>
      <ErrorBanner>{error}</ErrorBanner>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="min-w-[14rem] flex-1">
          <span className="mb-1 block text-xs font-medium text-body">{t.type}</span>
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
            {t.name} <span className="font-normal text-subtle">{t.optional}</span>
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
          <Button onClick={handleSubmit} loading={submitting} loadingLabel={t.creating}>
            {t.create}
          </Button>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            {t.cancel}
          </Button>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted">
        {t.hint}
        {template ? ` ("${derivedWorkspaceName(template)}")` : ''}.
      </p>
    </div>
  );
}
