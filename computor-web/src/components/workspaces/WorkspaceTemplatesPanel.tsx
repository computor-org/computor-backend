'use client';

import { useMemo, useState } from 'react';
import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import Toggle from '@/src/components/ui/Toggle';
import { useNotify } from '@/src/contexts/NotificationContext';
import { CoderClient } from '@/src/clients/CoderClient';
import { TaskStatus } from '@/src/types/workspaces';
import type {
  TemplateCatalogEntry,
  WorkspaceTemplateSettings,
} from '@/src/types/workspaces';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import TemplateIcon from './TemplateIcon';
import TemplateTaskProgress from './TemplateTaskProgress';

const coderClient = new CoderClient();

const TERMINAL = new Set<TaskStatus>([
  TaskStatus.FINISHED,
  TaskStatus.FAILED,
  TaskStatus.CANCELLED,
]);

/** What an admin has to do next to make this template usable, if anything. */
function availability(template: TemplateCatalogEntry): { label: string; color: 'green' | 'gray' | 'yellow' } {
  if (!template.deployed) return { label: 'Not deployed', color: 'gray' };
  if (!template.enabled) return { label: 'Disabled', color: 'yellow' };
  return { label: 'Available', color: 'green' };
}

/** A template can only be built if this deployment ships its directory. */
function isDeployable(template: TemplateCatalogEntry): boolean {
  return !template.deployed && Boolean(template.dir_name);
}

/**
 * The template catalog: everything the deployment ships, deployed or not, with
 * the two switches that decide whether a user can pick it — is its image built
 * and pushed to Coder, and is it enabled.
 *
 * This is where which templates a deployment offers gets decided, including the
 * first time. Nothing is deployed automatically: building every shipped image
 * is tens of gigabytes, and a site that only teaches Python should not wait on
 * MATLAB to find that out. So a fresh system arrives with an empty Coder and
 * this list of candidates, and someone picks.
 */
