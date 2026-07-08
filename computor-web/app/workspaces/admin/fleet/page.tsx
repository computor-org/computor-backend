'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import { inputCls } from '@/src/components/ui/tokens';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import { CoderClient } from '@/src/clients/CoderClient';
import { TaskStatus } from '@/src/types/workspaces';
import type { CoderWorkspace, CoderTemplate, TaskInfo } from '@/src/types/workspaces';
import { Table, Thead, Tbody, Th } from '@/src/components/ui/Table';

const coderClient = new CoderClient();

const TERMINAL = new Set<TaskStatus>([TaskStatus.FINISHED, TaskStatus.FAILED, TaskStatus.CANCELLED]);

type RunningTask = { label: string; workflowId: string; status: TaskStatus };

function ownerName(w: CoderWorkspace): string {
  return w.owner_name || w.owner_id;
}

export default function WorkspaceFleetPage() {
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
      notify('Building image and pushing a new template version…', 'success');
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
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[
            { label: 'Workspaces', href: '/workspaces' },
            { label: 'Administration', href: '/workspaces/admin' },
            { label: 'Fleet' },
          ]}
          title="Workspace Fleet"
          subtitle="Every workspace across all users, and rolling a new extension out to them."
          actions={
            <button
              onClick={() => reload()}
              disabled={loading}
              className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Refresh
            </button>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {/* Extension rollout controls */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Update the workspace extension</h2>
            <p className="text-sm text-gray-500 mt-1">
              The VSCode extension is baked into the workspace image. To ship a new version:{' '}
              <strong>build &amp; push</strong> a new image/template version, then <strong>roll it out</strong> —
              running workspaces rebuild now, stopped ones adopt it on their next start. Home directories are
              preserved.
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
            <button
              onClick={runBuildPush}
              disabled={busy}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Build &amp; push new version
            </button>
            <button
              onClick={runRollout}
              disabled={busy}
              className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50"
            >
              Roll out to all workspaces
            </button>
            {task && (
              <span className="text-sm text-gray-600">
                {task.label}: <span className="font-medium">{task.status}</span>
                {busy && <span className="text-gray-400"> — this can take a few minutes…</span>}
              </span>
            )}
          </div>
        </div>

        {/* Fleet table */}
        <div className="shrink-0 text-sm text-gray-600">
          {loading ? '—' : `${workspaces.length} workspaces`}
          {outdatedCount > 0 && (
            <span className="text-amber-700"> · {outdatedCount} on an older version</span>
          )}
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
                    <tr key={w.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">{ownerName(w)}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{w.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{w.template_name || '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-600">{w.template_version_name || '—'}</span>
                          {outdated ? (
                            <Badge color="yellow">outdated</Badge>
                          ) : (
                            w.template_version_id && <Badge color="green">latest</Badge>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <WorkspaceStatusBadge status={w.latest_build_status} size="sm" />
                      </td>
                    </tr>
                  );
                })}
                {workspaces.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500">
                      No workspaces.
                    </td>
                  </tr>
                )}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}

        <div className="shrink-0">
          <Link href="/workspaces/admin" className="text-sm text-blue-600 hover:underline">
            ← Back to workspace administration
          </Link>
        </div>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
