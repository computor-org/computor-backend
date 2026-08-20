'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge, { type BadgeColor } from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import TemplateTaskProgress from '@/src/components/workspaces/TemplateTaskProgress';
import { phaseLabel } from '@/src/components/workspaces/templateTaskStage';
import { CoderClient } from '@/src/clients/CoderClient';
import { TaskStatus } from '@/src/types/workspaces';
import type {
  CoderTemplateFleetStatus,
  CoderWorkspace,
  TaskInfo,
} from '@/src/types/workspaces';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';

const coderClient = new CoderClient();
const TERMINAL = new Set<TaskStatus>([
  TaskStatus.FINISHED,
  TaskStatus.FAILED,
  TaskStatus.CANCELLED,
]);

/**
 * Who a workspace belongs to, in the order a maintainer can actually read.
 *
 * Coder only knows owners by their encoded username (`u` + base32 of the
 * Computor user id — `coder/naming.py`), which is unreadable; the backend
 * resolves it for this view. The encoded name is still what addresses the
 * workspace in Coder's own UI and URLs, so it stays reachable on hover rather
 * than taking the line.
 */
function ownerLines(workspace: CoderWorkspace): { primary: string; secondary: string | null } {
  const name = workspace.owner_display_name;
  const email = workspace.owner_email;
  const primary = name || email || workspace.owner_name || workspace.owner_id;
  return { primary, secondary: name && email ? email : null };
}

