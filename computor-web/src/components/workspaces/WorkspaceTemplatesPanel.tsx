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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatNumber } from '@/src/utils/locale';

const coderClient = new CoderClient();

const COPY = {
  de: {
    notDeployed: 'Nicht bereitgestellt',
    disabled: 'Deaktiviert',
    available: 'Verfügbar',
    updateFailed: 'Vorlage konnte nicht aktualisiert werden',
    building: (name: string) => `${name} wird gebaut – das dauert einige Minuten.`,
    buildingMany: (n: number) => `${n} Vorlagen werden gebaut – das dauert einige Minuten.`,
    buildFailed: 'Build konnte nicht gestartet werden',
    intro1: 'Alle Vorlagen für Arbeitsumgebungen, die diese Installation mitbringt. Eine Vorlage wird Nutzenden angeboten, sobald sie ',
    deployed: 'bereitgestellt',
    intro2: ' (ihr Image ist gebaut und nach Coder gepusht) und ',
    enabled: 'aktiviert',
    intro3:
      ' ist. Wird sie deaktiviert, ist sie für Nutzende und Kurse ausgeblendet, ohne die darauf laufenden Arbeitsumgebungen anzufassen. Ressourcenlimits und Terraform-Variablen gelten ab dem nächsten Build, Platzkontingente sofort.',
    noDir:
      'Das Vorlagenverzeichnis ist vom Backend aus nicht lesbar (CODER_TEMPLATES_DIR); daher werden nur Vorlagen aufgeführt, die bereits in Coder liegen – von hier aus lässt sich nichts Neues bereitstellen.',
    firstRunTitle: 'Es sind noch keine Vorlagen für Arbeitsumgebungen bereitgestellt',
    firstRunBody:
      'Wähle die Vorlagen aus, die diese Installation anbieten soll, und stelle sie bereit. Jede baut ein Container-Image, was einige Minuten und einige Gigabyte braucht – wähle daher nur, was du brauchst. Du kannst jederzeit weitere bereitstellen.',
    starting: 'Wird gestartet …',
    selectOne: 'Wähle mindestens eine nicht bereitgestellte Vorlage aus',
    deploySelected: (n: number) => `Auswahl bereitstellen (${n})`,
    deployAllTitle: 'Alle Vorlagen dieser Installation bauen und pushen',
    deployAll: (n: number) => `Alle bereitstellen (${n})`,
    buildRunning: 'Ein Build läuft bereits – warte, bis er fertig ist.',
    loading: 'Vorlagen werden geladen …',
    selectAll: 'Alle nicht bereitgestellten Vorlagen auswählen',
    thTemplate: 'Vorlage',
    thState: 'Status',
    thEnabled: 'Aktiviert',
    thWorkspaces: 'Arbeitsumgebungen',
    thMemory: 'Speicherlimit',
    thCpu: 'CPU-Anteile',
    thSeats: 'Plätze (laufend / max.)',
    thActions: 'Aktionen',
    select: (name: string) => `${name} auswählen`,
    clonedTitle: (from: string) => `Hier aus „${from}“ erstellt; die Synchronisierung mit dem Repository fasst sie nie an`,
    clonedFrom: (from: string) => `geklont von ${from}`,
    customizedTitle: 'Auf dem Datenträger bearbeitet; wird nicht mehr aus dem Repository synchronisiert',
    customized: 'angepasst',
    noDirectory: 'kein Vorlagenverzeichnis',
    availableToUsers: (name: string) => `${name} für Nutzende verfügbar`,
    deployFirst: 'Stelle die Vorlage bereit, bevor sie Nutzenden angeboten werden kann',
    unlimited: 'Unbegrenzt',
    default: 'Standard',
    busyTitle: 'Eine andere Vorlagenoperation läuft',
    deployTitle: 'Image bauen und Vorlage nach Coder pushen',
    deploy: 'Bereitstellen',
    configure: 'Konfigurieren',
    clone: 'Klonen',
    none: 'Keine Vorlagen.',
  },
  en: {
    notDeployed: 'Not deployed',
    disabled: 'Disabled',
    available: 'Available',
    updateFailed: 'Failed to update template',
    building: (name: string) => `Building ${name} — this takes a few minutes.`,
    buildingMany: (n: number) => `Building ${n} templates — this takes a few minutes.`,
    buildFailed: 'Failed to start the build',
    intro1: 'Every workspace template this deployment ships. A template is offered to users once it is ',
    deployed: 'deployed',
    intro2: ' (its image is built and pushed to Coder) and ',
    enabled: 'enabled',
    intro3:
      '; disabling one hides it from users and courses without touching the workspaces already running on it. Resource limits and Terraform variables apply at the next build; seat quotas apply immediately.',
    noDir:
      'The templates directory is not readable from the backend (CODER_TEMPLATES_DIR), so only templates already in Coder are listed — nothing new can be deployed from here.',
    firstRunTitle: 'No workspace templates are deployed yet',
    firstRunBody:
      'Pick the ones this deployment should offer and deploy them — each builds a container image, which takes a few minutes and a few gigabytes, so it is worth choosing only what you need. You can come back and deploy more at any time.',
    starting: 'Starting…',
    selectOne: 'Select at least one undeployed template',
    deploySelected: (n: number) => `Deploy selected (${n})`,
    deployAllTitle: 'Build and push every template this deployment ships',
    deployAll: (n: number) => `Deploy all (${n})`,
    buildRunning: 'A build is already running — wait for it to finish.',
    loading: 'Loading templates…',
    selectAll: 'Select all undeployed templates',
    thTemplate: 'Template',
    thState: 'State',
    thEnabled: 'Enabled',
    thWorkspaces: 'Workspaces',
    thMemory: 'Memory cap',
    thCpu: 'CPU shares',
    thSeats: 'Seats (running / max)',
    thActions: 'Actions',
    select: (name: string) => `Select ${name}`,
    clonedTitle: (from: string) => `Created here from '${from}'; the repository sync never touches it`,
    clonedFrom: (from: string) => `cloned from ${from}`,
    customizedTitle: 'Edited on disk; no longer re-synced from the repo',
    customized: 'customized',
    noDirectory: 'no template directory',
    availableToUsers: (name: string) => `${name} available to users`,
    deployFirst: 'Deploy the template before it can be offered to users',
    unlimited: 'Unlimited',
    default: 'Default',
    busyTitle: 'Another template operation is running',
    deployTitle: 'Build the image and push the template to Coder',
    deploy: 'Deploy',
    configure: 'Configure',
    clone: 'Clone',
    none: 'No templates.',
  },
};

