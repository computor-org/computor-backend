import type { AgentLifecycle } from '@/src/types/workspaces';
import { AGENT_LIFECYCLE_GAVE_UP } from '@/src/types/workspaces';
import { categorizeStatus, type StatusCategory } from './WorkspaceStatusBadge';

/**
 * What one workspace is doing, in a word.
 *
 * Deliberately not something a bar can draw. A workspace start or stop is a
 * wait of seconds whose only honest content is which step it is on, and the
 * status chip already carries that — a bar beside it drew a second, vaguer
 * copy of the same word while sitting at a percentage nobody measured.
 * (Template deployments are the opposite case and do get bars: tens of
 * minutes, several templates, stages worth comparing — see templateTaskStage.)
 */
export interface WorkspaceStage {
  /** Short human label for the stage, e.g. 'Starting'. */
  label: string;
  /** Nothing is happening: a settled workspace (running, stopped) or a failure. */
  settled: boolean;
}

/**
 * `latest_build_status` is the status of the latest BUILD, so it only means
 * what the build's `transition` says it means: 'succeeded'/'running' with
 * transition 'stop' is a stopped workspace, not a running one. Callers that
 * have the transition should pass it — the backend gates its own
 * running-workspace quota the same way (business_logic/course_workspaces.py).
 */
export function workspaceStage(
  status?: string | null,
  transition?: string | null,
  /** From the details endpoint; the list endpoint has no agent information. */
  agentLifecycle?: AgentLifecycle | string | null,
): WorkspaceStage {
  const category: StatusCategory = categorizeStatus(status, transition);
  const stopping = transition === 'stop';
  const deleting = transition === 'delete';

  if (category === 'failed') {
    return { label: 'Failed', settled: true };
  }

  if (category === 'pending') {
    const s = (status || '').toLowerCase();
    if (deleting || s === 'deleting') return { label: 'Deleting', settled: false };
    if (stopping || s === 'stopping') return { label: 'Stopping', settled: false };
    if (s === 'canceling') return { label: 'Canceling', settled: false };
    if (s === 'starting') return { label: 'Starting', settled: false };
    return { label: 'Queued', settled: false };
  }

  if (category === 'running') {
    // The build is up, which is not the same as the editor being reachable —
    // the agent still has a startup script to finish. Only the details endpoint
    // knows; from the list, `running` is as far as we can honestly claim.
    if (agentLifecycle === undefined || agentLifecycle === null) {
      return { label: 'Running', settled: true };
    }
    if (agentLifecycle === 'ready') {
      return { label: 'Ready', settled: true };
    }
    if (AGENT_LIFECYCLE_GAVE_UP.includes(agentLifecycle)) {
      // Running, but its startup script is never reporting ready. Not a build
      // failure — the workspace opens — so settled: waiting longer changes
      // nothing.
      return { label: 'Running (startup incomplete)', settled: true };
    }
    return { label: 'Preparing the editor', settled: false };
  }

  if (category === 'stopped') {
    return { label: 'Stopped', settled: true };
  }

  return { label: 'Unknown', settled: true };
}
