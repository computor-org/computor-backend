'use client';

import { useMemo, useState } from 'react';
import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import { useNotify } from '@/src/contexts/NotificationContext';
import { CoderClient } from '@/src/clients/CoderClient';
import { WorkspaceBuildStatus } from '@/src/types/workspaces';
import type { CoderWorkspace, WorkspaceTemplateSettings } from '@/src/types/workspaces';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';

const coderClient = new CoderClient();

/** Builds counted against a template's seat quota (mirrors the backend). */
const ACTIVE_BUILD_STATUSES = new Set<WorkspaceBuildStatus>([
  WorkspaceBuildStatus.PENDING,
  WorkspaceBuildStatus.STARTING,
  WorkspaceBuildStatus.RUNNING,
  WorkspaceBuildStatus.SUCCEEDED,
]);

function isActive(workspace: CoderWorkspace): boolean {
  return (
    workspace.latest_build_transition === 'start' &&
    workspace.latest_build_status != null &&
    ACTIVE_BUILD_STATUSES.has(workspace.latest_build_status)
  );
}

/** Per-template resource limits + seat quota overview, linking to the editor. */
export default function WorkspaceTemplatesPanel() {
  const notify = useNotify();
  const [toggling, setToggling] = useState<string | null>(null);
  const { data, loading, error, reload } = useResource(
    async () => {
      const [templates, settings, workspaces] = await Promise.all([
        coderClient.listTemplates(),
        coderClient.listTemplateSettings(),
        coderClient.listAllWorkspaces(),
      ]);
      return {
        templates: templates.templates,
        settings: settings.settings,
        workspaces: workspaces.workspaces,
      };
    },
    [],
    { refetchInterval: 5000 },
  );

  const settingsByName = useMemo(
    () => new Map((data?.settings ?? []).map((row) => [row.template_name, row])),
    [data],
  );
  const runningByTemplate = useMemo(() => {
    const counts = new Map<string, number>();
    for (const workspace of data?.workspaces ?? []) {
      if (!workspace.template_name || !isActive(workspace)) continue;
      counts.set(workspace.template_name, (counts.get(workspace.template_name) ?? 0) + 1);
    }
    return counts;
  }, [data]);

  const templates = data?.templates ?? [];

  // The settings PUT is a full replace, so the toggle re-sends the row's
  // current values (or the defaults when no row exists) with enabled flipped.
  async function toggleEnabled(templateName: string, settings?: WorkspaceTemplateSettings) {
    setToggling(templateName);
    try {
      await coderClient.updateTemplateSettings({
        templateName,
        body: {
          enabled: !(settings?.enabled ?? true),
          memory_mb: settings?.memory_mb ?? null,
          cpu_shares: settings?.cpu_shares ?? null,
          max_running_workspaces: settings?.max_running_workspaces ?? null,
          template_variables: settings?.template_variables ?? {},
        },
      });
      reload();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to update template', 'error');
    } finally {
      setToggling(null);
    }
  }

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <p className="shrink-0 text-sm text-gray-500">
        Per-template container resource limits, running-workspace seat quotas, and Terraform
        configuration. Limits and variable changes apply at the next{' '}
        <span className="font-medium">Build &amp; push</span> (Fleet tab); seat quotas apply
        immediately. Disabled templates are hidden from users and courses and cannot be
        provisioned; running workspaces keep working.
      </p>

      {loading ? (
        <ListLoading>Loading templates…</ListLoading>
      ) : (
        <ScrollPanel className="h-[36rem] min-h-[36rem] max-h-[36rem]">
          <Table>
            <Thead>
              <tr>
                <Th>Template</Th>
                <Th>Enabled</Th>
                <Th>Memory cap</Th>
                <Th>CPU shares</Th>
                <Th>Seats (running / max)</Th>
                <Th>Extra variables</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {templates.map((template) => {
                const settings = settingsByName.get(template.name);
                const enabled = settings?.enabled ?? true;
                const running = runningByTemplate.get(template.name) ?? 0;
                const extraCount = Object.keys(settings?.template_variables ?? {}).length;
                return (
                  <Tr key={template.id} className={`hover:bg-gray-50 ${enabled ? '' : 'opacity-60'}`}>
                    <Td>
                      <div className="text-sm font-medium text-gray-900">
                        {template.display_name || template.name}
                      </div>
                      <div className="text-xs text-gray-500">{template.name}</div>
                    </Td>
                    <Td>
                      <Button
                        size="xs"
                        variant={enabled ? 'secondary' : 'primary'}
                        disabled={toggling === template.name}
                        onClick={() => toggleEnabled(template.name, settings)}
                      >
                        {enabled ? 'Disable' : 'Enable'}
                      </Button>
                    </Td>
                    <Td className="text-sm text-gray-700">
                      {settings?.memory_mb ? `${settings.memory_mb} MiB` : 'Unlimited'}
                    </Td>
                    <Td className="text-sm text-gray-700">
                      {settings?.cpu_shares ? settings.cpu_shares : 'Default'}
                    </Td>
                    <Td className="text-sm text-gray-700">
                      {running} / {settings?.max_running_workspaces ?? '∞'}
                    </Td>
                    <Td className="text-sm text-gray-700">
                      {extraCount > 0 ? extraCount : '—'}
                    </Td>
                    <Td>
                      <div className="flex justify-end">
                        <ButtonLink
                          href={`/workspaces/admin/templates/${encodeURIComponent(template.name)}`}
                          size="xs"
                          variant="secondary"
                        >
                          Configure
                        </ButtonLink>
                      </div>
                    </Td>
                  </Tr>
                );
              })}
              {templates.length === 0 && (
                <Tr>
                  <Td colSpan={7} className="py-8 text-center text-sm text-gray-500">
                    No templates.
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
