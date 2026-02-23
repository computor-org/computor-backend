'use client';

import { useState } from 'react';
import type { CoderWorkspace, WorkspaceDetails } from '@/src/types/workspaces';
import WorkspaceStatusBadge, { categorizeStatus } from './WorkspaceStatusBadge';

interface WorkspaceCardProps {
  workspace: CoderWorkspace;
  onStart: (owner: string, name: string) => Promise<void>;
  onStop: (owner: string, name: string) => Promise<void>;
  onDelete: (owner: string, name: string) => void;
  onViewDetails: (owner: string, name: string) => void;
}

export default function WorkspaceCard({
  workspace,
  onStart,
  onStop,
  onDelete,
  onViewDetails,
}: WorkspaceCardProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const category = categorizeStatus(workspace.latest_build_status);

  const handleAction = async (action: 'start' | 'stop', fn: (owner: string, name: string) => Promise<void>) => {
    if (!workspace.owner_name) return;
    setActionLoading(action);
    try {
      await fn(workspace.owner_name, workspace.name);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-semibold text-gray-900 truncate">{workspace.name}</h3>
          <p className="text-sm text-gray-500 mt-1">{workspace.template_name || 'Unknown template'}</p>
        </div>
        <WorkspaceStatusBadge status={workspace.latest_build_status} />
      </div>

      {/* Info */}
      <div className="space-y-2 mb-4 text-sm text-gray-600">
        {workspace.created_at && (
          <div className="flex items-center gap-2">
            <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span>{new Date(workspace.created_at).toLocaleDateString()}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-4 border-t border-gray-200">
        {category === 'running' && (
          <>
            <button
              onClick={() => onViewDetails(workspace.owner_name || '', workspace.name)}
              className="flex-1 px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            >
              Open
            </button>
            <button
              onClick={() => handleAction('stop', onStop)}
              disabled={actionLoading === 'stop'}
              className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              {actionLoading === 'stop' ? 'Stopping...' : 'Stop'}
            </button>
          </>
        )}
        {category === 'stopped' && (
          <button
            onClick={() => handleAction('start', onStart)}
            disabled={actionLoading === 'start'}
            className="flex-1 px-3 py-2 text-sm font-medium text-green-700 bg-green-50 rounded-lg hover:bg-green-100 transition-colors disabled:opacity-50"
          >
            {actionLoading === 'start' ? 'Starting...' : 'Start'}
          </button>
        )}
        {category === 'pending' && (
          <span className="flex-1 px-3 py-2 text-sm text-center text-yellow-700 bg-yellow-50 rounded-lg">
            {workspace.latest_build_status}...
          </span>
        )}
        <button
          onClick={() => onViewDetails(workspace.owner_name || '', workspace.name)}
          className="px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          title="Details"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
        <button
          onClick={() => onDelete(workspace.owner_name || '', workspace.name)}
          className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Delete"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  );
}
