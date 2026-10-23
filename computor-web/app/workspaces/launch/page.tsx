'use client';

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Button from '@/src/components/ui/Button';
import Spinner from '@/src/components/ui/Spinner';
import LearningOptions from '@/src/components/courses/LearningOptions';
import { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import { workspaceStage } from '@/src/components/workspaces/workspaceStage';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import { CoderClient } from '@/src/clients/CoderClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { loginPathFor } from '@/src/utils/safeRedirect';
import { AGENT_LIFECYCLE_GAVE_UP, type WorkspaceDetails, type WorkspaceLaunchContext } from '@/src/types/workspaces';

const coderClient = new CoderClient();

const COPY = {
  de: {
    courseNotSelected: 'Der Kurs konnte in deiner Arbeitsumgebung nicht ausgewählt werden. Versuch es noch einmal.',
    courseNotSelectedShort: 'Der Kurs konnte in deiner Arbeitsumgebung nicht ausgewählt werden.',
    startFailed: 'Die Arbeitsumgebung konnte nicht gestartet werden.',
    startRequestFailed: 'Die Arbeitsumgebung konnte nicht gestartet werden.',
    tooSlow: 'Das Starten dieser Arbeitsumgebung dauert länger als erwartet.',
    notCreated: 'Die Arbeitsumgebung wurde nicht erstellt.',
    missingTarget: 'Diesem Link fehlt die Arbeitsumgebung, die geöffnet werden soll.',
    starting: 'Wird gestartet',
    creatingYours: 'Deine Arbeitsumgebung wird erstellt',
    couldNotOpen: 'Die Arbeitsumgebung konnte nicht geöffnet werden',
    startingTitle: (name: string) => `${name} wird gestartet …`,
    startingWorkspaceTitle: 'Arbeitsumgebung wird gestartet …',
    startingYours: 'Deine Arbeitsumgebung wird gestartet',
    retry: 'Erneut versuchen',
    back: 'Zurück zu den Arbeitsumgebungen',
    opensAutomatically: 'Dieser Tab öffnet sich automatisch, sobald die Arbeitsumgebung bereit ist.',
  },
  en: {
    courseNotSelected: 'The course could not be selected in your workspace. Please retry.',
    courseNotSelectedShort: 'The course could not be selected in your workspace.',
    startFailed: 'The workspace failed to start.',
    startRequestFailed: 'Failed to start the workspace.',
    tooSlow: 'This workspace is taking longer than expected to start.',
    notCreated: 'The workspace was not created.',
    missingTarget: 'This link is missing the workspace to open.',
    starting: 'Starting',
    creatingYours: 'Creating your workspace',
    couldNotOpen: 'Could not open the workspace',
    startingTitle: (name: string) => `Starting ${name}…`,
    startingWorkspaceTitle: 'Starting workspace…',
    startingYours: 'Starting your workspace',
    retry: 'Retry',
    back: 'Back to workspaces',
    opensAutomatically: 'This tab opens automatically when it is ready.',
  },
};

const POLL_MS = 2000;
/**
 * Once the build is up, how long to keep waiting for the agent to report `ready`
 * before opening anyway. Workspaces still on a template version from before the
 * startup scripts gained their "wait for the port" gate report ready almost
 * immediately — for them this grace period is all the settling time there is,
 * so it must not be zero.
 */
const READY_GRACE_MS = 45_000;
/** Absolute ceiling on the whole wait, so a stuck build can never spin forever. */
const OVERALL_TIMEOUT_MS = 5 * 60_000;
/**
 * How long the `creating` state waits for the opener to swap in the real
 * workspace URL. Normally that takes seconds (or the opener closes this tab on
 * failure); the timeout only catches an opener that died mid-provision or
 * someone navigating here directly.
 */
const CREATING_TIMEOUT_MS = 30_000;

function workspaceUrl(details: WorkspaceDetails): string | null {
  return details.code_server_url || details.access_url || null;
}

function LaunchWorkspace() {
  const owner = useSearchParam('owner');
  const name = useSearchParam('name');
  const courseId = useSearchParam('courseId');
  // Creation parks the tab here before the workspace's name is known — the
  // opener replaces the URL (or closes the tab) once provisioning returns.
  const creating = Boolean(useSearchParam('creating'));
  const hasTarget = Boolean(owner && name);

  const language = useUiLanguage();
  const t = COPY[language];
  // Callbacks below read the copy through a ref, so a language change neither
  // restarts timers nor refetches the poll.
  const tRef = useRef(t);
  useEffect(() => {
    tRef.current = t;
  }, [t]);

  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  /** The states worth giving up on; everything else is derived at render. */
  const [terminalError, setTerminalError] = useState<string | null>(null);

  // One-shot guards. Refs, not state: StrictMode double-invokes effects in dev,
  // and re-renders must not fire a second build or a second redirect.
  const startRequested = useRef(false);
  const opening = useRef(false);
  const redirected = useRef(false);
  const launchFailed = useRef(false);
  const mounted = useRef(false);
  const contextRequest = useRef<Promise<WorkspaceLaunchContext> | null>(null);
  const graceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  /**
   * Whether the workspace has reported anything other than `failed` since we
   * asked it to start. Until it has, a `failed` status is still describing the
   * build that was already there when we arrived — not ours.
   */
  const leftFailedBehind = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const failLaunch = useCallback((message: string) => {
    launchFailed.current = true;
    if (graceTimer.current) clearTimeout(graceTimer.current);
    if (mounted.current) setTerminalError(message);
  }, []);

  // Start and redirect share one request. In particular, a ready poll or the
  // grace timer must not race past a context handoff still in flight. Keeping
  // the promise also prevents StrictMode/repeated polls creating new requests.
  const handOffCourse = useCallback(async () => {
    if (!courseId) return;
    contextRequest.current ??= coderClient.setWorkspaceLaunchContext({
      username: owner, workspaceName: name, courseId,
    });
    const context = await contextRequest.current;
    if (context.course_id !== courseId) {
      throw new Error(tRef.current.courseNotSelected);
    }
  }, [owner, name, courseId]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push(loginPathFor(window.location));
    }
  }, [isAuthenticated, authLoading, router]);

  const { data: details, error } = useResource<WorkspaceDetails>(
    async () => {
      const polled = await coderClient.getWorkspaceDetails({ username: owner, workspaceName: name });
      // Judge each poll here, in the fetcher, rather than from a separate timer:
      // this runs exactly once per poll and in order, so the `failed` that lags
      // our start request can be told apart from a build that actually failed.
      if (categorizeStatus(polled.status) === 'failed') {
        if (startRequested.current && leftFailedBehind.current) {
          failLaunch(tRef.current.startFailed);
        }
      } else {
        leftFailedBehind.current = true;
      }
      return polled;
    },
    [owner, name, failLaunch],
    { enabled: hasTarget, refetchInterval: POLL_MS },
  );

  const openWorkspace = useCallback(async (url: string) => {
    if (opening.current || redirected.current || launchFailed.current) return;
    opening.current = true;
    try {
      await handOffCourse();
      if (!mounted.current || launchFailed.current) return;
      redirected.current = true;
      // replace(), not href: Back should return to the app, not to this waiter.
      window.location.replace(url);
    } catch (err) {
      failLaunch(err instanceof Error ? err.message : tRef.current.courseNotSelectedShort);
    }
  }, [handOffCourse, failLaunch]);

  // Ceiling on the whole wait. A timer rather than a wall-clock check on each
  // poll, because polling pauses while the tab is hidden — and a workspace that
  // becomes ready must still open, however long the tab sat in the background.
  useEffect(() => {
    if (!hasTarget) return;
    const id = setTimeout(() => {
      if (!redirected.current) {
        failLaunch(tRef.current.tooSlow);
      }
    }, OVERALL_TIMEOUT_MS);
    return () => clearTimeout(id);
  }, [hasTarget, failLaunch]);

  useEffect(() => {
    if (hasTarget || !creating) return;
    const id = setTimeout(() => failLaunch(tRef.current.notCreated), CREATING_TIMEOUT_MS);
    return () => clearTimeout(id);
  }, [hasTarget, creating, failLaunch]);

  useEffect(() => () => {
    if (graceTimer.current) clearTimeout(graceTimer.current);
    graceTimer.current = null;
  }, []);

  useEffect(() => {
    if (!hasTarget || redirected.current || launchFailed.current || error || !details) return;

    const category = categorizeStatus(details.status);
    const url = workspaceUrl(details);

    if (category === 'running' && url) {
      const gaveUp =
        !!details.agent_lifecycle && AGENT_LIFECYCLE_GAVE_UP.includes(details.agent_lifecycle);

      // `ready` is the real signal; `gaveUp` means it is never coming.
      if (details.ready || gaveUp) {
        void openWorkspace(url);
        return;
      }

      // Running but not ready: give the service a bounded chance to come up,
      // then open anyway and let the workspace URL be the retry surface. This
      // is what carries workspaces still on a pre-port-gate template version.
      if (graceTimer.current === null) {
        graceTimer.current = setTimeout(() => { void openWorkspace(url); }, READY_GRACE_MS);
      }
      return;
    }

    if (graceTimer.current) {
      clearTimeout(graceTimer.current);
      graceTimer.current = null;
    }

    // A stopped workspace is why we are here; a failed one is what the Start
    // button offers to retry. Either way: start it, exactly once.
    if ((category === 'stopped' || category === 'failed') && !startRequested.current) {
      startRequested.current = true;
      handOffCourse()
        .then(() => {
          if (!mounted.current || launchFailed.current) return;
          return coderClient.startWorkspace({ username: owner, workspaceName: name });
        })
        .catch((err) =>
          failLaunch(err instanceof Error ? err.message : tRef.current.startRequestFailed),
        );
    }
  }, [details, error, hasTarget, owner, name, openWorkspace, handOffCourse, failLaunch]);

  const errorMessage = hasTarget
    ? (terminalError ?? error)
    : creating
      ? terminalError
      : t.missingTarget;

  // The stage in words — 'Starting', 'Preparing the editor'. Before the first
  // poll lands (and while `creating` has no workspace to poll at all) there is
  // no status to map, so say what we know is happening.
  const stage = details
    ? workspaceStage(details.status, undefined, details.agent_lifecycle, language)
    : { label: hasTarget ? t.starting : t.creatingYours };

  useEffect(() => {
    document.title = errorMessage
      ? t.couldNotOpen
      : name
        ? t.startingTitle(name)
        : t.startingWorkspaceTitle;
  }, [errorMessage, name, t]);

  return errorMessage ? (
    <div className="max-w-md w-full text-center space-y-4">
      <h1 className="text-xl font-semibold text-fg">{t.couldNotOpen}</h1>
      <p className="text-muted">{errorMessage}</p>
      <LearningOptions capacity language={language} />
      <div className="flex items-center justify-center gap-3 pt-2">
        {hasTarget && <Button onClick={() => window.location.reload()}>{t.retry}</Button>}
        <Link href="/workspaces" className="text-sm text-accent-text hover:underline">
          {t.back}
        </Link>
      </div>
    </div>
  ) : (
    <div className="w-full max-w-sm space-y-5" aria-live="polite">
      <div className="space-y-1 text-center">
        <h1 className="text-lg font-semibold text-fg">
          {hasTarget ? t.startingYours : t.creatingYours}
        </h1>
        {name && <p className="text-sm text-muted">{name}</p>}
      </div>

      {/*
        A spinner and the stage in words. A bar here promised a measured wait
        it could not deliver: the numbers were stage boundaries, and a cached
        image passes all of them in three seconds while a cold MATLAB pull sits
        on one for two minutes.
      */}
      <div className="flex flex-col items-center gap-3">
        <Spinner size="md" label={`${stage.label}${name ? ` ${name}` : ''}`} />
        <p className="text-sm text-muted text-center">{stage.label}…</p>
      </div>

      <p className="text-xs text-subtle text-center">
        {t.opensAutomatically}
      </p>
    </div>
  );
}

// Deliberately a standalone page (no AuthenticatedLayout): this is a transient
// launch tab whose whole job is to show a spinner and hand over to the
// workspace — sidebar and top bar would only be noise here. Auth is still
// guarded (redirect to /login above); the consent gate is covered by the 403
// interceptor on the polling calls.
export default function LaunchWorkspacePage() {
  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
      <Suspense>
        <LaunchWorkspace />
      </Suspense>
    </div>
  );
}
