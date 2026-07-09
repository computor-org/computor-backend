'use client';

import Badge, { type BadgeColor } from '@/src/components/Badge';
import type { WorkspaceBuildStatus } from '@/src/types/workspaces';

type StatusCategory = 'running' | 'stopped' | 'pending' | 'failed' | 'unknown';

function categorizeStatus(status?: WorkspaceBuildStatus | string | null): StatusCategory {
  if (!status) return 'unknown';
  const s = status.toLowerCase();
  if (s === 'running' || s === 'succeeded') return 'running';
  if (s === 'stopped' || s === 'canceled') return 'stopped';
  if (s === 'starting' || s === 'stopping' || s === 'pending' || s === 'canceling' || s === 'deleting') return 'pending';
  if (s === 'failed') return 'failed';
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

/** Live workspace status as a shared Badge pill with a state dot. */
export default function WorkspaceStatusBadge({
  status,
}: {
  status?: WorkspaceBuildStatus | string | null;
}) {
  const category = categorizeStatus(status);
  return (
    <Badge color={categoryColor[category]} pill>
      <span className={`h-1.5 w-1.5 rounded-full mr-1.5 ${categoryDots[category]}`} />
      {status || 'unknown'}
    </Badge>
  );
}

export { categorizeStatus };
export type { StatusCategory };
