'use client';

import Badge, { type BadgeColor } from '@/src/components/Badge';
import type { WorkspaceBuildStatus } from '@/src/types/workspaces';

type StatusCategory = 'running' | 'stopped' | 'pending' | 'failed' | 'unknown';

/**
 * Which lifecycle bucket a workspace is in.
 *
 * `latest_build_status` describes the latest BUILD, and a build's meaning
 * depends on its `transition`: a stopped workspace's last build succeeded — at
 * stopping. Without the transition, 'succeeded' and 'running' have to be read
 * optimistically (that is all the caller gave us); with it, a finished stop or
 * delete lands in 'stopped' instead of claiming the workspace is up. The
 * backend gates its running-workspace quota on the same pair.
 */
function categorizeStatus(
  status?: WorkspaceBuildStatus | string | null,
  transition?: string | null,
): StatusCategory {
  if (!status) return 'unknown';
  const s = status.toLowerCase();
  if (s === 'failed') return 'failed';
  if (s === 'running' || s === 'succeeded') {
    if (transition === 'stop') return 'stopped';
    if (transition === 'delete') return 'unknown';
    return 'running';
  }
  if (s === 'stopped' || s === 'canceled') return 'stopped';
  if (s === 'starting' || s === 'stopping' || s === 'pending' || s === 'canceling' || s === 'deleting') return 'pending';
  return 'unknown';
}

const categoryColor: Record<StatusCategory, BadgeColor> = {
  running: 'green',
  stopped: 'gray',
  pending: 'yellow',
  failed: 'red',
  unknown: 'gray',
};

const categoryDots: Record<StatusCategory, string> = {
  running: 'bg-green-500',
  stopped: 'bg-gray-400',
  pending: 'bg-yellow-500 animate-pulse',
  failed: 'bg-red-500',
  unknown: 'bg-gray-400',
};

/**
 * What to call the state in the UI. The raw build status is provisioner
 * vocabulary ('succeeded' for a workspace that is merely stopped), so the badge
 * shows the lifecycle word a user recognises and keeps the raw value in the
 * tooltip for whoever is debugging.
 */
const CATEGORY_LABEL: Record<StatusCategory, string> = {
  running: 'running',
  stopped: 'stopped',
  pending: 'working',
  failed: 'failed',
  unknown: 'unknown',
};

function statusLabel(status?: string | null, transition?: string | null): string {
  const s = (status || '').toLowerCase();
  // In-flight statuses already read well; they are the transition itself.
  if (['starting', 'stopping', 'pending', 'canceling', 'deleting'].includes(s)) return s;
  return CATEGORY_LABEL[categorizeStatus(status, transition)];
}

/** Live workspace status as a shared Badge pill with a state dot. */
export default function WorkspaceStatusBadge({
  status,
  transition,
}: {
  status?: WorkspaceBuildStatus | string | null;
  /** The build's transition ('start' | 'stop' | 'delete') — pass it when known. */
  transition?: string | null;
}) {
  const category = categorizeStatus(status, transition);
  return (
    <Badge color={categoryColor[category]} pill className="capitalize" >
      <span className={`h-1.5 w-1.5 rounded-full mr-1.5 ${categoryDots[category]}`} />
      <span title={status ? `Build status: ${status}` : undefined}>
        {statusLabel(status, transition)}
      </span>
    </Badge>
  );
}

export { categorizeStatus };
export type { StatusCategory };
