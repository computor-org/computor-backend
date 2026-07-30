'use client';

import Link from 'next/link';
import type { CoderWorkspace } from '@/src/types/workspaces';
import { derivedWorkspaceName } from '@/src/utils/workspaceLaunch';
import TemplateCard from './TemplateCard';
import WorkspaceStatusBadge, { categorizeStatus } from './WorkspaceStatusBadge';
import { isUsable, type TemplateOption } from './templateOptions';
import { workspaceStage } from './workspaceStage';

/**
 * The workspace types a user can have, as the place they create one.
 *
 * Creation used to be its own page, which for a self-provisioning user was a
 * navigation step wrapped around a single choice: the server forces their
 * workspace's name, so they get exactly one per type — the list of types IS
 * the list of workspaces they can have. Putting it here also means the answer
 * to "why can't I make the MATLAB one" is on the screen that raised the
 * question, whether the answer is "it is building" or "nobody deployed it".
 *
 * Maintainers are the exception the cards cannot express — custom names, more
 * than one workspace per type — which is what the inline form beside this is
 * for.
 */
export default function WorkspaceTypeGrid({
  options,
  workspaces,
  busyTemplate,
  onCreate,
  onOpen,
  isMaintainer,
}: {
  options: TemplateOption[];
  /** The caller's own workspaces, for the card that already has one. */
  workspaces: CoderWorkspace[];
  /** Template whose creation is in flight. */
  busyTemplate?: string | null;
  onCreate: (templateName: string) => void;
  onOpen: (workspace: CoderWorkspace) => void;
  isMaintainer: boolean;
}) {
  if (options.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500">
        <p>No workspace types are available to you yet.</p>
        {isMaintainer ? (
          <p className="mt-1">
            Nothing is deployed automatically — pick which ones this deployment offers under{' '}
            <Link
              href="/workspaces/admin?tab=templates"
              className="text-blue-600 hover:underline"
            >
              Administration → Templates
            </Link>
            .
          </p>
        ) : (
          <p className="mt-1">If this does not resolve itself, contact your administrator.</p>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {options.map((option) => {
        // What provisioning without a name would produce — the workspace a
        // click on this card opens, or creates. Self-provisioners never get
        // any other name, so for them this is simply "their" workspace.
        const derived = derivedWorkspaceName(option.name);
        const own = workspaces.find(
          (w) => w.template_name === option.name && w.name === derived,
        );

        if (!own) {
          return (
            <TemplateCard
              key={option.name}
              option={option}
              actionLabel="Create workspace"
              busy={busyTemplate === option.name}
              onClick={() => onCreate(option.name)}
            />
          );
        }

        const category = categorizeStatus(own.latest_build_status, own.latest_build_transition);
        const stage = workspaceStage(own.latest_build_status, own.latest_build_transition);
        return (
          <TemplateCard
            key={option.name}
            option={option}
            // The card's own stage bar is about the TEMPLATE being deployed;
            // this line is about the user's workspace on it. Both can be true
            // at once (an update runs while your workspace is up), so they are
            // kept as separate sentences rather than one merged status.
            actionLabel={
              category === 'running' ? 'Open workspace'
              : category === 'stopped' ? 'Start and open'
              : category === 'failed' ? 'Failed — open for details'
              : `${stage.label}…`
            }
            trailing={
              <WorkspaceStatusBadge
                status={own.latest_build_status}
                transition={own.latest_build_transition}
              />
            }
            onClick={() => onOpen(own)}
          />
        );
      })}
    </div>
  );
}

/** Types a maintainer may pick in the custom-name form. */
export function usableOptions(options: TemplateOption[]): TemplateOption[] {
  return options.filter(isUsable);
}
