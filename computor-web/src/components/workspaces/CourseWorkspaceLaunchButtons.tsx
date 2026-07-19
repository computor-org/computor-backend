'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import Button from '@/src/components/ui/Button';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';
import { CoderClient } from '@/src/clients/CoderClient';
import { CourseWorkspacesClient } from '@/src/clients/CourseWorkspacesClient';
import {
  openLaunchTab,
  workspaceCreatingUrl,
  workspaceLaunchUrl,
} from '@/src/utils/workspaceLaunch';
import type { CoderWorkspace } from '@/src/types/workspaces';

const coderClient = new CoderClient();
const courseWorkspacesClient = new CourseWorkspacesClient();

/**
 * Launch buttons for a course's allowed workspace templates.
 *
 * Renders one icon button per (enabled) template — clicking ensures the
 * caller's per-template workspace exists (provisioning is idempotent; a
 * re-click just refreshes its token) and opens the launch tab. The non-compact
 * variant also lists the caller's existing workspaces on course templates,
 * which covers lecturer-provisioned throwaway workspaces (students can open
 * and start those, but not provision them).
 *
 * Self-hiding: renders nothing while loading, on error (non-members), or when
 * the course has no templates.
 */
export default function CourseWorkspaceLaunchButtons({
  courseId,
  compact = false,
}: {
  courseId: string;
  compact?: boolean;
}) {
  const router = useRouter();
  const notify = useNotify();
  const [launching, setLaunching] = useState<string | null>(null);

  const { data } = useResource(
    async () => {
      const settings = await courseWorkspacesClient
        .getSettings({ courseId })
        .catch(() => null);
      const templates = (settings?.templates ?? []).filter((t) => t.enabled);
      if (templates.length === 0) return { templates: [], workspaces: [] as CoderWorkspace[] };
      const names = new Set(templates.map((t) => t.template_name));
      // Own workspaces on course templates (incl. lecturer-provisioned ones).
      // 403s only when the caller has neither a workspace role nor course
      // access — then the section is icon-only.
      const workspaces = compact
        ? []
        : await coderClient
            .listWorkspaces()
            .then((r) => r.workspaces.filter((w) => w.template_name && names.has(w.template_name)))
            .catch(() => [] as CoderWorkspace[]);
      return { templates, workspaces };
    },
    [courseId, compact],
  );

  const templates = data?.templates ?? [];
  const workspaces = data?.workspaces ?? [];
  if (templates.length === 0) return null;

  // window.open must happen synchronously inside the click — after an await it
  // is no longer tied to the user gesture and popup blockers eat it.
  async function provisionAndLaunch(templateName: string) {
    setLaunching(templateName);
    const tab = window.open(workspaceCreatingUrl, '_blank');
    try {
      const result = await coderClient.provisionWorkspace({
        body: { template: templateName },
      });
      const workspaceName = result.workspace?.name;
      if (!workspaceName) throw new Error('The workspace was not created.');
      const launchUrl = workspaceLaunchUrl(result.user.username, workspaceName);
      if (tab) {
        tab.location.replace(launchUrl);
      } else {
        router.push(launchUrl);
      }
    } catch (err) {
      tab?.close();
      notify(err instanceof Error ? err.message : 'Failed to launch workspace', 'error');
    } finally {
      setLaunching(null);
    }
  }

  function openExisting(workspace: CoderWorkspace) {
    if (!workspace.owner_name) return;
    if (!openLaunchTab(workspace.owner_name, workspace.name)) {
      router.push(workspaceLaunchUrl(workspace.owner_name, workspace.name));
    }
  }

  if (compact) {
    return (
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {templates.map((t) => (
          <button
            key={t.template_name}
            type="button"
            title={`Launch ${t.display_name || t.template_name}`}
            aria-label={`Launch ${t.display_name || t.template_name} workspace`}
            disabled={launching !== null}
            onClick={(event) => {
              // The card wraps this in a Link-adjacent row; keep the click local.
              event.stopPropagation();
              provisionAndLaunch(t.template_name);
            }}
            className={`rounded-lg transition-opacity hover:opacity-75 ${
              launching === t.template_name ? 'animate-pulse' : ''
            } ${launching !== null && launching !== t.template_name ? 'opacity-50' : ''}`}
          >
            <TemplateIcon template={{ icon: t.icon, name: t.template_name }} size="sm" />
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        {templates.map((t) => (
          <button
            key={t.template_name}
            type="button"
            disabled={launching !== null}
            onClick={() => provisionAndLaunch(t.template_name)}
            className={`flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 pr-4 text-left transition-colors hover:border-blue-400 hover:bg-blue-50 ${
              launching !== null && launching !== t.template_name ? 'opacity-50' : ''
            }`}
          >
            <TemplateIcon template={{ icon: t.icon, name: t.template_name }} />
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-gray-900">
                {t.display_name || t.template_name}
              </span>
              <span className="block text-xs text-gray-500">
                {launching === t.template_name ? 'Launching…' : 'Launch workspace'}
              </span>
            </span>
          </button>
        ))}
      </div>

      {workspaces.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Your workspaces</h3>
          <ul className="space-y-1.5">
            {workspaces.map((w) => (
              <li
                key={w.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-gray-200 px-3 py-2"
              >
                <div className="min-w-0">
                  <span className="block truncate text-sm font-medium text-gray-900">{w.name}</span>
                  <span className="block text-xs text-gray-500">
                    {w.template_display_name || w.template_name}
                  </span>
                </div>
                <Button size="xs" variant="secondary" onClick={() => openExisting(w)}>
                  Open
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
