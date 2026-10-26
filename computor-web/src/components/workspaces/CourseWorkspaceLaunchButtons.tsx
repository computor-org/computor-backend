'use client';

import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type Ref } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { useCoderTemplates } from '@/src/hooks/useCoderTemplates';
import { useWorkspaceActions } from '@/src/hooks/useWorkspaceActions';
import { useNotify } from '@/src/contexts/NotificationContext';
import Button from '@/src/components/ui/Button';
import LearningOptions from '@/src/components/courses/LearningOptions';
import WorkspaceStatusBadge, {
  categorizeStatus,
} from '@/src/components/workspaces/WorkspaceStatusBadge';
import TemplateCard, { TemplateIconButton } from '@/src/components/workspaces/TemplateCard';
import TemplateIcon from '@/src/components/workspaces/TemplateIcon';
import { courseTemplateOption, isUsable, templateLabel } from '@/src/components/workspaces/templateOptions';
import { CoderClient } from '@/src/clients/CoderClient';
import { CourseWorkspacesClient } from '@/src/clients/CourseWorkspacesClient';
import {
  derivedWorkspaceName,
  reserveWorkspaceLaunch,
  focusRunningWorkspace,
  workspaceLaunchUrl,
} from '@/src/utils/workspaceLaunch';
import type { CoderWorkspace } from '@/src/types/workspaces';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    targetLoading: 'VS Code wird noch vorbereitet. Versuch es gleich noch einmal.',
    targetUnavailable: 'VS Code ist für diesen Kurs gerade nicht verfügbar.',
    ownerUnavailable: 'Der Besitzer der vorhandenen Arbeitsumgebung ist nicht verfügbar. Versuch es noch einmal.',
    notCreated: 'Die Arbeitsumgebung wurde nicht erstellt.',
    launchFailed: 'Die Arbeitsumgebung konnte nicht gestartet werden',
    selectionFailed: 'Deine Auswahl konnte in deiner Arbeitsumgebung nicht geöffnet werden. Versuch es noch einmal.',
    launching: 'Wird gestartet …',
    launch: 'Arbeitsumgebung starten',
    setUp: 'Arbeitsumgebung einrichten',
    openIn: (label: string) => `In ${label} öffnen`,
    startAndOpen: 'Starten und öffnen',
    startAgain: 'Erneut starten',
    stopHint: (label: string) => `Beendet ${label}. Deine Dateien bleiben erhalten.`,
    yours: 'Weitere Arbeitsumgebungen',
    open: 'Öffnen',
    retry: 'Erneut versuchen',
    start: 'Starten',
    stop: 'Stoppen',
    stopping: 'Wird gestoppt …',
  },
  en: {
    targetLoading: 'VS Code is still loading. Please try again shortly.',
    targetUnavailable: 'VS Code is not currently available for this course.',
    ownerUnavailable: 'The existing workspace owner is unavailable. Please retry.',
    notCreated: 'The workspace was not created.',
    launchFailed: 'Failed to launch workspace',
    selectionFailed: 'Your selection could not be opened in your workspace. Please retry.',
    launching: 'Launching…',
    launch: 'Launch workspace',
    setUp: 'Set up workspace',
    openIn: (label: string) => `Open in ${label}`,
    startAndOpen: 'Start and open',
    startAgain: 'Start again',
    stopHint: (label: string) => `Shuts down ${label}. Your files are kept.`,
    yours: 'Other workspaces',
    open: 'Open',
    retry: 'Retry',
    start: 'Start',
    stop: 'Stop',
    stopping: 'Stopping…',
  },
};

const coderClient = new CoderClient();
const courseWorkspacesClient = new CourseWorkspacesClient();

/**
 * Launch buttons for a course's allowed workspace templates.
 *
 * One control per (enabled) template — clicking reuses the caller's
 * per-template workspace, or provisions it when missing, and opens the launch
 * tab. Reusing keeps the running editor and its credentials intact.
 *
 * On the course page a template whose personal workspace already exists is a
 * single row with its state and one state-aware action ("In VS Code öffnen",
 * "Starten und öffnen", "Erneut starten"), plus Stop while it runs, with no
 * text beside them: what Stop does is its tooltip. The tile
 * that sets a workspace up appears only while there is none: a tile next to a
 * row for the same workspace made returning learners guess which one resumes
 * their work and whether the tile creates a second workspace. Other
 * workspaces on course templates, such as lecturer-provisioned throwaway
 * ones (students can open and start those, but not provision them), are
 * listed below.
 *
 * A course holds its templates by name, so it can go on offering one Coder
 * does not have — never deployed, or still building. Those render dimmed and
 * unclickable, with the reason in reach: the click used to travel to the
 * server and come back as "Template 'bash-workspace' is not yet available",
 * which reads as a broken button rather than a fact about the deployment.
 *
 * Self-hiding: renders nothing while loading, on error (non-members), or when
 * the course has no templates.
 */