/** Everything about a workspace the search box matches on. */
function searchHaystack(workspace: CoderWorkspace): string {
  return [
    workspace.owner_display_name,
    workspace.owner_email,
    workspace.owner_name,
    workspace.name,
    workspace.template_display_name,
    workspace.template_name,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function readiness(template: CoderTemplateFleetStatus): {
  label: string;
  color: BadgeColor;
  detail: string;
} {
  switch (template.rollout_state) {
    case 'unavailable':
      return { label: 'Unavailable', color: 'gray', detail: 'No active template version' };
    case 'ready':
      return {
        label: 'Running outdated',
        color: 'yellow',
        detail: `${template.actionable_count} running workspace${template.actionable_count === 1 ? '' : 's'} can be updated now`,
      };
    case 'scheduled_on_start':
      return {
        label: 'Scheduled',
        color: 'blue',
        detail: `${template.scheduled_on_start_count} update on next start`,
      };
    default:
      return { label: 'Up to date', color: 'green', detail: 'No rollout needed' };
  }
}

/** Privileged template update controls plus the detailed workspace fleet. */
export default function WorkspaceFleetPanel() {
  const notify = useNotify();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [imageTag, setImageTag] = useState('');
  const [noCache, setNoCache] = useState(false);
  const [optimisticTask, setOptimisticTask] = useState<TaskInfo | null>(null);
  const [query, setQuery] = useState('');

  const { data, loading, error, reload, refresh } = useResource(
    async () => {
      const [fleet, workspaces, taskList] = await Promise.all([
        coderClient.getFleetStatus(),
        coderClient.listAllWorkspaces(),
        coderClient.listAdminTasks(10),
      ]);
      return { fleet, workspaces: workspaces.workspaces, tasks: taskList.tasks };
    },
    [],
    { refetchInterval: 3000 },
  );

  const templates = useMemo(() => data?.fleet.templates ?? [], [data]);
  const workspaces = useMemo(() => data?.workspaces ?? [], [data]);
  const tasks = useMemo(() => data?.tasks ?? [], [data]);
  const activeTask = tasks.find((item) => !TERMINAL.has(item.status)) ?? null;

  const optimisticVisible = optimisticTask && !tasks.some(
    (item) => item.task_id === optimisticTask.task_id,
  ) ? optimisticTask : null;
  const currentTask = activeTask ?? optimisticVisible ?? tasks[0] ?? null;
  const busy = Boolean(activeTask || optimisticVisible);
  const runningTask = activeTask ?? optimisticVisible;
  const selectedTemplates = templates.filter((template) => selected.has(template.name));
  const selectedReady = selectedTemplates.filter((template) => template.actionable_count > 0);

  const activeVersionByTemplate = useMemo(
    () => new Map(templates.map((template) => [template.id, template.active_version_id])),
    [templates],
  );

  function isOutdated(workspace: CoderWorkspace): boolean {
    const active = activeVersionByTemplate.get(workspace.template_id);
    return Boolean(active && workspace.template_version_id && workspace.template_version_id !== active);
  }

  const visibleWorkspaces = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return workspaces;
    return workspaces.filter((workspace) => searchHaystack(workspace).includes(needle));
  }, [workspaces, query]);

  function toggleTemplate(name: string) {
    setSelected((previous) => {
      const next = new Set(previous);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async function runBuildPush(names: string[]) {
    if (names.length === 0) return;
    try {
      const response = await coderClient.pushTemplates({
        templates: names,
        build_images: true,
        image_tag: imageTag.trim() || null,
        no_cache: noCache,
      });
      setOptimisticTask({
        task_id: response.workflow_id,
        workflow_id: response.workflow_id,
        task_name: response.task_name,
        status: TaskStatus.QUEUED,
        progress: { phase: 'queued', completed: 0, total: names.length },
      });
      notify(`Build & push queued for ${names.length} template${names.length === 1 ? '' : 's'}.`, 'success');
      await refresh();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to start build & push', 'error');
      await refresh();
    }
  }

  async function runRollout(names: string[]) {
    if (names.length === 0) return;
    try {
      const response = await coderClient.rolloutWorkspaces({ templates: names });
      setOptimisticTask({
        task_id: response.workflow_id,
        workflow_id: response.workflow_id,
        task_name: response.task_name,
        status: TaskStatus.QUEUED,
        progress: { phase: 'queued', completed: 0, total: names.length },
      });
      notify(`Rollout queued for ${names.length} template${names.length === 1 ? '' : 's'}.`, 'success');
      await refresh();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to start rollout', 'error');
      await refresh();
    }
  }

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${
              data === null ? 'bg-faint' : data.fleet.healthy ? 'bg-success' : 'bg-danger'
            }`}
          />
          {data === null
            ? 'Checking Coder…'
            : data.fleet.healthy
              ? `Coder healthy${data.fleet.version ? ` · v${data.fleet.version}` : ''}`
              : 'Coder unreachable'}
        </span>
        <span className="text-faint">·</span>
        <span>{loading ? '—' : `${data?.fleet.workspace_count ?? 0} workspaces`}</span>
      </div>

      <div className="shrink-0 bg-surface rounded-lg border border-rule p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-fg">Template updates</h2>
          <p className="text-sm text-muted mt-1">
            Build and activate a new version for selected templates. A push schedules the fleet
            update by itself: every workspace adopts the new version on its next start. Update
            running now additionally rebuilds workspaces that are up right now — that interrupts
            whoever is working in them, so save it for fixes that cannot wait. Only templates
            already deployed to Coder appear here — to deploy one for the first time, use the{' '}
            <Link href="/workspaces/admin?tab=templates" className="text-accent-text hover:underline">
              Templates
            </Link>{' '}
            tab.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="w-64">
            <label htmlFor="image-tag" className="block text-xs font-medium text-body mb-1">
              Image tag (advanced, optional)
            </label>
            <input
              id="image-tag"
              value={imageTag}
              onChange={(event) => setImageTag(event.target.value)}
              placeholder="auto (from run time)"
              className={inputCls}
              disabled={busy}
            />
          </div>
          {/*
            A build already re-runs the extension checkout whenever that repo
            moves, so this is not the normal way to get a new extension — it is
            the fallback for cache staleness elsewhere in the image, and it
            rebuilds everything (slow, especially for MATLAB).
          */}
          <label className="flex items-center gap-2 pb-2 text-xs text-body">
            <input
              type="checkbox"
              checked={noCache}
              onChange={(event) => setNoCache(event.target.checked)}
              disabled={busy}
              className="h-4 w-4"
            />
            Rebuild all layers (slow)
          </label>
          <Button
            onClick={() => runBuildPush(selectedTemplates.map((template) => template.name))}
            disabled={busy || selectedTemplates.length === 0}
            title={selectedTemplates.length === 0 ? 'Select at least one template' : undefined}
          >
            Build &amp; push selected ({selectedTemplates.length})
          </Button>
          <Button
            variant="secondary"
            onClick={() => runRollout(selectedReady.map((template) => template.name))}
            disabled={busy || selectedReady.length === 0}
            title={selectedReady.length === 0 ? 'No selected template has running outdated workspaces' : undefined}
          >
            Update running now ({selectedReady.length})
          </Button>
        </div>

        {currentTask && <TemplateTaskProgress task={currentTask} />}
      </div>

      {loading ? (
        <ListLoading>Loading template fleet…</ListLoading>
      ) : (
        <ScrollPanel className="h-[32rem]">
          <Table>
            <Thead>
              <tr>
                <Th className="w-10">
                  <input
                    type="checkbox"
                    aria-label="Select all templates"
                    checked={templates.length > 0 && selectedTemplates.length === templates.length}
                    onChange={(event) =>
                      setSelected(event.target.checked ? new Set(templates.map((item) => item.name)) : new Set())
                    }
                  />
                </Th>
                <Th>Template</Th>
                <Th>Active version</Th>
                <Th>Workspaces</Th>
                <Th>Readiness</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {templates.map((template) => {
                const operation = runningTask?.progress?.templates?.find(
                  (item) => item.name === template.name,
                );
                const state = operation
                  ? {
                      label: operation.status === 'failed'
                        ? 'Failed'
                        : runningTask?.task_name === 'rollout_workspaces'
                          ? 'Rolling out'
                          : operation.status === 'succeeded'
                            ? 'Version ready'
                            : operation.phase === 'pushing'
                              ? 'Pushing'
                              : 'Building',
                      color: (operation.status === 'failed'
                        ? 'red'
                        : operation.status === 'succeeded'
                          ? 'green'
                          : 'blue') as BadgeColor,
                      detail: operation.error || phaseLabel(operation.phase),
                    }
                  : readiness(template);
                return (
                  <Tr key={template.id} className="hover:bg-canvas">
                    <Td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${template.display_name || template.name}`}
                        checked={selected.has(template.name)}
                        onChange={() => toggleTemplate(template.name)}
                      />
                    </Td>
                    <Td>
                      <div className="text-sm font-medium text-fg">
                        {template.display_name || template.name}
                      </div>
                      <div className="text-xs text-muted">{template.name}</div>
                    </Td>
                    <Td className="text-sm text-muted font-mono">
                      {template.active_version_id ? template.active_version_id.slice(0, 12) : '—'}
                    </Td>
                    <Td>
                      <div className="text-sm text-body">{template.workspace_count} total</div>
                      <div className="text-xs text-muted">
                        {template.outdated_count > 0
                          ? `${template.outdated_count} on older version`
                          : `${template.current_count} current`}
                      </div>
                    </Td>
                    <Td>
                      <Badge color={state.color}>{state.label}</Badge>
                      <div className="text-xs text-muted mt-1">{state.detail}</div>
                    </Td>
                    <Td>
                      <div className="flex justify-end gap-2">
                        <Button size="xs" variant="ghost" disabled={busy} onClick={() => runBuildPush([template.name])}>
                          Build &amp; push
                        </Button>
                        <Button
                          size="xs"
                          variant="secondary"
                          disabled={busy || template.actionable_count === 0}
                          title={template.actionable_count === 0 ? state.detail : undefined}
                          onClick={() => runRollout([template.name])}
                        >
                          Update running
                        </Button>
                      </div>
                    </Td>
                  </Tr>
                );
              })}
              {templates.length === 0 && (
                <Tr>
                  <Td colSpan={6} className="py-8 text-center text-sm text-muted">No templates.</Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
      )}

      <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <span>
          Workspace details
          {query.trim() && <span> · {visibleWorkspaces.length} of {workspaces.length}</span>}
          {visibleWorkspaces.some(isOutdated) && (
            <span className="text-warn-text"> · {visibleWorkspaces.filter(isOutdated).length} on an older version</span>
          )}
        </span>
        <div className="flex items-center gap-2">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className={`${inputCls} w-72`}
            placeholder="Filter by owner or template…"
            aria-label="Filter workspaces"
          />
          <Button size="xs" variant="ghost" onClick={() => reload()} disabled={loading}>Refresh</Button>
        </div>
      </div>

      {!loading && (
        <ScrollPanel className="h-[32rem]">
          <Table>
            <Thead>
              <tr>
                <Th>Owner</Th><Th>Workspace</Th><Th>Template</Th><Th>Version</Th><Th>Status</Th>
              </tr>
            </Thead>
            <Tbody>
              {visibleWorkspaces.map((workspace) => {
                const owner = ownerLines(workspace);
                return (
                <Tr key={workspace.id} className="hover:bg-canvas">
                  <Td title={workspace.owner_name ? `Coder user: ${workspace.owner_name}` : undefined}>
                    {workspace.owner_user_id ? (
                      <Link
                        href={`/workspaces/admin/${workspace.owner_user_id}`}
                        className="text-sm text-accent-text hover:underline"
                      >
                        {owner.primary}
                      </Link>
                    ) : (
                      <span className="text-sm text-fg">{owner.primary}</span>
                    )}
                    {owner.secondary && (
                      <div className="text-xs text-muted">{owner.secondary}</div>
                    )}
                  </Td>
                  <Td className="text-sm text-muted">{workspace.name}</Td>
                  <Td className="text-sm text-muted">
                    {workspace.template_display_name || workspace.template_name || '—'}
                  </Td>
                  <Td>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted">{workspace.template_version_name || '—'}</span>
                      {isOutdated(workspace) ? (
                        <Badge color="yellow">outdated</Badge>
                      ) : workspace.template_version_id ? (
                        <Badge color="green">latest</Badge>
                      ) : null}
                    </div>
                  </Td>
                  <Td>
                    <WorkspaceStatusBadge
                      status={workspace.latest_build_status}
                      transition={workspace.latest_build_transition}
                    />
                  </Td>
                </Tr>
                );
              })}
              {visibleWorkspaces.length === 0 && (
                <Tr>
                  <Td colSpan={5} className="py-8 text-center text-sm text-muted">
                    {workspaces.length === 0 ? 'No workspaces.' : 'No workspaces match the filter.'}
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
      )}
    </>
  );
}
