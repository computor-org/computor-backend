'use client';

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Spinner from '@/src/components/ui/Spinner';
import Button from '@/src/components/ui/Button';
import { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import { CoderClient } from '@/src/clients/CoderClient';
import { AGENT_LIFECYCLE_GAVE_UP, type WorkspaceDetails } from '@/src/types/workspaces';

const coderClient = new CoderClient();

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
  // Creation parks the tab here before the workspace's name is known — the
  // opener replaces the URL (or closes the tab) once provisioning returns.
  const creating = Boolean(useSearchParam('creating'));
  const hasTarget = Boolean(owner && name);

  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  /** The states worth giving up on; everything else is derived at render. */
  const [terminalError, setTerminalError] = useState<string | null>(null);

  // One-shot guards. Refs, not state: StrictMode double-invokes effects in dev,
  // and re-renders must not fire a second build or a second redirect.
  const startRequested = useRef(false);
  const redirected = useRef(false);
  const graceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  /**
   * Whether the workspace has reported anything other than `failed` since we
   * asked it to start. Until it has, a `failed` status is still describing the
   * build that was already there when we arrived — not ours.
   */
  const leftFailedBehind = useRef(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
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
          setTerminalError('The workspace failed to start.');
        }
      } else {
        leftFailedBehind.current = true;
      }
      return polled;
    },
    [owner, name],
    { enabled: hasTarget, refetchInterval: POLL_MS },
  );

  /** Pure side effect — no state, so it is safe to call straight from an effect. */
  const openWorkspace = useCallback((url: string) => {
    if (redirected.current) return;
    redirected.current = true;
    // replace(), not href: Back should return to the app, not to this waiter.
    window.location.replace(url);
  }, []);

  // Ceiling on the whole wait. A timer rather than a wall-clock check on each
  // poll, because polling pauses while the tab is hidden — and a workspace that
  // becomes ready must still open, however long the tab sat in the background.
  useEffect(() => {
    if (!hasTarget) return;
    const id = setTimeout(() => {
      if (!redirected.current) {
        setTerminalError('This workspace is taking longer than expected to start.');
      }
    }, OVERALL_TIMEOUT_MS);
    return () => clearTimeout(id);
  }, [hasTarget]);

  useEffect(() => {
    if (hasTarget || !creating) return;
    const id = setTimeout(() => setTerminalError('The workspace was not created.'), CREATING_TIMEOUT_MS);
    return () => clearTimeout(id);
  }, [hasTarget, creating]);

  useEffect(() => () => {
    if (graceTimer.current) clearTimeout(graceTimer.current);
  }, []);

  useEffect(() => {
    if (!hasTarget || redirected.current || error || !details) return;

    const category = categorizeStatus(details.status);
    const url = workspaceUrl(details);

    if (category === 'running' && url) {
      const gaveUp =
        !!details.agent_lifecycle && AGENT_LIFECYCLE_GAVE_UP.includes(details.agent_lifecycle);

      // `ready` is the real signal; `gaveUp` means it is never coming.
      if (details.ready || gaveUp) {
        openWorkspace(url);
        return;
      }

      // Running but not ready: give the service a bounded chance to come up,
      // then open anyway and let the workspace URL be the retry surface. This
      // is what carries workspaces still on a pre-port-gate template version.
      if (graceTimer.current === null) {
        graceTimer.current = setTimeout(() => openWorkspace(url), READY_GRACE_MS);
      }
      return;
    }

    // A stopped workspace is why we are here; a failed one is what the Start
    // button offers to retry. Either way: start it, exactly once.
    if ((category === 'stopped' || category === 'failed') && !startRequested.current) {
      startRequested.current = true;
      coderClient
        .startWorkspace({ username: owner, workspaceName: name })
        .catch((err) =>
          setTerminalError(err instanceof Error ? err.message : 'Failed to start the workspace.'),
        );
    }
  }, [details, error, hasTarget, owner, name, openWorkspace]);

  const errorMessage = hasTarget
    ? (terminalError ?? error)
    : creating
      ? terminalError
      : 'This link is missing the workspace to open.';

  // A poll error clears itself on the next successful tick, so the card is not sticky.
  const waitingMessage = !hasTarget
    ? 'Creating your workspace…'
    : details && categorizeStatus(details.status) === 'running'
      ? 'Almost there — waiting for the editor…'
      : 'Starting your workspace…';

  useEffect(() => {
    document.title = errorMessage
      ? 'Could not open the workspace'
      : name
        ? `Starting ${name}…`
        : 'Starting workspace…';
  }, [errorMessage, name]);

  return errorMessage ? (
    <div className="max-w-md w-full text-center space-y-4">
      <h1 className="text-xl font-semibold text-gray-900">Could not open the workspace</h1>
      <p className="text-gray-600">{errorMessage}</p>
      <div className="flex items-center justify-center gap-3 pt-2">
        {hasTarget && <Button onClick={() => window.location.reload()}>Retry</Button>}
        <Link href="/workspaces" className="text-sm text-blue-600 hover:underline">
          Back to workspaces
        </Link>
      </div>
    </div>
  ) : (
    <div className="text-center space-y-4">
      <Spinner label="Starting workspace" />
      <p className="text-gray-600">{waitingMessage}</p>
      {name && <p className="text-sm text-gray-400">{name}</p>}
      <p className="text-xs text-gray-400 pt-2">This tab opens automatically when it is ready.</p>
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
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <Suspense>
        <LaunchWorkspace />
      </Suspense>
    </div>
  );
}
