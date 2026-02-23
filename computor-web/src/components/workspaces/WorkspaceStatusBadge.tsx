'use client';

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

const categoryStyles: Record<StatusCategory, string> = {
  running: 'bg-green-100 text-green-700',
  stopped: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-700',
  failed: 'bg-red-100 text-red-700',
  unknown: 'bg-gray-100 text-gray-500',
};

const categoryDots: Record<StatusCategory, string> = {
  running: 'bg-green-500',
  stopped: 'bg-gray-400',
  pending: 'bg-yellow-500 animate-pulse',
  failed: 'bg-red-500',
  unknown: 'bg-gray-400',
};

interface WorkspaceStatusBadgeProps {
  status?: WorkspaceBuildStatus | string | null;
  size?: 'sm' | 'md';
}

export default function WorkspaceStatusBadge({ status, size = 'md' }: WorkspaceStatusBadgeProps) {
  const category = categorizeStatus(status);
  const label = status || 'unknown';

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses} ${categoryStyles[category]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${categoryDots[category]}`} />
      {label}
    </span>
  );
}

export { categorizeStatus };
export type { StatusCategory };
