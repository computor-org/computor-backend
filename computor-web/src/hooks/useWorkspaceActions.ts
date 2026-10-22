'use client';

import { useCallback } from 'react';
import { CoderClient } from '@/src/clients/CoderClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import type { WorkspaceDetails, WorkspaceProvisionRequest } from '@/src/types/workspaces';
import { useUiLanguage } from './useUiLanguage';

const COPY = {
  de: {
    starting: 'Arbeitsumgebung wird gestartet …', startFailed: 'Starten fehlgeschlagen',
    stopping: 'Arbeitsumgebung wird gestoppt …', stopFailed: 'Stoppen fehlgeschlagen',
    deleted: 'Arbeitsumgebung gelöscht', deleteFailed: 'Löschen fehlgeschlagen',
    provisioned: 'Arbeitsumgebung eingerichtet', provisionFailed: 'Einrichten fehlgeschlagen',
    detailsFailed: 'Details konnten nicht geladen werden',
  },
  en: {
    starting: 'Workspace starting...', startFailed: 'Failed to start',
    stopping: 'Workspace stopping...', stopFailed: 'Failed to stop',
    deleted: 'Workspace deleted', deleteFailed: 'Failed to delete',
    provisioned: 'Workspace provisioned', provisionFailed: 'Provisioning failed',
    detailsFailed: 'Failed to fetch details',
  },
};

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
  const t = COPY[useUiLanguage()];

  const start = useCallback(
    async (owner: string, name: string) => {
      try {
        await coderClient.startWorkspace({ username: owner, workspaceName: name });
        notify(t.starting, 'success');
        setTimeout(refresh, 2000);
      } catch (err) {
        notify(err instanceof Error ? err.message : t.startFailed, 'error');
      }
    },
    [notify, refresh, t],
  );

  const stop = useCallback(
    async (owner: string, name: string) => {
      try {
        await coderClient.stopWorkspace({ username: owner, workspaceName: name });
        notify(t.stopping, 'success');
        setTimeout(refresh, 2000);
      } catch (err) {
        notify(err instanceof Error ? err.message : t.stopFailed, 'error');
      }
    },
    [notify, refresh, t],
  );

  const remove = useCallback(
    async (owner: string, name: string) => {
      try {
        await coderClient.deleteWorkspace({ username: owner, workspaceName: name });
        notify(t.deleted, 'success');
        refresh();
      } catch (err) {
        notify(err instanceof Error ? err.message : t.deleteFailed, 'error');
      }
    },
    [notify, refresh, t],
  );

  /** Provision with success/error notifications; true on success. */
  const provision = useCallback(
    async (body: WorkspaceProvisionRequest): Promise<boolean> => {
      try {
        await coderClient.provisionWorkspace({ body });
        notify(t.provisioned, 'success');
        refresh();
        return true;
      } catch (err) {
        notify(err instanceof Error ? err.message : t.provisionFailed, 'error');
        return false;
      }
    },
    [notify, refresh, t],
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
        notify(err instanceof Error ? err.message : t.detailsFailed, 'error');
        return null;
      }
    },
    [notify, t],
  );

  return { start, stop, remove, provision, openOrDetails };
}
