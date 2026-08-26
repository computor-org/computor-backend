'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useResource } from '@/src/hooks/useResource';
import { useCoderTemplates } from '@/src/hooks/useCoderTemplates';
import { useWorkspaceActions } from '@/src/hooks/useWorkspaceActions';
import { useNotify } from '@/src/contexts/NotificationContext';
import Button from '@/src/components/ui/Button';
import WorkspaceStatusBadge, {
  categorizeStatus,
} from '@/src/components/workspaces/WorkspaceStatusBadge';
import TemplateCard, { TemplateIconButton } from '@/src/components/workspaces/TemplateCard';
import { courseTemplateOption } from '@/src/components/workspaces/templateOptions';
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
 * Renders one card per (enabled) template — clicking ensures the caller's
 * per-template workspace exists (provisioning is idempotent; a re-click just
 * refreshes its token) and opens the launch tab. The non-compact variant also
 * lists the caller's existing workspaces on course templates, which covers
 * lecturer-provisioned throwaway workspaces (students can open and start
 * those, but not provision them).
 *
 * A course holds its templates by name, so it can go on offering one Coder
 * does not have — never deployed, or still building. Those render dimmed and
 * unclickable, with the reason in reach: the click used to travel to the
 * server and come back as "Template 'bash-workspace' is not yet available",
 * which reads as a broken button rather than a fact about the deployment.
 *
 * Self-hiding: renders nothing while loading, on error (non-members), or when
 * the course has no templates.
 */
export default function CourseWorkspaceLaunchButtons({
  courseId,
  compact = false,
  className,
  title,
}: {
  courseId: string;
  compact?: boolean;
  /** Extra classes on the root, e.g. outer spacing — only rendered when the
      component itself renders, so callers don't get stray margins when it
      self-hides. */
  className?: string;
  /** Section heading rendered inside the root (non-compact only) — lives here
      rather than in the caller so it disappears with the component when the
      course has no templates, instead of leaving an empty titled card. */
  title?: string;
}) {
  const router = useRouter();
  const notify = useNotify();
  const [launching, setLaunching] = useState<string | null>(null);
  const [stopping, setStopping] = useState<string | null>(null);

  // Enabled course templates — one snapshot; what a course offers does not
  // change under an open page.
  const { data: courseTemplates } = useResource(
    async () => {
      const settings = await courseWorkspacesClient
        .getSettings({ courseId })
        .catch(() => null);
      return (settings?.templates ?? []).filter((t) => t.enabled);
    },
    [courseId],
  );
  const templates = useMemo(() => courseTemplates ?? [], [courseTemplates]);

  // Own workspaces on course templates (incl. lecturer-provisioned ones),
  // polled like the /workspaces table so the status chip follows a start or
  // stop on its own instead of freezing on the first snapshot. 403s only when
  // the caller has neither a workspace role nor course access — then the
  // section is icon-only.
  const { data: workspacesData, refresh } = useResource(
    async () => {
      const names = new Set(templates.map((t) => t.template_name));
      return coderClient
        .listWorkspaces()
        .then((r) => r.workspaces.filter((w) => w.template_name && names.has(w.template_name)))
        .catch(() => [] as CoderWorkspace[]);
    },
    [courseId, templates],
    { enabled: !compact && templates.length > 0, refetchInterval: 3000 },
  );

  // Deployment state — including the build a user may be waiting on — comes
  // from the templates listing, but only where one of these is on the page.
  // The compact variant sits on every card of the courses list, where a second
  // request per course would be the page's dominant cost; there the course
  // settings' own exists_in_coder carries the "not available" case, and an
  // icon row has no room for a stage bar anyway.
  const {
    options,
    answered: templatesAnswered,
    error: templatesError,
  } = useCoderTemplates({
    enabled: !compact,
    refetchInterval: compact ? undefined : 10000,
  });

  const workspaces = workspacesData ?? [];

  // Same stop as the /workspaces table (notification + delayed refresh) — the
  // backend allows course-derived callers to stop their own workspaces, and
  // this widget is the only workspace surface many of them ever see.
  const actions = useWorkspaceActions(refresh);

  const courseOptions = useMemo(() => {
    const byName = new Map(options.map((option) => [option.name, option]));
    // A listing that never ran, or failed, tells us nothing — then the course
    // settings' exists_in_coder is what is left to go on.
    const answered = !compact && templatesAnswered && !templatesError;
    return templates.map((t) => courseTemplateOption(t, byName.get(t.template_name), answered));
  }, [templates, options, templatesAnswered, templatesError, compact]);

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

  async function stopExisting(workspace: CoderWorkspace) {
    if (!workspace.owner_name) return;
    setStopping(workspace.id);
    try {
      await actions.stop(workspace.owner_name, workspace.name);
    } finally {
      setStopping(null);
    }
  }

  if (compact) {
    return (
      <div className={`mt-2 flex flex-wrap items-center gap-1.5 ${className ?? ''}`}>
        {courseOptions.map((option) => (
          <TemplateIconButton
            key={option.name}
            option={option}
            busy={launching === option.name}
            dimmed={launching !== null && launching !== option.name}
            onClick={() => provisionAndLaunch(option.name)}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className ?? ''}`}>
      {title && <h2 className="text-lg font-semibold text-fg">{title}</h2>}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {courseOptions.map((option) => (
          <TemplateCard
            key={option.name}
            option={option}
            actionLabel={launching === option.name ? 'Launching…' : 'Launch workspace'}
            busy={launching === option.name}
            onClick={() => provisionAndLaunch(option.name)}
          />
        ))}
      </div>

      {workspaces.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-body mb-2">Your workspaces</h3>
          <ul className="space-y-1.5">
            {workspaces.map((w) => {
              const category = categorizeStatus(w.latest_build_status, w.latest_build_transition);
              return (
                <li
                  key={w.id}
                  className="flex items-center justify-between gap-2 rounded-lg border border-rule px-3 py-2"
                >
                  <div className="min-w-0">
                    <span className="block truncate text-sm font-medium text-fg">{w.name}</span>
                    <span className="block text-xs text-muted">
                      {w.template_display_name || w.template_name}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {/*
                      The chip alone, as in the workspaces table: starting or
                      stopping is a wait of seconds with no stages to report,
                      and the chip already names it.
                    */}
                    <WorkspaceStatusBadge
                      status={w.latest_build_status}
                      transition={w.latest_build_transition}
                    />
                    <Button size="xs" onClick={() => openExisting(w)}>
                      {category === 'running' ? 'Open' : category === 'failed' ? 'Retry' : 'Start'}
                    </Button>
                    {category === 'running' && (
                      <Button
                        size="xs"
                        variant="secondary"
                        onClick={() => stopExisting(w)}
                        loading={stopping === w.id}
                        loadingLabel="Stopping…"
                      >
                        Stop
                      </Button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
