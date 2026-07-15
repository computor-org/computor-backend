'use client';

import { useMemo, useState } from 'react';
import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge, { type BadgeColor } from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import { CoderClient } from '@/src/clients/CoderClient';
import { TaskStatus } from '@/src/types/workspaces';
import type {
  CoderTemplateFleetStatus,
  CoderTemplateTaskProgress,
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

function ownerName(workspace: CoderWorkspace): string {
  return workspace.owner_name || workspace.owner_id;
}

function taskLabel(taskName: string): string {
  if (taskName === 'rollout_workspaces') return 'Workspace rollout';
  if (taskName === 'build_workspace_images') return 'Image build';
  return 'Build & push';
}

function phaseLabel(phase?: string): string {
  return (phase || 'starting').replaceAll('_', ' ');
}

function progressColor(status: CoderTemplateTaskProgress['status']): BadgeColor {
  if (status === 'succeeded') return 'green';
  if (status === 'failed') return 'red';
  if (status === 'running') return 'blue';
  return 'gray';
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
        label: 'Ready to roll out',
        color: 'yellow',
        detail: `${template.actionable_count} workspace${template.actionable_count === 1 ? '' : 's'} can be updated`,
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
  const [optimisticTask, setOptimisticTask] = useState<TaskInfo | null>(null);

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
  const progress = currentTask?.progress;
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

      <div className="shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600">
        <span className="inline-flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${
              data === null ? 'bg-gray-300' : data.fleet.healthy ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          {data === null
            ? 'Checking Coder…'
            : data.fleet.healthy
              ? `Coder healthy${data.fleet.version ? ` · v${data.fleet.version}` : ''}`
              : 'Coder unreachable'}
        </span>
        <span className="text-gray-300">·</span>
        <span>{loading ? '—' : `${data?.fleet.workspace_count ?? 0} workspaces`}</span>
      </div>

      <div className="shrink-0 bg-white rounded-lg border border-gray-200 p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Template updates</h2>
          <p className="text-sm text-gray-500 mt-1">
            Build and activate a new version for selected templates, then roll out only the
            templates that have actionable outdated workspaces. Stopped workspaces update on
            their next start.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="w-64">
            <label htmlFor="image-tag" className="block text-xs font-medium text-gray-700 mb-1">
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
            title={selectedReady.length === 0 ? 'No selected template needs a rollout' : undefined}
          >
            Roll out ready ({selectedReady.length})
          </Button>
        </div>

        {currentTask && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4" aria-live="polite">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {taskLabel(currentTask.task_name)} · {phaseLabel(progress?.phase)}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {progress?.completed ?? 0} / {progress?.total ?? progress?.templates?.length ?? 0} templates
                  {progress?.image_tag ? ` · ${progress.image_tag}` : ''}
                  {currentTask.duration ? ` · ${currentTask.duration}` : ''}
                </p>
              </div>
              <Badge
                pill
                color={
                  currentTask.status === TaskStatus.FAILED || progress?.operation_status === 'completed_with_errors'
                    ? 'red'
                    : currentTask.status === TaskStatus.FINISHED
                      ? 'green'
                      : 'blue'
                }
              >
                {progress?.operation_status || currentTask.status}
              </Badge>
            </div>
            {progress?.templates && progress.templates.length > 0 && (
              <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                {progress.templates.map((template) => (
                  <div key={template.key} className="rounded border border-gray-200 bg-white px-3 py-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-gray-800 truncate">
                        {template.display_name || template.name}
                      </span>
                      <Badge color={progressColor(template.status)}>{template.status}</Badge>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{phaseLabel(template.phase)}</p>
                    {template.error && <p className="text-xs text-red-700 mt-1 break-words">{template.error}</p>}
                  </div>
                ))}
              </div>
            )}
            {currentTask.error && <p className="text-sm text-red-700 mt-2">{currentTask.error}</p>}
          </div>
        )}
      </div>

      {loading ? (
        <ListLoading>Loading template fleet…</ListLoading>
      ) : (
        <ScrollPanel className="h-[32rem] min-h-[32rem] max-h-[32rem]">
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
                  <Tr key={template.id} className="hover:bg-gray-50">
                    <Td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${template.display_name || template.name}`}
                        checked={selected.has(template.name)}
                        onChange={() => toggleTemplate(template.name)}
                      />
                    </Td>
                    <Td>
                      <div className="text-sm font-medium text-gray-900">
                        {template.display_name || template.name}
                      </div>
                      <div className="text-xs text-gray-500">{template.name}</div>
                    </Td>
                    <Td className="text-sm text-gray-600 font-mono">
                      {template.active_version_id ? template.active_version_id.slice(0, 12) : '—'}
                    </Td>
                    <Td>
                      <div className="text-sm text-gray-700">{template.workspace_count} total</div>
                      <div className="text-xs text-gray-500">
                        {template.outdated_count > 0
                          ? `${template.outdated_count} on older version`
                          : `${template.current_count} current`}
                      </div>
                    </Td>
                    <Td>
                      <Badge color={state.color}>{state.label}</Badge>
                      <div className="text-xs text-gray-500 mt-1">{state.detail}</div>
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
                          Roll out
                        </Button>
                      </div>
                    </Td>
                  </Tr>
                );
              })}
              {templates.length === 0 && (
                <Tr>
                  <Td colSpan={6} className="py-8 text-center text-sm text-gray-500">No templates.</Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
      )}

      <div className="shrink-0 flex items-center justify-between text-sm text-gray-600">
        <span>
          Workspace details
          {workspaces.some(isOutdated) && (
            <span className="text-amber-700"> · {workspaces.filter(isOutdated).length} on an older version</span>
          )}
        </span>
        <Button size="xs" variant="ghost" onClick={() => reload()} disabled={loading}>Refresh</Button>
      </div>

      {!loading && (
        <ScrollPanel className="h-[32rem] min-h-[32rem] max-h-[32rem]">
          <Table>
            <Thead>
              <tr>
                <Th>Owner</Th><Th>Workspace</Th><Th>Template</Th><Th>Version</Th><Th>Status</Th>
              </tr>
            </Thead>
            <Tbody>
              {workspaces.map((workspace) => (
                <Tr key={workspace.id} className="hover:bg-gray-50">
                  <Td className="text-sm text-gray-900">{ownerName(workspace)}</Td>
                  <Td className="text-sm text-gray-600">{workspace.name}</Td>
                  <Td className="text-sm text-gray-600">
                    {workspace.template_display_name || workspace.template_name || '—'}
                  </Td>
                  <Td>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">{workspace.template_version_name || '—'}</span>
                      {isOutdated(workspace) ? (
                        <Badge color="yellow">outdated</Badge>
                      ) : workspace.template_version_id ? (
                        <Badge color="green">latest</Badge>
                      ) : null}
                    </div>
                  </Td>
                  <Td><WorkspaceStatusBadge status={workspace.latest_build_status} /></Td>
                </Tr>
              ))}
              {workspaces.length === 0 && (
                <Tr><Td colSpan={5} className="py-8 text-center text-sm text-gray-500">No workspaces.</Td></Tr>
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
      )}
    </>
  );
}
