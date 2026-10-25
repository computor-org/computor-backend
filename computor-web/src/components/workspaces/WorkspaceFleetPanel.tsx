'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge, { type BadgeColor } from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import TemplateTaskProgress from '@/src/components/workspaces/TemplateTaskProgress';
import { phaseLabel } from '@/src/components/workspaces/templateTaskStage';
import { CoderClient } from '@/src/clients/CoderClient';
import { TaskStatus } from '@/src/types/workspaces';
import type {
  CoderTemplateFleetStatus,
  CoderWorkspace,
  TaskInfo,
} from '@/src/types/workspaces';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
import { formatNumber } from '@/src/utils/locale';

const coderClient = new CoderClient();

const COPY = {
  de: {
    unavailable: 'Nicht verfügbar',
    noActiveVersion: 'Keine aktive Vorlagenversion',
    runningOutdated: 'Läuft veraltet',
    updatable: (n: number) =>
      n === 1
        ? '1 laufende Arbeitsumgebung kann jetzt aktualisiert werden'
        : `${n} laufende Arbeitsumgebungen können jetzt aktualisiert werden`,
    scheduled: 'Geplant',
    updateOnStart: (n: number) => `${n} Aktualisierung${n === 1 ? '' : 'en'} beim nächsten Start`,
    upToDate: 'Aktuell',
    noRollout: 'Kein Rollout nötig',
    buildQueued: (n: number) =>
      `Build & Push für ${n} ${n === 1 ? 'Vorlage' : 'Vorlagen'} eingereiht.`,
    buildFailed: 'Build & Push konnte nicht gestartet werden',
    rolloutQueued: (n: number) =>
      `Rollout für ${n} ${n === 1 ? 'Vorlage' : 'Vorlagen'} eingereiht.`,
    rolloutFailed: 'Rollout konnte nicht gestartet werden',
    checkingCoder: 'Coder wird geprüft …',
    coderHealthy: 'Coder läuft',
    coderUnreachable: 'Coder nicht erreichbar',
    workspacesCount: (n: string) => `${n} Arbeitsumgebungen`,
    updatesHeading: 'Vorlagen-Updates',
    updatesIntro1:
      'Erstellt und aktiviert eine neue Version für die ausgewählten Vorlagen. Ein Push plant das Update der Flotte von selbst: Jede Arbeitsumgebung übernimmt die neue Version beim nächsten Start. „Laufende jetzt aktualisieren“ baut zusätzlich Arbeitsumgebungen neu, die gerade laufen. Das unterbricht alle, die darin arbeiten, also nutze es nur für Korrekturen, die nicht warten können. Hier erscheinen nur Vorlagen, die bereits in Coder bereitgestellt sind. Um eine zum ersten Mal bereitzustellen, nutze den Tab ',
    updatesIntro2: '.',
    templatesTab: 'Vorlagen',
    imageTag: 'Image-Tag (erweitert, optional)',
    imageTagPlaceholder: 'automatisch (aus der Laufzeit)',
    rebuildAll: 'Alle Layer neu bauen (langsam)',
    selectOne: 'Wähle mindestens eine Vorlage aus',
    buildPushSelected: (n: number) => `Ausgewählte bauen & pushen (${n})`,
    noOutdated: 'Keine ausgewählte Vorlage hat laufende veraltete Arbeitsumgebungen',
    updateRunningNow: (n: number) => `Laufende jetzt aktualisieren (${n})`,
    loadingFleet: 'Vorlagen-Flotte wird geladen …',
    selectAll: 'Alle Vorlagen auswählen',
    template: 'Vorlage',
    activeVersion: 'Aktive Version',
    workspaces: 'Arbeitsumgebungen',
    readiness: 'Bereitschaft',
    actions: 'Aktionen',
    failed: 'Fehlgeschlagen',
    rollingOut: 'Rollout läuft',
    versionReady: 'Version bereit',
    pushing: 'Wird gepusht',
    building: 'Wird gebaut',
    select: (name: string) => `${name} auswählen`,
    total: (n: number) => `${n} insgesamt`,
    onOlder: (n: number) => `${n} mit älterer Version`,
    current: (n: number) => `${n} aktuell`,
    buildPush: 'Build & Push',
    updateRunning: 'Laufende aktualisieren',
    noTemplates: 'Keine Vorlagen.',
    details: 'Details zu den Arbeitsumgebungen',
    ofTotal: (shown: number, all: number) => ` · ${shown} von ${all}`,
    onOlderVersion: (n: number) => ` · ${n} mit älterer Version`,
    filterPlaceholder: 'Nach Besitzer oder Vorlage filtern …',
    filterLabel: 'Arbeitsumgebungen filtern',
    refresh: 'Aktualisieren',
    owner: 'Besitzer',
    workspace: 'Arbeitsumgebung',
    version: 'Version',
    status: 'Status',
    coderUser: (name: string) => `Coder-Benutzer: ${name}`,
    outdated: 'veraltet',
    latest: 'neueste',
    noWorkspaces: 'Keine Arbeitsumgebungen.',
    noMatch: 'Keine Arbeitsumgebungen entsprechen dem Filter.',
  },
  en: {
    unavailable: 'Unavailable',
    noActiveVersion: 'No active template version',
    runningOutdated: 'Running outdated',
    updatable: (n: number) =>
      `${n} running workspace${n === 1 ? '' : 's'} can be updated now`,
    scheduled: 'Scheduled',
    updateOnStart: (n: number) => `${n} update on next start`,
    upToDate: 'Up to date',
    noRollout: 'No rollout needed',
    buildQueued: (n: number) => `Build & push queued for ${n} template${n === 1 ? '' : 's'}.`,
    buildFailed: 'Failed to start build & push',
    rolloutQueued: (n: number) => `Rollout queued for ${n} template${n === 1 ? '' : 's'}.`,
    rolloutFailed: 'Failed to start rollout',
    checkingCoder: 'Checking Coder…',
    coderHealthy: 'Coder healthy',
    coderUnreachable: 'Coder unreachable',
    workspacesCount: (n: string) => `${n} workspaces`,
    updatesHeading: 'Template updates',
    updatesIntro1:
      'Build and activate a new version for selected templates. A push schedules the fleet update by itself: every workspace adopts the new version on its next start. Update running now additionally rebuilds workspaces that are up right now — that interrupts whoever is working in them, so save it for fixes that cannot wait. Only templates already deployed to Coder appear here — to deploy one for the first time, use the ',
    updatesIntro2: ' tab.',
    templatesTab: 'Templates',
    imageTag: 'Image tag (advanced, optional)',
    imageTagPlaceholder: 'auto (from run time)',
    rebuildAll: 'Rebuild all layers (slow)',
    selectOne: 'Select at least one template',
    buildPushSelected: (n: number) => `Build & push selected (${n})`,
    noOutdated: 'No selected template has running outdated workspaces',
    updateRunningNow: (n: number) => `Update running now (${n})`,
    loadingFleet: 'Loading template fleet…',
    selectAll: 'Select all templates',
    template: 'Template',
    activeVersion: 'Active version',
    workspaces: 'Workspaces',
    readiness: 'Readiness',
    actions: 'Actions',
    failed: 'Failed',
    rollingOut: 'Rolling out',
    versionReady: 'Version ready',
    pushing: 'Pushing',
    building: 'Building',
    select: (name: string) => `Select ${name}`,
    total: (n: number) => `${n} total`,
    onOlder: (n: number) => `${n} on older version`,
    current: (n: number) => `${n} current`,
    buildPush: 'Build & push',
    updateRunning: 'Update running',
    noTemplates: 'No templates.',
    details: 'Workspace details',
    ofTotal: (shown: number, all: number) => ` · ${shown} of ${all}`,
    onOlderVersion: (n: number) => ` · ${n} on an older version`,
    filterPlaceholder: 'Filter by owner or template…',
    filterLabel: 'Filter workspaces',
    refresh: 'Refresh',
    owner: 'Owner',
    workspace: 'Workspace',
    version: 'Version',
    status: 'Status',
    coderUser: (name: string) => `Coder user: ${name}`,
    outdated: 'outdated',
    latest: 'latest',
    noWorkspaces: 'No workspaces.',
    noMatch: 'No workspaces match the filter.',
  },
};
const TERMINAL = new Set<TaskStatus>([
  TaskStatus.FINISHED,
  TaskStatus.FAILED,
  TaskStatus.CANCELLED,
]);

