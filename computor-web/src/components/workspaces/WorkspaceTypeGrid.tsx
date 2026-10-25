'use client';

import Link from 'next/link';
import type { CoderWorkspace } from '@/src/types/workspaces';
import { derivedWorkspaceName } from '@/src/utils/workspaceLaunch';
import TemplateCard from './TemplateCard';
import WorkspaceStatusBadge, { categorizeStatus } from './WorkspaceStatusBadge';
import { isUsable, type TemplateOption } from './templateOptions';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    none: 'Für dich sind noch keine Arten von Arbeitsumgebungen verfügbar.',
    maintainerPre: 'Es wird nichts automatisch bereitgestellt. Wähle unter ',
    maintainerLink: 'Administration → Vorlagen',
    maintainerPost: ' aus, welche Arten diese Installation anbietet.',
    contact: 'Falls sich das nicht von selbst löst, wende dich an deine Administration.',
    create: 'Arbeitsumgebung erstellen',
    open: 'Arbeitsumgebung öffnen',
    startOpen: 'Starten und öffnen',
    failed: 'Fehlgeschlagen, zum Ansehen öffnen',
    openWhenReady: 'Öffnen, sobald bereit',
  },
  en: {
    none: 'No workspace types are available to you yet.',
    maintainerPre: 'Nothing is deployed automatically — pick which ones this deployment offers under ',
    maintainerLink: 'Administration → Templates',
    maintainerPost: '.',
    contact: 'If this does not resolve itself, contact your administrator.',
    create: 'Create workspace',
    open: 'Open workspace',
    startOpen: 'Start and open',
    failed: 'Failed — open for details',
    openWhenReady: 'Open when ready',
  },
};

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
  const t = COPY[useUiLanguage()];
  if (options.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-rule-strong bg-canvas p-4 text-sm text-muted">
        <p>{t.none}</p>
        {isMaintainer ? (
          <p className="mt-1">
            {t.maintainerPre}
            <Link
              href="/workspaces/admin?tab=templates"
              className="text-accent-text hover:underline"
            >
              {t.maintainerLink}
            </Link>
            {t.maintainerPost}
          </p>
        ) : (
          <p className="mt-1">{t.contact}</p>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {options.map((option) => {
        const own = ownWorkspace(option, workspaces);

        if (!own) {
          return (
            <TemplateCard
              key={option.name}
              option={option}
              actionLabel={t.create}
              busy={busyTemplate === option.name}
              onClick={() => onCreate(option.name)}
            />
          );
        }

        const category = categorizeStatus(own.latest_build_status, own.latest_build_transition);
        return (
          <TemplateCard
            key={option.name}
            option={option}
            // What the click does, never what the badge beside it already
            // says: while a workspace is stopping, "Stopping" belongs in the
            // chip once, not in the chip and in the line under the title.
            // (The card's own stage bar, when it has one, is about the
            // TEMPLATE being deployed — a different fact about a different
            // thing, which is why both can be on one card.)
            actionLabel={
              category === 'running' ? t.open
              : category === 'stopped' ? t.startOpen
              : category === 'failed' ? t.failed
              : t.openWhenReady
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

/**
 * What provisioning without a name would produce for this type — the
 * workspace a click on its card opens, or creates. Self-provisioners never get
 * any other name, so for them this is simply "their" workspace.
 */
export function ownWorkspace(
  option: TemplateOption,
  workspaces: CoderWorkspace[],
): CoderWorkspace | undefined {
  const derived = derivedWorkspaceName(option.name);
  return workspaces.find((w) => w.template_name === option.name && w.name === derived);
}

/** Types a maintainer may pick in the custom-name form. */
export function usableOptions(options: TemplateOption[]): TemplateOption[] {
  return options.filter(isUsable);
}