const TERMINAL = new Set<TaskStatus>([
  TaskStatus.FINISHED,
  TaskStatus.FAILED,
  TaskStatus.CANCELLED,
]);

/** What an admin has to do next to make this template usable, if anything. */
function availability(
  template: TemplateCatalogEntry,
  t: (typeof COPY)['en'],
): { label: string; color: 'green' | 'gray' | 'yellow' } {
  if (!template.deployed) return { label: t.notDeployed, color: 'gray' };
  if (!template.enabled) return { label: t.disabled, color: 'yellow' };
  return { label: t.available, color: 'green' };
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
  const language = useUiLanguage();
  const t = COPY[language];
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
      notify(err instanceof Error ? err.message : t.updateFailed, 'error');
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
          ? t.building(entries[0].display_name || entries[0].name)
          : t.buildingMany(dirs.length),
        'success',
      );
      setSelected(new Set());
      await refresh();
    } catch (err) {
      notify(err instanceof Error ? err.message : t.buildFailed, 'error');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 space-y-2">
        <p className="text-sm text-muted">
          {t.intro1}<span className="font-medium">{t.deployed}</span>
          {t.intro2}<span className="font-medium">{t.enabled}</span>
          {t.intro3}
        </p>
        {data && !data.catalog.templates_dir_available && (
          <p className="text-sm text-warn-text">
            {t.noDir}
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
          <h3 className="text-sm font-semibold text-fg">{t.firstRunTitle}</h3>
          <p className="mt-1 text-sm text-muted">{t.firstRunBody}</p>
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
            loadingLabel={t.starting}
            title={
              selectedNames.length === 0 ? t.selectOne : undefined
            }
            onClick={() => deploy(selectedNames)}
          >
            {t.deploySelected(selectedNames.length)}
          </Button>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => deploy(deployable)}
            title={t.deployAllTitle}
          >
            {t.deployAll(deployable.length)}
          </Button>
          {activeTask && (
            <span className="text-sm text-muted">{t.buildRunning}</span>
          )}
        </div>
      )}

      {loading ? (
        <ListLoading>{t.loading}</ListLoading>
      ) : (
        <ScrollPanel>
          <Table>
            <Thead>
              <tr>
                <Th className="w-10">
                  <input
                    type="checkbox"
                    aria-label={t.selectAll}
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
                <Th>{t.thTemplate}</Th>
                <Th>{t.thState}</Th>
                <Th>{t.thEnabled}</Th>
                <Th>{t.thWorkspaces}</Th>
                <Th>{t.thMemory}</Th>
                <Th>{t.thCpu}</Th>
                <Th>{t.thSeats}</Th>
                <Th className="text-right">{t.thActions}</Th>
              </tr>
            </Thead>
            <Tbody>
              {templates.map((template) => {
                const settings = settingsByName.get(template.name);
                const state = availability(template, t);
                // Not currently offered to users, so the row reads quieter —
                // but as a muted TITLE, never as opacity on the <tr>. Opacity
                // composites the whole subtree and a child cannot opt out, so
                // `opacity-70` here also dimmed the row's Deploy button: the one
                // control these rows exist for looked disabled while being the
                // primary action on them.
                const dimmed = !template.deployed || !template.enabled;
                return (
                  <Tr key={template.name} className="hover:bg-canvas">
                    <Td>
                      {/* Only undeployed templates are deploy targets, so only
                          they are selectable — the rest have no action here. */}
                      {isDeployable(template) && (
                        <input
                          type="checkbox"
                          aria-label={t.select(template.display_name || template.name)}
                          checked={selected.has(template.name)}
                          onChange={() => toggleSelected(template.name)}
                        />
                      )}
                    </Td>
                    <Td>
                      <div className="flex items-start gap-3">
                        <TemplateIcon template={template} size="sm" />
                        <div className="min-w-0">
                          <div className={`text-sm font-medium ${dimmed ? 'text-muted' : 'text-fg'}`}>
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
                        {/* A clone is always customized (it has no marker), so
                            say where it came from instead of "edited on disk". */}
                        {template.cloned_from ? (
                          <Badge
                            tone="info"
                            title={t.clonedTitle(template.cloned_from)}
                          >
                            {t.clonedFrom(template.cloned_from)}
                          </Badge>
                        ) : template.customized ? (
                          <Badge tone="info" title={t.customizedTitle}>
                            {t.customized}
                          </Badge>
                        ) : null}
                        {!template.dir_name && (
                          <span className="text-xs text-subtle">{t.noDirectory}</span>
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
                          label={t.availableToUsers(template.display_name || template.name)}
                          onChange={() => toggleEnabled(template.name, settings)}
                        />
                      ) : (
                        <span
                          className="text-sm text-subtle"
                          title={t.deployFirst}
                        >
                          —
                        </span>
                      )}
                    </Td>
                    <Td className="text-sm text-body">{formatNumber(template.workspace_count, language)}</Td>
                    <Td className="text-sm text-body">
                      {settings?.memory_mb ? `${formatNumber(settings.memory_mb, language)} MiB` : t.unlimited}
                    </Td>
                    <Td className="text-sm text-body">
                      {settings?.cpu_shares ? formatNumber(settings.cpu_shares, language) : t.default}
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
                            title={busy ? t.busyTitle : t.deployTitle}
                            onClick={() => deploy([template])}
                          >
                            {t.deploy}
                          </Button>
                        )}
                        {template.dir_name && (
                          <ButtonLink
                            href={`/workspaces/admin/templates/${encodeURIComponent(template.name)}`}
                            size="xs"
                            variant="secondary"
                          >
                            {t.configure}
                          </ButtonLink>
                        )}
                        {template.dir_name && (
                          <ButtonLink
                            href={`/workspaces/admin/templates/create?from=${encodeURIComponent(template.dir_name)}`}
                            size="xs"
                            variant="ghost"
                          >
                            {t.clone}
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
                    {t.none}
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
