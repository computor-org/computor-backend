'use client';

import { useState } from 'react';
import { ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { CoderClient } from '@/src/clients/CoderClient';
import type { WorkspaceVolume } from '@/src/types/workspaces';

const coderClient = new CoderClient();

function formatSize(bytes?: number | null): string {
  if (bytes == null) return 'unknown';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/** Who a volume belongs to, or why we cannot say. */
function owner(volume: WorkspaceVolume): string {
  if (volume.kind === 'home') return volume.user_name || volume.user_id || '—';
  return volume.workspace_name || '—';
}

/**
 * Home and scratch volumes: what exists, how big it is, and the two things a
 * maintainer needs to do with them.
 *
 * These volumes are deliberately not Terraform-managed so deleting a workspace
 * can never destroy a home — which is also why nothing else in the platform
 * shows them.
 */
export default function WorkspaceVolumesPanel() {
  const notify = useNotify();
  const [busy, setBusy] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<WorkspaceVolume | null>(null);

  const { data, loading, error, reload } = useResource(() => coderClient.listVolumes(), []);

  async function run(action: 'delete' | 'repair', volume: WorkspaceVolume) {
    setBusy(volume.name);
    try {
      const result =
        action === 'delete'
          ? await coderClient.deleteVolume({ name: volume.name })
          : await coderClient.repairVolume({ name: volume.name });
      notify(result.message, 'success');
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : `Failed to ${action} the volume`, 'error');
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <ListLoading>Reading volumes…</ListLoading>;

  const volumes = data?.volumes ?? [];

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 bg-surface rounded-lg border border-rule p-5">
        <h2 className="text-lg font-semibold text-fg">Workspace volumes</h2>
        <p className="text-sm text-muted mt-1">
          A <span className="font-medium">home</span> volume holds one user&apos;s files and is
          shared by all of their workspaces; deleting a workspace never touches it, which is why
          reclaiming one has to happen here. A <span className="font-medium">scratch</span> volume
          belongs to a single throwaway workspace and goes away with it.
          {data ? ` ${formatSize(data.total_bytes)} in total.` : ''}
        </p>
        {data?.unresolved && (
          <p className="mt-2 text-sm text-amber-700">
            Coder is unreachable, so owners could not be resolved. Nothing is marked as an orphan —
            a missing owner here would only mean the lookup failed.
          </p>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-auto bg-surface rounded-lg border border-rule">
        <table className="min-w-full text-sm">
          <thead className="bg-canvas text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-2">Volume</th>
              <th className="px-4 py-2">Kind</th>
              <th className="px-4 py-2">Belongs to</th>
              <th className="px-4 py-2 text-right">Size</th>
              <th className="px-4 py-2">State</th>
              <th className="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule-soft">
            {volumes.map((volume) => (
              <tr key={volume.name} className={volume.orphaned ? 'bg-amber-50/40' : undefined}>
                <td className="px-4 py-2 font-mono text-xs text-body">{volume.name}</td>
                <td className="px-4 py-2">{volume.kind}</td>
                <td className="px-4 py-2">{owner(volume)}</td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {formatSize(volume.size_bytes)}
                </td>
                <td className="px-4 py-2">
                  {volume.in_use && (
                    <span className="inline-flex items-center rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                      In use
                    </span>
                  )}
                  {volume.orphaned && (
                    <span
                      className="ml-1 inline-flex items-center rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
                      title="The user or workspace this volume was created for no longer exists."
                    >
                      Orphaned
                    </span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <div className="flex justify-end gap-2">
                    {volume.kind === 'home' && (
                      <Button
                        variant="ghost"
                        onClick={() => run('repair', volume)}
                        loading={busy === volume.name}
                        title="Give every file back to the workspace user. Needed when a workspace wrote files as root and the template has since lost root access."
                      >
                        Repair ownership
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      onClick={() => setConfirming(volume)}
                      disabled={busy !== null || volume.in_use === true}
                      title={
                        volume.in_use
                          ? 'A container is using this volume — stop the workspace first.'
                          : undefined
                      }
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {volumes.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-sm text-muted">
                  No workspace volumes.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {confirming && (
        <ConfirmDeleteDialog
          title="Delete volume"
          message={
            confirming.kind === 'home'
              ? `This deletes every file of ${owner(confirming)} — across all of their workspaces, not just one. It cannot be undone.`
              : `This deletes the scratch volume of ${owner(confirming)}. It cannot be undone.`
          }
          confirmWord={confirming.name}
          onConfirm={async () => {
            await run('delete', confirming);
            setConfirming(null);
          }}
          onClose={() => setConfirming(null)}
        />
      )}
    </>
  );
}