export interface CourseWorkspaceLauncher {
  /** Open one selected assignment through this page's existing personal launcher. */
  launch: (courseContentId: string, options?: { sameTab?: boolean }) => void;
}

export default function CourseWorkspaceLaunchButtons({
  courseId,
  courseContentId,
  autoLaunch = false,
  ref,
  compact = false,
  className,
  title,
}: {
  courseId: string;
  courseContentId?: string;
  /** Legacy learner exercise links hand off once, in the current tab. */
  autoLaunch?: boolean;
  ref?: Ref<CourseWorkspaceLauncher>;
  compact?: boolean;
  /** Extra classes on the root, e.g. outer spacing — only rendered when the
      component itself renders, so callers don't get stray margins when it
      self-hides. */
  className?: string;
  /** Section heading rendered inside the root (non-compact only) — lives here
      rather than in the caller so it disappears with the component when the
      course has no templates, instead of leaving an empty titled card. */
  title?: string;
}) {
  const router = useRouter();
  const { user } = useAuth();
  const reservationRef = useRef<ReturnType<typeof reserveWorkspaceLaunch> | null>(null);
  useEffect(() => () => { reservationRef.current?.cancel(); }, [user?.id]);
  const notify = useNotify();
  const language = useUiLanguage();
  const t = COPY[language];
  const autoAttempt = useRef<string | null>(null);
  const [launchMessage, setLaunchMessage] = useState<string | null>(null);
  const [launching, setLaunching] = useState<string | null>(null);
  const [stopping, setStopping] = useState<string | null>(null);

  // Enabled course templates — one snapshot; what a course offers does not
  // change under an open page.
  const { data: courseTemplates } = useResource(
    async () => {
      const settings = await courseWorkspacesClient
        .getSettings({ courseId })
        .catch(() => null);
      return (settings?.templates ?? []).filter((t) => t.enabled);
    },
    [courseId],
  );
  const templates = useMemo(() => courseTemplates ?? [], [courseTemplates]);

  // Own workspaces on course templates (incl. lecturer-provisioned ones),
  // polled like the /workspaces table so the status chip follows a start or
  // stop on its own instead of freezing on the first snapshot. 403s only when
  // the caller has neither a workspace role nor course access — then the
  // section is icon-only.
  const { data: workspacesData, refresh } = useResource(
    async () => {
      const names = new Set(templates.map((t) => t.template_name));
      return coderClient
        .listWorkspaces()
        .then((r) => r.workspaces.filter((w) => w.template_name && names.has(w.template_name)))
        .catch(() => [] as CoderWorkspace[]);
    },
    [courseId, templates],
    { enabled: !compact && templates.length > 0, refetchInterval: 3000 },
  );

  // Deployment state — including the build a user may be waiting on — comes
  // from the templates listing, but only where one of these is on the page.
  // The compact variant sits on every card of the courses list, where a second
  // request per course would be the page's dominant cost; there the course
  // settings' own exists_in_coder carries the "not available" case, and an
  // icon row has no room for a stage bar anyway.
  const {
    options,
    answered: templatesAnswered,
    error: templatesError,
  } = useCoderTemplates({
    enabled: !compact,
    refetchInterval: compact ? undefined : 10000,
  });

  const workspaces = workspacesData ?? [];
  // The personal workspace per template, the one provisionAndLaunch reuses.
  // Unknown until the first listing answers, which keeps the neutral tile.
  const personal = new Map(
    workspaces
      .filter((w) => w.template_name && w.name === derivedWorkspaceName(w.template_name))
      .map((w) => [w.template_name as string, w]),
  );
  const others = workspaces.filter((w) => personal.get(w.template_name ?? '') !== w);
  const [launchError, setLaunchError] = useState(false);

  // Same stop as the /workspaces table (notification + delayed refresh) — the
  // backend allows course-derived callers to stop their own workspaces, and
  // this widget is the only workspace surface many of them ever see.
  const actions = useWorkspaceActions(refresh);

  const courseOptions = useMemo(() => {
    const byName = new Map(options.map((option) => [option.name, option]));
    // A listing that never ran, or failed, tells us nothing — then the course
    // settings' exists_in_coder is what is left to go on.
    const answered = !compact && templatesAnswered && !templatesError;
    return templates.map((t) => courseTemplateOption(t, byName.get(t.template_name), answered));
  }, [templates, options, templatesAnswered, templatesError, compact]);

  // window.open must happen synchronously inside the click — after an await it
  // is no longer tied to the user gesture and popup blockers eat it.
  const provisionAndLaunch = useCallback(async (templateName: string, targetId = courseContentId, sameTab = false) => {
    if (!user?.id) return;
    setLaunchError(false);
    setLaunchMessage(null);
    setLaunching(templateName);
    const reservation = reserveWorkspaceLaunch(user.id, templateName, undefined, undefined, sameTab);
    reservationRef.current = reservation;
    try {
      const workspace = await reservation.resolveWorkspace(async () => {
        const { workspaces: ownWorkspaces } = await coderClient.listWorkspaces();
        const existing = ownWorkspaces.find((candidate) =>
          candidate.template_name === templateName && candidate.name === derivedWorkspaceName(templateName));
        if (existing) {
          if (!existing.owner_name) throw new Error(t.ownerUnavailable);
          return existing;
        }
        // A newer same-key waiter may still need this shared resolution,
        // but a fully cancelled launch must not create a workspace.
        if (!reservation.wanted()) throw new Error(t.notCreated);
        const result = await coderClient.provisionWorkspace({ body: { template: templateName } });
        if (!result.workspace?.name) throw new Error(t.notCreated);
        return { ...result.workspace, owner_name: result.user.username, template_name: templateName };
      });
      if (!reservation.current()) return;
      const outcome = await focusRunningWorkspace(reservation, workspace, courseId, targetId, language);
      if (outcome === 'handled') return;
      if (!reservation.current()) return;
      const launchUrl = workspaceLaunchUrl(workspace.owner_name!, workspace.name, courseId, targetId);
      const tab = outcome === 'lifecycle' ? reservation.tab : null;
      if (tab) {
        tab.location.replace(launchUrl);
      } else {
        if (!reservation.tab) window.name = reservation.key;
        router.push(launchUrl);
      }
    } catch (err) {
      reservation.closeFresh();
      if (!reservation.current()) return;
      setLaunchError(true);
      const message = targetId || (reservation.tab && !reservation.fresh) ? t.selectionFailed : err instanceof Error ? err.message : t.launchFailed;
      setLaunchMessage(sameTab && message !== t.ownerUnavailable && message !== t.notCreated ? t.launchFailed : message);
      if (!sameTab) notify(message, 'error');
    } finally {
      if (reservation.active() && reservationRef.current === reservation) setLaunching(null);
    }
  }, [courseId, courseContentId, language, notify, router, t, user?.id]);

  async function openExisting(workspace: CoderWorkspace) {
    if (!workspace.owner_name || !user?.id) return;
    const reservation = reserveWorkspaceLaunch(user.id, workspace.template_name ?? workspace.name, workspace.name, workspace.owner_name);
    reservationRef.current = reservation;
    try {
      const outcome = await focusRunningWorkspace(reservation, workspace, courseId, courseContentId, language);
      if (outcome === 'handled') return;
      if (!reservation.current()) return;
      const url = workspaceLaunchUrl(workspace.owner_name, workspace.name, courseId, courseContentId);
      if (outcome === 'lifecycle' && reservation.tab) reservation.tab.location.replace(url);
      else { if (!reservation.tab) window.name = reservation.key; router.push(url); }
    } catch {
      reservation.closeFresh();
      if (reservation.current()) notify(courseContentId ? t.selectionFailed : t.launchFailed, 'error');
    }
  }

  async function stopExisting(workspace: CoderWorkspace) {
    if (!workspace.owner_name) return;
    setStopping(workspace.id);
    try {
      await actions.stop(workspace.owner_name, workspace.name);
    } finally {
      setStopping(null);
    }
  }

  // One mounted course launcher serves every exercise action on the page.
  // No row needs its own template/workspace fetches or provisioning logic.
  useImperativeHandle(ref, () => ({
    launch(targetId, launchOptions) {
      if (launching || courseTemplates === null || (!compact && !templatesAnswered && !templatesError)) {
        notify(t.targetLoading, 'info');
        return;
      }
      const vscode = courseOptions.find((option) => option.name === 'vscode-workspace' && isUsable(option));
      if (!vscode) {
        notify(t.targetUnavailable, 'error');
        return;
      }
      void provisionAndLaunch(vscode.name, targetId, launchOptions?.sameTab);
    },
  }));

  useEffect(() => {
    if (!autoLaunch || !courseContentId || courseTemplates === null || (!templatesAnswered && !templatesError)) return;
    const key = `${courseId}:${courseContentId}`;
    if (autoAttempt.current === key) return;
    const vscode = courseOptions.find((option) => option.name === 'vscode-workspace' && isUsable(option));
    if (!vscode) return;
    autoAttempt.current = key;
    // Start the external launch after this readiness effect has committed.
    void Promise.resolve().then(() => provisionAndLaunch(vscode.name, courseContentId, true));
  }, [autoLaunch, courseId, courseContentId, courseTemplates, templatesAnswered, templatesError, courseOptions, provisionAndLaunch, t]);

  if (autoLaunch) {
    const ready = courseTemplates !== null && (templatesAnswered || !!templatesError);
    const unavailable = ready && !courseOptions.some((option) => option.name === 'vscode-workspace' && isUsable(option));
    const message = launchMessage ?? (unavailable ? t.targetUnavailable : null);
    return <p role={message ? 'alert' : 'status'}>{message ?? t.launching}</p>;
  }

  if (templates.length === 0) return null;

  const ownOptions = courseOptions.filter((option) => personal.has(option.name));
  const newOptions = courseOptions.filter((option) => !personal.has(option.name));

  if (compact) {
    return (
      <div className={`mt-2 flex flex-wrap items-center gap-1.5 ${className ?? ''}`}>
        {launchError && <LearningOptions capacity language={language} />}
        {courseOptions.map((option) => (
          <TemplateIconButton
            key={option.name}
            option={option}
            busy={launching === option.name}
            dimmed={launching !== null && launching !== option.name}
            onClick={() => provisionAndLaunch(option.name)}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className ?? ''}`}>
      {launchError && <LearningOptions capacity language={language} />}
      {title && <h2 className="text-lg font-semibold text-fg">{title}</h2>}
      {ownOptions.length > 0 && (
        <ul className="space-y-3">
          {ownOptions.map((option) => {
            const w = personal.get(option.name)!;
            const category = categorizeStatus(w.latest_build_status, w.latest_build_transition);
            const label = templateLabel(option);
            // A workspace that is stopping is started again once it has
            // stopped, which is what the launch page does.
            const primary =
              category === 'failed'
                ? t.startAgain
                : category === 'stopped' || w.latest_build_transition === 'stop'
                  ? t.startAndOpen
                  : t.openIn(label);
            return (
              <li
                key={option.name}
                className="flex flex-wrap items-center gap-x-3 gap-y-3 rounded-lg border border-rule bg-surface p-3 pr-4"
              >
                {/* On a phone the icon would take a line of its own; the name says it. */}
                <span className="hidden sm:block">
                  <TemplateIcon template={{ icon: option.icon, name: option.name }} />
                </span>
                {/* basis-48: on a phone the actions wrap below instead of squeezing the text. */}
                <div className="min-w-0 flex-1 basis-48">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-fg">{label}</span>
                    <WorkspaceStatusBadge
                      status={w.latest_build_status}
                      transition={w.latest_build_transition}
                    />
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
                  {/* Same click as the tile: a fresh lookup, then reuse. */}
                  <Button
                    size="sm"
                    onClick={() => provisionAndLaunch(option.name)}
                    loading={launching === option.name}
                    loadingLabel={t.launching}
                  >
                    {primary}
                  </Button>
                  {category === 'running' && (
                    <Button
                      size="sm"
                      variant="secondary"
                      title={t.stopHint(label)}
                      onClick={() => stopExisting(w)}
                      loading={stopping === w.id}
                      loadingLabel={t.stopping}
                    >
                      {t.stop}
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {newOptions.length > 0 && (
        <div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {newOptions.map((option) => (
              <TemplateCard
                key={option.name}
                option={option}
                actionLabel={
                  launching === option.name ? t.launching : workspacesData ? t.setUp : t.launch
                }
                busy={launching === option.name}
                onClick={() => provisionAndLaunch(option.name)}
              />
            ))}
          </div>
        </div>
      )}

      {others.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-body mb-2">{t.yours}</h3>
          <ul className="space-y-1.5">
            {others.map((w) => {
              const category = categorizeStatus(w.latest_build_status, w.latest_build_transition);
              return (
                <li
                  key={w.id}
                  className="flex items-center justify-between gap-2 rounded-lg border border-rule px-3 py-2"
                >
                  <div className="min-w-0">
                    <span className="block truncate text-sm font-medium text-fg">{w.name}</span>
                    <span className="block text-xs text-muted">
                      {w.template_display_name || w.template_name}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {/*
                      The chip alone, as in the workspaces table: starting or
                      stopping is a wait of seconds with no stages to report,
                      and the chip already names it.
                    */}
                    <WorkspaceStatusBadge
                      status={w.latest_build_status}
                      transition={w.latest_build_transition}
                    />
                    <Button size="xs" onClick={() => openExisting(w)}>
                      {category === 'running' ? t.open : category === 'failed' ? t.retry : t.start}
                    </Button>
                    {category === 'running' && (
                      <Button
                        size="xs"
                        variant="secondary"
                        onClick={() => stopExisting(w)}
                        loading={stopping === w.id}
                        loadingLabel={t.stopping}
                      >
                        {t.stop}
                      </Button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
