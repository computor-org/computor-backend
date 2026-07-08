'use client';

import { useState } from 'react';
import type { CoderWorkspace } from '@/src/types/workspaces';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import WorkspaceStatusBadge, { categorizeStatus } from './WorkspaceStatusBadge';

interface WorkspaceTableProps {
  workspaces: CoderWorkspace[];
  onStart: (owner: string, name: string) => Promise<void>;
  onStop: (owner: string, name: string) => Promise<void>;
  onDelete: (owner: string, name: string) => void;
  onViewDetails: (owner: string, name: string) => void;
}

const actionBtn =
  'px-2.5 py-1 text-xs font-medium rounded-md transition-colors disabled:opacity-50';

function WorkspaceRow({
  workspace,
  onStart,
  onStop,
  onDelete,
  onViewDetails,
}: {
  workspace: CoderWorkspace;
  onStart: (owner: string, name: string) => Promise<void>;
  onStop: (owner: string, name: string) => Promise<void>;
  onDelete: (owner: string, name: string) => void;
  onViewDetails: (owner: string, name: string) => void;
}) {
  const [actionLoading, setActionLoading] = useState<'start' | 'stop' | null>(null);
  const owner = workspace.owner_name || '';
  const category = categorizeStatus(workspace.latest_build_status);

  const runAction = async (action: 'start' | 'stop', fn: (o: string, n: string) => Promise<void>) => {
    if (!owner) return;
    setActionLoading(action);
    try {
      await fn(owner, workspace.name);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <Tr className="hover:bg-gray-50">
      <Td>
        <span className="font-medium text-gray-900 text-sm">{workspace.name}</span>
      </Td>
      <Td className="text-sm text-gray-600">{workspace.template_name || '—'}</Td>
      <Td>
        <WorkspaceStatusBadge status={workspace.latest_build_status} size="sm" />
      </Td>
      <Td className="text-sm text-gray-500 whitespace-nowrap">
        {workspace.created_at ? new Date(workspace.created_at).toLocaleDateString() : '—'}
      </Td>
      <Td>
        <div className="flex items-center justify-end gap-1.5">
          {category === 'running' && (
            <>
              <button
                onClick={() => onViewDetails(owner, workspace.name)}
                className={`${actionBtn} text-blue-700 bg-blue-50 hover:bg-blue-100`}
              >
                Open
              </button>
              <button
                onClick={() => runAction('stop', onStop)}
                disabled={actionLoading === 'stop'}
                className={`${actionBtn} text-gray-700 bg-gray-100 hover:bg-gray-200`}
              >
                {actionLoading === 'stop' ? 'Stopping…' : 'Stop'}
              </button>
            </>
          )}
          {(category === 'stopped' || category === 'failed') && (
            <button
              onClick={() => runAction('start', onStart)}
              disabled={actionLoading === 'start'}
              className={`${actionBtn} text-green-700 bg-green-50 hover:bg-green-100`}
            >
              {actionLoading === 'start' ? 'Starting…' : 'Start'}
            </button>
          )}
          {category === 'pending' && (
            <span className={`${actionBtn} text-yellow-700 bg-yellow-50`}>
              {workspace.latest_build_status}…
            </span>
          )}
          <button
            onClick={() => onViewDetails(owner, workspace.name)}
            className={`${actionBtn} text-gray-600 hover:bg-gray-100`}
          >
            Details
          </button>
          <button
            onClick={() => onDelete(owner, workspace.name)}
            className={`${actionBtn} text-red-600 hover:bg-red-50`}
          >
            Delete
          </button>
        </div>
      </Td>
    </Tr>
  );
}

/** Dense, space-efficient list of workspaces with inline row actions. */
export default function WorkspaceTable({
  workspaces,
  onStart,
  onStop,
  onDelete,
  onViewDetails,
}: WorkspaceTableProps) {
  return (
    <Table>
      <Thead>
        <tr>
          <Th>Name</Th>
          <Th>Template</Th>
          <Th>Status</Th>
          <Th>Created</Th>
          <Th className="text-right">Actions</Th>
        </tr>
      </Thead>
      <Tbody>
        {workspaces.map((ws) => (
          <WorkspaceRow
            key={ws.id}
            workspace={ws}
            onStart={onStart}
            onStop={onStop}
            onDelete={onDelete}
            onViewDetails={onViewDetails}
          />
        ))}
      </Tbody>
    </Table>
  );
}
