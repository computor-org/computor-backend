'use client';

import Modal from '@/src/components/Modal';
import WorkspaceStatusBadge from './WorkspaceStatusBadge';
import { workspaceStage } from './workspaceStage';
import type { WorkspaceDetails } from '@/src/types/workspaces';

/** Read-only workspace details (status, URLs, ids) in a modal. */
export default function WorkspaceDetailsModal({
  details,
  onClose,
}: {
  details: WorkspaceDetails;
  onClose: () => void;
}) {
  const ws = details.workspace;
  // The details endpoint knows the agent's lifecycle, so this is the one place
  // that can tell "the build is up" from "the editor is actually reachable".
  const stage = workspaceStage(details.status, undefined, details.agent_lifecycle);
  return (
    <Modal title="Workspace Details" onClose={onClose} maxWidth="max-w-lg">
      <div className="p-6 pt-4 max-h-[80vh] overflow-y-auto scroll-slim">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-gray-100">
              <tr>
                <td className="py-2 font-medium text-gray-600 pr-4">Name</td>
                <td className="py-2 text-gray-900">{ws.name}</td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-gray-600 pr-4 align-top">Status</td>
                <td className="py-2">
                  <div className="space-y-1.5">
                    <WorkspaceStatusBadge status={details.status} />
                    {/*
                      No bar (see WorkspaceTable) — but the words stay, because
                      this is the one view that knows the agent's lifecycle:
                      'running' and 'preparing the editor' are the same chip.
                    */}
                    {!stage.settled && (
                      <p className="text-xs text-gray-500">{stage.label}…</p>
                    )}
                  </div>
                </td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-gray-600 pr-4">Template</td>
                <td className="py-2 text-gray-900">{ws.template_display_name || ws.template_name}</td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-gray-600 pr-4">Owner</td>
                <td className="py-2 text-gray-900">{ws.owner_name}</td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-gray-600 pr-4">ID</td>
                <td className="py-2 text-gray-500 font-mono text-xs">{ws.id}</td>
              </tr>
              {details.access_url && (
                <tr>
                  <td className="py-2 font-medium text-gray-600 pr-4">Access URL</td>
                  <td className="py-2">
                    <a href={details.access_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs break-all">
                      {details.access_url}
                    </a>
                  </td>
                </tr>
              )}
              {details.code_server_url && details.code_server_url !== details.access_url && (
                <tr>
                  <td className="py-2 font-medium text-gray-600 pr-4">Editor URL</td>
                  <td className="py-2">
                    <a href={details.code_server_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs break-all">
                      {details.code_server_url}
                    </a>
                  </td>
                </tr>
              )}
              {ws.created_at && (
                <tr>
                  <td className="py-2 font-medium text-gray-600 pr-4">Created</td>
                  <td className="py-2 text-gray-900">{new Date(ws.created_at).toLocaleString()}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Modal>
  );
}
