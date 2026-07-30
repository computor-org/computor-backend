import type { ProgressTone } from '@/src/components/ui/ProgressTrack';
import type { AgentLifecycle } from '@/src/types/workspaces';
import { AGENT_LIFECYCLE_GAVE_UP } from '@/src/types/workspaces';
import { categorizeStatus, type StatusCategory } from './WorkspaceStatusBadge';

/**
 * One workspace's position in its lifecycle, as something a bar can draw.
 *
 * Coder reports stages ("starting"), never percentages, so the numbers here are
 * the *stage boundaries* of a start: queued, provisioning, agent booting, in.
 * They are honest about ordering and never about time — a MATLAB image pulling
 * for two minutes sits at the same 45 as a cached one that passes through in
 * three seconds. That is why anything unfinished also sets `active`, which
 * makes the bar sweep: the width says how far, the motion says still going.
 */
export interface WorkspaceStage {
  /** 0–100, the stage boundary reached. */
  percent: number;
  /** Short human label for the stage, e.g. 'Starting'. */
  label: string;
  tone: ProgressTone;
  /** Work is still in flight — draw the bar as moving. */
  active: boolean;
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
    return { percent: 100, label: 'Failed', tone: 'red', active: false, settled: true };
  }

  if (category === 'pending') {
    const s = (status || '').toLowerCase();
    if (deleting || s === 'deleting') {
      return { percent: 60, label: 'Deleting', tone: 'gray', active: true, settled: false };
    }
    if (stopping || s === 'stopping') {
      return { percent: 60, label: 'Stopping', tone: 'gray', active: true, settled: false };
    }
    if (s === 'canceling') {
      return { percent: 60, label: 'Canceling', tone: 'gray', active: true, settled: false };
    }
    if (s === 'starting') {
      return { percent: 45, label: 'Starting', tone: 'blue', active: true, settled: false };
    }
    return { percent: 15, label: 'Queued', tone: 'blue', active: true, settled: false };
  }

  if (category === 'running') {
    // The build is up, which is not the same as the editor being reachable —
    // the agent still has a startup script to finish. Only the details endpoint
    // knows; from the list, `running` is as far as we can honestly claim.
    if (agentLifecycle === undefined || agentLifecycle === null) {
      return { percent: 100, label: 'Running', tone: 'green', active: false, settled: true };
    }
    if (agentLifecycle === 'ready') {
      return { percent: 100, label: 'Ready', tone: 'green', active: false, settled: true };
    }
    if (AGENT_LIFECYCLE_GAVE_UP.includes(agentLifecycle)) {
      // Running, but its startup script is never reporting ready. Not a build
      // failure — the workspace opens — so amber, and settled: waiting longer
      // changes nothing.
      return { percent: 100, label: 'Running (startup incomplete)', tone: 'amber', active: false, settled: true };
    }
    return { percent: 80, label: 'Preparing the editor', tone: 'blue', active: true, settled: false };
  }

  if (category === 'stopped') {
    return { percent: 0, label: 'Stopped', tone: 'gray', active: false, settled: true };
  }

  return { percent: 0, label: 'Unknown', tone: 'gray', active: false, settled: true };
}
