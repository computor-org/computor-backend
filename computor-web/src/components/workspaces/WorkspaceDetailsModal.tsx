'use client';

import Modal from '@/src/components/Modal';
import WorkspaceStatusBadge from './WorkspaceStatusBadge';
import { workspaceStage } from './workspaceStage';
import type { WorkspaceDetails } from '@/src/types/workspaces';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    title: 'Details der Arbeitsumgebung',
    name: 'Name',
    status: 'Status',
    template: 'Vorlage',
    owner: 'Besitzer',
    id: 'ID',
    accessUrl: 'Zugriffs-URL',
    editorUrl: 'Editor-URL',
    created: 'Erstellt',
  },
  en: {
    title: 'Workspace Details',
    name: 'Name',
    status: 'Status',
    template: 'Template',
    owner: 'Owner',
    id: 'ID',
    accessUrl: 'Access URL',
    editorUrl: 'Editor URL',
    created: 'Created',
  },
};

/** Read-only workspace details (status, URLs, ids) in a modal. */
export default function WorkspaceDetailsModal({
  details,
  onClose,
}: {
  details: WorkspaceDetails;
  onClose: () => void;
}) {
  const language = useUiLanguage();
  const t = COPY[language];
  const ws = details.workspace;
  // The details endpoint knows the agent's lifecycle, so this is the one place
  // that can tell "the build is up" from "the editor is actually reachable".
  const stage = workspaceStage(details.status, undefined, details.agent_lifecycle, language);
  return (
    <Modal title={t.title} onClose={onClose} maxWidth="max-w-lg">
      <div className="p-6 pt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody className="divide-y divide-rule-soft">
              <tr>
                <td className="py-2 font-medium text-muted pr-4">{t.name}</td>
                <td className="py-2 text-fg">{ws.name}</td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-muted pr-4 align-top">{t.status}</td>
                <td className="py-2">
                  <div className="space-y-1.5">
                    <WorkspaceStatusBadge status={details.status} />
                    {/*
                      No bar (see WorkspaceTable) — but the words stay, because
                      this is the one view that knows the agent's lifecycle:
                      'running' and 'preparing the editor' are the same chip.
                    */}
                    {!stage.settled && (
                      <p className="text-xs text-muted">{stage.label}…</p>
                    )}
                  </div>
                </td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-muted pr-4">{t.template}</td>
                <td className="py-2 text-fg">{ws.template_display_name || ws.template_name}</td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-muted pr-4 align-top">{t.owner}</td>
                {/*
                  The Coder username is an encoding of the Computor user id, so
                  it reads as noise; the backend resolves the person behind it.
                  It still addresses the workspace in Coder's URLs, which is why
                  a details view keeps it visible underneath.
                */}
                <td className="py-2 text-fg">
                  {ws.owner_display_name || ws.owner_email || ws.owner_name}
                  {(ws.owner_display_name || ws.owner_email) && ws.owner_name && (
                    <div className="text-muted font-mono text-xs">{ws.owner_name}</div>
                  )}
                </td>
              </tr>
              <tr>
                <td className="py-2 font-medium text-muted pr-4">{t.id}</td>
                <td className="py-2 text-muted font-mono text-xs">{ws.id}</td>
              </tr>
              {details.access_url && (
                <tr>
                  <td className="py-2 font-medium text-muted pr-4">{t.accessUrl}</td>
                  <td className="py-2">
                    <a href={details.access_url} target="_blank" rel="noopener noreferrer" className="text-accent-text hover:underline text-xs break-all">
                      {details.access_url}
                    </a>
                  </td>
                </tr>
              )}
              {details.code_server_url && details.code_server_url !== details.access_url && (
                <tr>
                  <td className="py-2 font-medium text-muted pr-4">{t.editorUrl}</td>
                  <td className="py-2">
                    <a href={details.code_server_url} target="_blank" rel="noopener noreferrer" className="text-accent-text hover:underline text-xs break-all">
                      {details.code_server_url}
                    </a>
                  </td>
                </tr>
              )}
              {ws.created_at && (
                <tr>
                  <td className="py-2 font-medium text-muted pr-4">{t.created}</td>
                  <td className="py-2 text-fg">{new Date(ws.created_at).toLocaleString(language === 'de' ? 'de-AT' : undefined)}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Modal>
  );
}