/**
 * Who a workspace belongs to, in the order a maintainer can actually read.
 *
 * Coder only knows owners by their encoded username (`u` + base32 of the
 * Computor user id — `coder/naming.py`), which is unreadable; the backend
 * resolves it for this view. The encoded name is still what addresses the
 * workspace in Coder's own UI and URLs, so it stays reachable on hover rather
 * than taking the line.
 */
function ownerLines(workspace: CoderWorkspace): { primary: string; secondary: string | null } {
  const name = workspace.owner_display_name;
  const email = workspace.owner_email;
  const primary = name || email || workspace.owner_name || workspace.owner_id;
  return { primary, secondary: name && email ? email : null };
}

/** Everything about a workspace the search box matches on. */
function searchHaystack(workspace: CoderWorkspace): string {
  return [
    workspace.owner_display_name,
    workspace.owner_email,
    workspace.owner_name,
    workspace.name,
    workspace.template_display_name,
    workspace.template_name,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function readiness(template: CoderTemplateFleetStatus, language: UiLanguage): {
  label: string;
  color: BadgeColor;
  detail: string;
} {
  const t = COPY[language];
  switch (template.rollout_state) {
    case 'unavailable':
      return { label: t.unavailable, color: 'gray', detail: t.noActiveVersion };
    case 'ready':
      return {
        label: t.runningOutdated,
        color: 'yellow',
        detail: t.updatable(template.actionable_count),
      };
    case 'scheduled_on_start':
      return {
        label: t.scheduled,
        color: 'blue',
        detail: t.updateOnStart(template.scheduled_on_start_count),
      };
    default:
      return { label: t.upToDate, color: 'green', detail: t.noRollout };
  }
}

/** Privileged template update controls plus the detailed workspace fleet. */
export default function WorkspaceFleetPanel() {
  const language = useUiLanguage();
  const t = COPY[language];
  const notify = useNotify();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [imageTag, setImageTag] = useState('');
  const [noCache, setNoCache] = useState(false);
  const [optimisticTask, setOptimisticTask] = useState<TaskInfo | null>(null);
  const [query, setQuery] = useState('');

  const { data, loading, error, reload, refresh } = useResource(
    async () => {
      const [fleet, workspaces, taskList] = await Promise.all([
        coderClient.getFleetStatus(),
        coderClient.listAllWorkspaces(),
        coderClient.listAdminTasks(10),
      ]);
      return { fleet, workspaces: workspaces.workspaces, tasks: taskList.tasks };
    },
    [],
    { refetchInterval: 3000 },
  );

  const templates = useMemo(() => data?.fleet.templates ?? [], [data]);
  const workspaces = useMemo(() => data?.workspaces ?? [], [data]);
  const tasks = useMemo(() => data?.tasks ?? [], [data]);
  const activeTask = tasks.find((item) => !TERMINAL.has(item.status)) ?? null;

  const optimisticVisible = optimisticTask && !tasks.some(
    (item) => item.task_id === optimisticTask.task_id,
  ) ? optimisticTask : null;
  const currentTask = activeTask ?? optimisticVisible ?? tasks[0] ?? null;
  const busy = Boolean(activeTask || optimisticVisible);
  const runningTask = activeTask ?? optimisticVisible;
  const selectedTemplates = templates.filter((template) => selected.has(template.name));
  const selectedReady = selectedTemplates.filter((template) => template.actionable_count > 0);

  const activeVersionByTemplate = useMemo(
    () => new Map(templates.map((template) => [template.id, template.active_version_id])),
    [templates],
  );

  function isOutdated(workspace: CoderWorkspace): boolean {
    const active = activeVersionByTemplate.get(workspace.template_id);
    return Boolean(active && workspace.template_version_id && workspace.template_version_id !== active);
  }

  const visibleWorkspaces = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return workspaces;
    return workspaces.filter((workspace) => searchHaystack(workspace).includes(needle));
  }, [workspaces, query]);

  function toggleTemplate(name: string) {
    setSelected((previous) => {
      const next = new Set(previous);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async function runBuildPush(names: string[]) {
    if (names.length === 0) return;
    try {
      const response = await coderClient.pushTemplates({
        templates: names,
        build_images: true,
        image_tag: imageTag.trim() || null,
        no_cache: noCache,
      });
      setOptimisticTask({
        task_id: response.workflow_id,
        workflow_id: response.workflow_id,
        task_name: response.task_name,
        status: TaskStatus.QUEUED,
        progress: { phase: 'queued', completed: 0, total: names.length },
      });
      notify(t.buildQueued(names.length), 'success');
      await refresh();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.buildFailed, 'error');
      await refresh();
    }
  }

  async function runRollout(names: string[]) {
    if (names.length === 0) return;
    try {
      const response = await coderClient.rolloutWorkspaces({ templates: names });
      setOptimisticTask({
        task_id: response.workflow_id,
        workflow_id: response.workflow_id,
        task_name: response.task_name,
        status: TaskStatus.QUEUED,
        progress: { phase: 'queued', completed: 0, total: names.length },
      });
      notify(t.rolloutQueued(names.length), 'success');
      await refresh();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.rolloutFailed, 'error');
      await refresh();
    }
  }

  return (
    <>
      <ErrorBanner>{error}</ErrorBanner>

      <div className="shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span
            className={`h-2 w-2 rounded-full ${
              data === null ? 'bg-faint' : data.fleet.healthy ? 'bg-success' : 'bg-danger'
            }`}
          />
          {data === null
            ? t.checkingCoder
            : data.fleet.healthy
              ? `${t.coderHealthy}${data.fleet.version ? ` · v${data.fleet.version}` : ''}`
              : t.coderUnreachable}
        </span>
        <span className="text-faint">·</span>
        <span>{loading ? '—' : t.workspacesCount(formatNumber(data?.fleet.workspace_count ?? 0, language))}</span>
      </div>

      <div className="shrink-0 bg-surface rounded-lg border border-rule p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-fg">{t.updatesHeading}</h2>
          <p className="text-sm text-muted mt-1">
            {t.updatesIntro1}
            <Link href="/workspaces/admin?tab=templates" className="text-accent-text hover:underline">
              {t.templatesTab}
            </Link>
            {t.updatesIntro2}
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="w-64">
            <label htmlFor="image-tag" className="block text-xs font-medium text-body mb-1">
              {t.imageTag}
            </label>
            <input
              id="image-tag"
              value={imageTag}
              onChange={(event) => setImageTag(event.target.value)}
              placeholder={t.imageTagPlaceholder}
              className={inputCls}
              disabled={busy}
            />
          </div>
          {/*
            A build already re-runs the extension checkout whenever that repo
            moves, so this is not the normal way to get a new extension — it is
            the fallback for cache staleness elsewhere in the image, and it
            rebuilds everything (slow, especially for MATLAB).
          */}
          <label className="flex items-center gap-2 pb-2 text-xs text-body">
            <input
              type="checkbox"
              checked={noCache}
              onChange={(event) => setNoCache(event.target.checked)}
              disabled={busy}
              className="h-4 w-4"
            />
            {t.rebuildAll}
          </label>
          <Button
            onClick={() => runBuildPush(selectedTemplates.map((template) => template.name))}
            disabled={busy || selectedTemplates.length === 0}
            title={selectedTemplates.length === 0 ? t.selectOne : undefined}
          >
            {t.buildPushSelected(selectedTemplates.length)}
          </Button>
          <Button
            variant="secondary"
            onClick={() => runRollout(selectedReady.map((template) => template.name))}
            disabled={busy || selectedReady.length === 0}
            title={selectedReady.length === 0 ? t.noOutdated : undefined}
          >
            {t.updateRunningNow(selectedReady.length)}
          </Button>
        </div>

        {currentTask && <TemplateTaskProgress task={currentTask} />}
      </div>

      {loading ? (
        <ListLoading>{t.loadingFleet}</ListLoading>
      ) : (
        <ScrollPanel className="h-[32rem]">
          <Table>
            <Thead>
              <tr>
                <Th className="w-10">
                  <input
                    type="checkbox"
                    aria-label={t.selectAll}
                    checked={templates.length > 0 && selectedTemplates.length === templates.length}
                    onChange={(event) =>
                      setSelected(event.target.checked ? new Set(templates.map((item) => item.name)) : new Set())
                    }
                  />
                </Th>
                <Th>{t.template}</Th>
                <Th>{t.activeVersion}</Th>
                <Th>{t.workspaces}</Th>
                <Th>{t.readiness}</Th>
                <Th className="text-right">{t.actions}</Th>
              </tr>
            </Thead>
            <Tbody>
              {templates.map((template) => {
                const operation = runningTask?.progress?.templates?.find(
                  (item) => item.name === template.name,
                );
                const state = operation
                  ? {
                      label: operation.status === 'failed'
                        ? t.failed
                        : runningTask?.task_name === 'rollout_workspaces'
                          ? t.rollingOut
                          : operation.status === 'succeeded'
                            ? t.versionReady
                            : operation.phase === 'pushing'
                              ? t.pushing
                              : t.building,
                      color: (operation.status === 'failed'
                        ? 'red'
                        : operation.status === 'succeeded'
                          ? 'green'
                          : 'blue') as BadgeColor,
                      detail: operation.error || phaseLabel(operation.phase, language),
                    }
                  : readiness(template, language);
                return (
                  <Tr key={template.id} className="hover:bg-canvas">
                    <Td>
                      <input
                        type="checkbox"
                        aria-label={t.select(template.display_name || template.name)}
                        checked={selected.has(template.name)}
                        onChange={() => toggleTemplate(template.name)}
                      />
                    </Td>
                    <Td>
                      <div className="text-sm font-medium text-fg">
                        {template.display_name || template.name}
                      </div>
                      <div className="text-xs text-muted">{template.name}</div>
                    </Td>
                    <Td className="text-sm text-muted font-mono">
                      {template.active_version_id ? template.active_version_id.slice(0, 12) : '—'}
                    </Td>
                    <Td>
                      <div className="text-sm text-body">{t.total(template.workspace_count)}</div>
                      <div className="text-xs text-muted">
                        {template.outdated_count > 0
                          ? t.onOlder(template.outdated_count)
                          : t.current(template.current_count)}
                      </div>
                    </Td>
                    <Td>
                      <Badge color={state.color}>{state.label}</Badge>
                      <div className="text-xs text-muted mt-1">{state.detail}</div>
                    </Td>
                    <Td>
                      <div className="flex justify-end gap-2">
                        <Button size="xs" variant="ghost" disabled={busy} onClick={() => runBuildPush([template.name])}>
                          {t.buildPush}
                        </Button>
                        <Button
                          size="xs"
                          variant="secondary"
                          disabled={busy || template.actionable_count === 0}
                          title={template.actionable_count === 0 ? state.detail : undefined}
                          onClick={() => runRollout([template.name])}
                        >
                          {t.updateRunning}
                        </Button>
                      </div>
                    </Td>
                  </Tr>
                );
              })}
              {templates.length === 0 && (
                <Tr>
                  <Td colSpan={6} className="py-8 text-center text-sm text-muted">{t.noTemplates}</Td>
                </Tr>
              )}
            </Tbody>
          </Table>
        </ScrollPanel>
      )}

      <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <span>
          {t.details}
          {query.trim() && <span>{t.ofTotal(visibleWorkspaces.length, workspaces.length)}</span>}
          {visibleWorkspaces.some(isOutdated) && (
            <span className="text-warn-text">{t.onOlderVersion(visibleWorkspaces.filter(isOutdated).length)}</span>
          )}
        </span>
        <div className="flex items-center gap-2">
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className={`${inputCls} w-72`}
            placeholder={t.filterPlaceholder}
            aria-label={t.filterLabel}
          />
          <Button size="xs" variant="ghost" onClick={() => reload()} disabled={loading}>{t.refresh}</Button>
        </div>
      </div>

      {!loading && (
        <ScrollPanel className="h-[32rem]">
          <Table>
            <Thead>
              <tr>
                <Th>{t.owner}</Th><Th>{t.workspace}</Th><Th>{t.template}</Th><Th>{t.version}</Th><Th>{t.status}</Th>
              </tr>
            </Thead>
            <Tbody>
              {visibleWorkspaces.map((workspace) => {
                const owner = ownerLines(workspace);
                return (
                <Tr key={workspace.id} className="hover:bg-canvas">
                  <Td title={workspace.owner_name ? t.coderUser(workspace.owner_name) : undefined}>
                    {workspace.owner_user_id ? (
                      <Link
                        href={`/workspaces/admin/${workspace.owner_user_id}`}
                        className="text-sm text-accent-text hover:underline"
                      >
                        {owner.primary}
                      </Link>
                    ) : (
                      <span className="text-sm text-fg">{owner.primary}</span>
                    )}
                    {owner.secondary && (
                      <div className="text-xs text-muted">{owner.secondary}</div>
                    )}
                  </Td>
                  <Td className="text-sm text-muted">{workspace.name}</Td>
                  <Td className="text-sm text-muted">
                    {workspace.template_display_name || workspace.template_name || '—'}
                  </Td>
                  <Td>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted">{workspace.template_version_name || '—'}</span>
                      {isOutdated(workspace) ? (
                        <Badge color="yellow">{t.outdated}</Badge>
                      ) : workspace.template_version_id ? (
                        <Badge color="green">{t.latest}</Badge>
                      ) : null}
                    </div>
                  </Td>
                  <Td>
                    <WorkspaceStatusBadge
                      status={workspace.latest_build_status}
                      transition={workspace.latest_build_transition}
                    />
                  </Td>
                </Tr>
                );
              })}
              {visibleWorkspaces.length === 0 && (
                <Tr>
                  <Td colSpan={5} className="py-8 text-center text-sm text-muted">
                    {workspaces.length === 0 ? t.noWorkspaces : t.noMatch}
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
