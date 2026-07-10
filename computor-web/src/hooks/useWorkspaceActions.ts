'use client';

import { useCallback } from 'react';
import { CoderClient } from '@/src/clients/CoderClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import type { WorkspaceDetails, WorkspaceProvisionRequest } from '@/src/types/workspaces';

const coderClient = new CoderClient();

/**
 * The workspace lifecycle actions (start / stop / delete / provision / open)
 * with the notification + delayed-refresh behavior that used to be
 * copy-pasted across the workspaces pages. `refresh` is called after each
 * action — for start/stop with a short delay, since Coder needs a moment
 * before the new build status is visible.
 */
export function useWorkspaceActions(refresh: () => void) {
  const notify = useNotify();

  const start = useCallback(
    async (owner: string, name: string) => {
      try {
        await coderClient.startWorkspace({ username: owner, workspaceName: name });
        notify('Workspace starting...', 'success');
        setTimeout(refresh, 2000);
      } catch (err) {
        notify(err instanceof Error ? err.message : 'Failed to start', 'error');
      }
    },
    [notify, refresh],
  );

  const stop = useCallback(
    async (owner: string, name: string) => {
      try {
        await coderClient.stopWorkspace({ username: owner, workspaceName: name });
        notify('Workspace stopping...', 'success');
        setTimeout(refresh, 2000);
      } catch (err) {
        notify(err instanceof Error ? err.message : 'Failed to stop', 'error');
      }
    },
    [notify, refresh],
  );

  const remove = useCallback(
    async (owner: string, name: string) => {
      try {
        await coderClient.deleteWorkspace({ username: owner, workspaceName: name });
        notify('Workspace deleted', 'success');
        refresh();
      } catch (err) {
        notify(err instanceof Error ? err.message : 'Failed to delete', 'error');
      }
    },
    [notify, refresh],
  );

  /** Provision with success/error notifications; true on success. */
  const provision = useCallback(
    async (body: WorkspaceProvisionRequest): Promise<boolean> => {
      try {
        await coderClient.provisionWorkspace({ body });
        notify('Workspace provisioned', 'success');
        refresh();
        return true;
      } catch (err) {
        notify(err instanceof Error ? err.message : 'Provisioning failed', 'error');
        return false;
      }
    },
    [notify, refresh],
  );

  /**
   * Open a running workspace in a new tab; for a workspace that is not
   * running (or has no URL yet) return its details so the caller can show
   * them instead. Returns null when the workspace was opened or on error
   * (already notified).
   */
  const openOrDetails = useCallback(
    async (owner: string, name: string): Promise<WorkspaceDetails | null> => {
      try {
        const details = await coderClient.getWorkspaceDetails({ username: owner, workspaceName: name });
        const url = details.code_server_url || details.access_url;
        if (details.status === 'running' && url) {
          window.open(url, '_blank');
          return null;
        }
        return details;
      } catch (err) {
        notify(err instanceof Error ? err.message : 'Failed to fetch details', 'error');
        return null;
      }
    },
    [notify],
  );

  return { start, stop, remove, provision, openOrDetails };
}
