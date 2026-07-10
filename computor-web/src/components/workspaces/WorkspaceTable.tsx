'use client';

import { useState } from 'react';
import type { CoderWorkspace } from '@/src/types/workspaces';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import Button from '@/src/components/ui/Button';
import WorkspaceStatusBadge, { categorizeStatus } from './WorkspaceStatusBadge';

interface WorkspaceTableProps {
  workspaces: CoderWorkspace[];
  onStart: (owner: string, name: string) => Promise<void>;
  onStop: (owner: string, name: string) => Promise<void>;
  onDelete: (owner: string, name: string) => void;
  onViewDetails: (owner: string, name: string) => void;
}

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
      <Td className="text-sm text-gray-600">
        {workspace.template_display_name || workspace.template_name || '—'}
      </Td>
      <Td>
        <WorkspaceStatusBadge status={workspace.latest_build_status} />
      </Td>
      <Td className="text-sm text-gray-500 whitespace-nowrap">
        {workspace.created_at ? new Date(workspace.created_at).toLocaleDateString() : '—'}
      </Td>
      <Td>
        <div className="flex items-center justify-end gap-1.5">
          {category === 'running' && (
            <>
              <Button size="xs" onClick={() => onViewDetails(owner, workspace.name)}>
                Open
              </Button>
              <Button
                size="xs"
                variant="secondary"
                onClick={() => runAction('stop', onStop)}
                loading={actionLoading === 'stop'}
                loadingLabel="Stopping…"
              >
                Stop
              </Button>
            </>
          )}
          {(category === 'stopped' || category === 'failed') && (
            <Button
              size="xs"
              onClick={() => runAction('start', onStart)}
              loading={actionLoading === 'start'}
              loadingLabel="Starting…"
            >
              Start
            </Button>
          )}
          {category === 'pending' && (
            <span className="px-2.5 py-1 text-xs font-medium text-yellow-700">
              {workspace.latest_build_status}…
            </span>
          )}
          <Button size="xs" variant="ghost" onClick={() => onViewDetails(owner, workspace.name)}>
            Details
          </Button>
          <Button size="xs" variant="dangerGhost" onClick={() => onDelete(owner, workspace.name)}>
            Delete
          </Button>
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