export default function WorkspaceTemplatesPanel() {
  const notify = useNotify();
  const [toggling, setToggling] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  const { data, loading, error, reload, refresh } = useResource(
    async () => {
      const [catalog, settings, tasks] = await Promise.all([
        coderClient.listTemplateCatalog(),
        coderClient.listTemplateSettings(),
        coderClient.listAdminTasks(5),
      ]);
      return { catalog, settings: settings.settings, tasks: tasks.tasks };
    },
    [],
    { refetchInterval: 5000 },
  );

  const settingsByName = useMemo(
    () => new Map((data?.settings ?? []).map((row) => [row.template_name, row])),
    [data],
  );

  const templates = useMemo(() => data?.catalog.templates ?? [], [data]);
  const deployable = useMemo(() => templates.filter(isDeployable), [templates]);
  const nothingDeployed = templates.length > 0 && templates.every((t) => !t.deployed);

  // A deploy is a build+push like any other, so the fleet's task feed already
  // reports it — surfacing it here means whoever deploys a template from this
  // tab watches it finish here instead of guessing or switching tabs.
  const activeTask = (data?.tasks ?? []).find((task) => !TERMINAL.has(task.status)) ?? null;
  const busy = Boolean(activeTask) || submitting;

  // Only ever holds deployable names, so a refresh that flips one to deployed
  // (or a stale tick) can never leave it selected for a second build.
  const selectedNames = useMemo(
    () => deployable.filter((t) => selected.has(t.name)),
    [deployable, selected],
  );

  function toggleSelected(name: string) {
    setSelected((previous) => {
      const next = new Set(previous);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

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

  /** Build these templates' images and push them, making them selectable. */
  async function deploy(entries: TemplateCatalogEntry[]) {
    // The build activity resolves against the DIRECTORY name, not Coder's.
    const dirs = entries.map((entry) => entry.dir_name).filter((dir): dir is string => Boolean(dir));
    if (dirs.length === 0) return;
    setSubmitting(true);
    try {
      await coderClient.pushTemplates({ templates: dirs, build_images: true });
      notify(
        dirs.length === 1
          ? `Building ${entries[0].display_name || entries[0].name} — this takes a few minutes.`
          : `Building ${dirs.length} templates — this takes a few minutes.`,
        'success',
      );
      setSelected(new Set());
      await refresh();
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Failed to start the build', 'error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 space-y-2">
        <p className="text-sm text-muted">
          Every workspace template this deployment ships. A template is offered to users once it
          is <span className="font-medium">deployed</span> (its image is built and pushed to
          Coder) and <span className="font-medium">enabled</span>; disabling one hides it from
          users and courses without touching the workspaces already running on it. Resource
          limits and Terraform variables apply at the next build; seat quotas apply immediately.
        </p>
        {data && !data.catalog.templates_dir_available && (
          <p className="text-sm text-warn-text">
            The templates directory is not readable from the backend
            (CODER_TEMPLATES_DIR), so only templates already in Coder are listed — nothing new
            can be deployed from here.
          </p>
        )}
      </div>

      {/*
        First run. Nothing is deployed automatically, so a fresh system lands
        here with an empty Coder — say so plainly and put the choice in reach,
        rather than leaving a table of "Not deployed" rows to be interpreted.
      */}
      {nothingDeployed && !activeTask && (
        <div className="shrink-0 rounded-lg border border-accent-line bg-accent-wash p-4">
          <h3 className="text-sm font-semibold text-fg">
            No workspace templates are deployed yet
          </h3>
          <p className="mt-1 text-sm text-muted">
            Pick the ones this deployment should offer and deploy them — each builds a
            container image, which takes a few minutes and a few gigabytes, so it is worth
            choosing only what you need. You can come back and deploy more at any time.
          </p>
        </div>
      )}

      {activeTask && (
        <div className="shrink-0">
          <TemplateTaskProgress task={activeTask} />
        </div>
      )}

      {deployable.length > 0 && (
        <div className="shrink-0 flex flex-wrap items-center gap-3">
          <Button
            disabled={busy || selectedNames.length === 0}
            loading={submitting}
            loadingLabel="Starting…"
            title={
              selectedNames.length === 0
                ? 'Select at least one undeployed template'
                : undefined
            }
            onClick={() => deploy(selectedNames)}
          >
            Deploy selected ({selectedNames.length})
          </Button>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => deploy(deployable)}
            title="Build and push every template this deployment ships"
          >
            Deploy all ({deployable.length})
          </Button>
          {activeTask && (
            <span className="text-sm text-muted">
              A build is already running — wait for it to finish.
            </span>
          )}
        </div>
      )}

      {loading ? (
        <ListLoading>Loading templates…</ListLoading>
      ) : (
        <ScrollPanel>
          <Table>
            <Thead>
              <tr>
                <Th className="w-10">
                  <input
                    type="checkbox"
                    aria-label="Select all undeployed templates"
                    disabled={deployable.length === 0}
                    checked={
                      deployable.length > 0 && selectedNames.length === deployable.length
                    }
                    onChange={(event) =>
                      setSelected(
                        event.target.checked
                          ? new Set(deployable.map((entry) => entry.name))
                          : new Set(),
                      )
                    }
                  />
                </Th>
                <Th>Template</Th>
                <Th>State</Th>
                <Th>Enabled</Th>
                <Th>Workspaces</Th>
                <Th>Memory cap</Th>
                <Th>CPU shares</Th>
                <Th>Seats (running / max)</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {templates.map((template) => {
                const settings = settingsByName.get(template.name);
                const state = availability(template);
                const dimmed = !template.deployed || !template.enabled;
                return (
                  <Tr key={template.name} className={`hover:bg-canvas ${dimmed ? 'opacity-70' : ''}`}>
                    <Td>
                      {/* Only undeployed templates are deploy targets, so only
                          they are selectable — the rest have no action here. */}
                      {isDeployable(template) && (
                        <input
                          type="checkbox"
                          aria-label={`Select ${template.display_name || template.name}`}
                          checked={selected.has(template.name)}
                          onChange={() => toggleSelected(template.name)}
                        />
                      )}
                    </Td>
                    <Td>
                      <div className="flex items-start gap-3">
                        <TemplateIcon template={template} size="sm" />
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-fg">
                            {template.display_name || template.name}
                          </div>
                          <div className="text-xs text-muted">{template.name}</div>
                          {template.description && (
                            <div className="text-xs text-subtle mt-0.5 max-w-md">
                              {template.description}
                            </div>
                          )}
                        </div>
                      </div>
                    </Td>
                    <Td>
                      <div className="flex flex-col items-start gap-1">
                        <Badge color={state.color} pill>{state.label}</Badge>
                        {template.customized && (
                          <Badge color="blue" title="Edited on disk; no longer re-synced from the repo">
                            customized
                          </Badge>
                        )}
                        {!template.dir_name && (
                          <span className="text-xs text-subtle">no template directory</span>
                        )}
                      </div>
                    </Td>
                    <Td>
                      {/*
                        No switch until the template is deployed. A template with
                        no settings row counts as enabled, so a disabled switch
                        would sit here in the ON position for something users
                        cannot pick — claiming the opposite of the truth.
                      */}
                      {template.deployed ? (
                        <Toggle
                          checked={template.enabled}
                          busy={toggling === template.name}
                          label={`${template.display_name || template.name} available to users`}
                          onChange={() => toggleEnabled(template.name, settings)}
                        />
                      ) : (
                        <span
                          className="text-sm text-subtle"
                          title="Deploy the template before it can be offered to users"
                        >
                          —
                        </span>
                      )}
                    </Td>
                    <Td className="text-sm text-body">{template.workspace_count}</Td>
                    <Td className="text-sm text-body">
                      {settings?.memory_mb ? `${settings.memory_mb} MiB` : 'Unlimited'}
                    </Td>
                    <Td className="text-sm text-body">
                      {settings?.cpu_shares ? settings.cpu_shares : 'Default'}
                    </Td>
                    <Td className="text-sm text-body">
                      {template.running_workspace_count} / {settings?.max_running_workspaces ?? '∞'}
                    </Td>
                    <Td>
                      <div className="flex justify-end gap-2">
                        {isDeployable(template) && (
                          <Button
                            size="xs"
                            disabled={busy}
                            title={
                              busy
                                ? 'Another template operation is running'
                                : 'Build the image and push the template to Coder'
                            }
                            onClick={() => deploy([template])}
                          >
                            Deploy
                          </Button>
                        )}
                        {template.dir_name && (
                          <ButtonLink
                            href={`/workspaces/admin/templates/${encodeURIComponent(template.name)}`}
                            size="xs"
                            variant="secondary"
                          >
                            Configure
                          </ButtonLink>
                        )}
                      </div>
                    </Td>
                  </Tr>
                );
              })}
              {templates.length === 0 && (
                <Tr>
                  <Td colSpan={9} className="py-8 text-center text-sm text-muted">
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
