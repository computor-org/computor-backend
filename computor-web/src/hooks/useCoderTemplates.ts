'use client';

import { useResource } from './useResource';
import { CoderClient } from '@/src/clients/CoderClient';
import type { CoderTemplate } from '@/src/types/workspaces';

const coderClient = new CoderClient();

/**
 * Workspace templates from Coder (GET /coder/templates). Maintainer/admin
 * only — the backend gates the endpoint on workspace:templates, so gate the
 * caller with `enabled` (e.g. isWorkspaceMaintainer) to avoid guaranteed 403s.
 */
export function useCoderTemplates(opts: { enabled?: boolean } = {}) {
  const { data, loading, error, reload } = useResource(
    async () => (await coderClient.listTemplates()).templates,
    [],
    { enabled: opts.enabled },
  );
  return { templates: (data ?? []) as CoderTemplate[], loading, error, reload };
}
