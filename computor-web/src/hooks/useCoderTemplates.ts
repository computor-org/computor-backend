'use client';

import { useMemo } from 'react';
import { useResource } from './useResource';
import { CoderClient } from '@/src/clients/CoderClient';
import {
  buildTemplateOptions,
  type TemplateOption,
} from '@/src/components/workspaces/templateOptions';
import type { CoderTemplate, TemplatePreparation } from '@/src/types/workspaces';

const coderClient = new CoderClient();

/**
 * Workspace templates from Coder (GET /coder/templates), as `options` that
 * already know whether each one can be used — see templateOptions.ts.
 *
 * The endpoint is scoped: managers see everything, workspace:templates holders
 * see globally enabled templates, course members see what their courses allow,
 * and anyone else gets a 403 — so gate the caller with `enabled` where that is
 * knowable up front.
 *
 * Pass `refetchInterval` on a page a user may sit on while an administrator
 * deploys something: that is the only way a preparing template's stage moves,
 * or a finished one turns into a card they can click.
 */
export function useCoderTemplates(
  opts: { enabled?: boolean; refetchInterval?: number } = {},
) {
  const { data, loading, error, reload, refresh } = useResource(
    async () => {
      const response = await coderClient.listTemplates();
      return {
        templates: (response.templates ?? []) as CoderTemplate[],
        preparing: (response.preparing ?? []) as TemplatePreparation[],
      };
    },
    [],
    { enabled: opts.enabled, refetchInterval: opts.refetchInterval },
  );

  const options: TemplateOption[] = useMemo(
    () => buildTemplateOptions(data?.templates ?? [], data?.preparing ?? []),
    [data],
  );

  return {
    templates: data?.templates ?? [],
    preparing: data?.preparing ?? [],
    options,
    /** The listing answered — distinguishes "no templates" from "not asked yet". */
    answered: data !== null || error !== null,
    loading,
    error,
    reload,
    refresh,
  };
}
