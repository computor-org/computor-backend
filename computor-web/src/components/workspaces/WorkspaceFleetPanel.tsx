'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import { CoderClient } from '@/src/clients/CoderClient';
import { TaskStatus } from '@/src/types/workspaces';
import type { CoderWorkspace, CoderTemplate, TaskInfo } from '@/src/types/workspaces';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';

const coderClient = new CoderClient();

const TERMINAL = new Set<TaskStatus>([TaskStatus.FINISHED, TaskStatus.FAILED, TaskStatus.CANCELLED]);

type RunningTask = { label: string; workflowId: string; status: TaskStatus };

function ownerName(w: CoderWorkspace): string {
  return w.owner_name || w.owner_id;
}

/** "Fleet" admin tab: all workspaces across users + image/template rollout. */
export default function WorkspaceFleetPanel() {
  const notify = useNotify();

  const { data, loading, error, reload } = useResource(async () => {
    const [ws, tmpl] = await Promise.all([
      coderClient.listAllWorkspaces(),
      coderClient.listTemplates(),
    ]);
    return { workspaces: ws.workspaces, templates: tmpl.templates };
  }, []);

  const workspaces = useMemo(() => data?.workspaces ?? [], [data]);
  const templates = useMemo(() => data?.templates ?? [], [data]);

  // Active template version per template id → lets us flag workspaces still on
  // an older version (i.e. not yet carrying the newest extension).
  const activeVersionByTemplate = useMemo(() => {
    const m = new Map<string, string>();
    for (const t of templates as CoderTemplate[]) {
      if (t.active_version_id) m.set(t.id, t.active_version_id);
    }
    return m;
  }, [templates]);

  const isOutdated = useCallback(
    (w: CoderWorkspace): boolean => {
      const active = activeVersionByTemplate.get(w.template_id);
      return !!active && !!w.template_version_id && w.template_version_id !== active;
    },
    [activeVersionByTemplate],
  );

  const outdatedCount = workspaces.filter(isOutdated).length;

  // ---- admin task (build/push/rollout) with status polling -----------------
  const [imageTag, setImageTag] = useState('');
  const [task, setTask] = useState<RunningTask | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const busy = !!task && !TERMINAL.has(task.status);

  useEffect(() => {
    if (!task || TERMINAL.has(task.status)) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const info: TaskInfo = await coderClient.getAdminTask(task.workflowId);
        if (cancelled) return;
        setTask((prev) => (prev && prev.workflowId === task.workflowId ? { ...prev, status: info.status } : prev));
        if (info.status === TaskStatus.FINISHED) {
          notify(`${task.label} finished.`, 'success');
          reload();
        } else if (info.status === TaskStatus.FAILED || info.status === TaskStatus.CANCELLED) {
          notify(`${task.label} ${info.status}${info.error ? `: ${info.error}` : ''}.`, 'error');
        } else {
          pollRef.current = setTimeout(tick, 3000);
        }
      } catch {
        if (!cancelled) pollRef.current = setTimeout(tick, 3000);
      }
    };
    pollRef.current = setTimeout(tick, 2000);
    return () => {
      cancelled = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [task, notify, reload]);

  async function runBuildPush() {
    try {
      const res = await coderClient.pushTemplates({ build_images: true, image_tag: imageTag.trim() || null });
      setTask({ label: 'Build & push', workflowId: res.workflow_id, status: TaskStatus.STARTED });
      notify('Building images and pushing new template versions…', 'success');
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to start build & push', 'error');
    }
  }

  async function runRollout() {
    try {
      const res = await coderClient.rolloutWorkspaces({});
      setTask({ label: 'Rollout', workflowId: res.workflow_id, status: TaskStatus.STARTED });
      notify('Rolling out the active version to all workspaces…', 'success');
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to start rollout', 'error');
    }
  }

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      {/* Image build + template rollout controls */}
      <div className="shrink-0 bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Update workspace images</h2>
          <p className="text-sm text-gray-500 mt-1">
            Software (and the VSCode extension) is baked into the workspace images. To ship a new
            version: <strong>build &amp; push</strong> new image/template versions, then{' '}
            <strong>roll out</strong> — running workspaces rebuild now, stopped ones adopt it on
            their next start. Home directories are preserved.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="w-64">
            <label htmlFor="image-tag" className="block text-xs font-medium text-gray-700 mb-1">
              Image tag (optional)
            </label>
            <input
              id="image-tag"
              value={imageTag}
              onChange={(e) => setImageTag(e.target.value)}
              placeholder="auto (from run time)"
              className={inputCls}
              disabled={busy}
            />
          </div>
          <Button onClick={runBuildPush} disabled={busy}>
            Build &amp; push new version
          </Button>
          <Button variant="secondary" onClick={runRollout} disabled={busy}>
            Roll out to all workspaces
          </Button>
          {task && (
            <span className="text-sm text-gray-600">
              {task.label}: <span className="font-medium">{task.status}</span>
              {busy && <span className="text-gray-400"> — this can take a few minutes…</span>}
            </span>
          )}
        </div>
      </div>

      {/* Fleet table */}
      <div className="shrink-0 flex items-center justify-between text-sm text-gray-600">
        <span>
          {loading ? '—' : `${workspaces.length} workspaces`}
          {outdatedCount > 0 && (
            <span className="text-amber-700"> · {outdatedCount} on an older version</span>
          )}
        </span>
        <Button size="xs" variant="ghost" onClick={() => reload()} disabled={loading}>
          Refresh
        </Button>
      </div>

      {loading ? (
        <ListLoading>Loading fleet…</ListLoading>
      ) : (
        <ScrollPanel>
          <Table>
            <Thead>
              <tr>
                <Th>Owner</Th>
                <Th>Workspace</Th>
                <Th>Template</Th>
                <Th>Version</Th>
                <Th>Status</Th>
              </tr>
            </Thead>
            <Tbody>
              {workspaces.map((w) => {
                const outdated = isOutdated(w);
                return (
                  <Tr key={w.id} className="hover:bg-gray-50">
                    <Td className="text-sm text-gray-900">{ownerName(w)}</Td>
                    <Td className="text-sm text-gray-600">{w.name}</Td>
                    <Td className="text-sm text-gray-600">{w.template_display_name || w.template_name || '—'}</Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600">{w.template_version_name || '—'}</span>
                        {outdated ? (
                          <Badge color="yellow">outdated</Badge>
                        ) : (
                          w.template_version_id && <Badge color="green">latest</Badge>
                        )}
                      </div>
                    </Td>
                    <Td>
                      <WorkspaceStatusBadge status={w.latest_build_status} />
                    </Td>
                  </Tr>
                );
              })}
              {workspaces.length === 0 && (
                <Tr>
                  <Td colSpan={5} className="py-8 text-center text-sm text-gray-500">
                    No workspaces.
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
