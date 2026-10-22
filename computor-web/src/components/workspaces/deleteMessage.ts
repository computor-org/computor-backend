import type { CoderWorkspace } from '@/src/types/workspaces';
import type { UiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: {
    intro: (name: string) => `Möchtest du die Arbeitsumgebung "${name}" wirklich löschen?`,
    scratch:
      'Diese Arbeitsumgebung hat ein eigenes temporäres Home-Verzeichnis, das mit ihr GELÖSCHT wird. ' +
      'Dateien, die nicht gepusht oder heruntergeladen wurden, gehen verloren.',
    shared: (self: boolean) =>
      `${self ? 'Dein' : 'Das'} Home-Verzeichnis ${self ? '' : 'der Person '}wird von allen Arbeitsumgebungen geteilt und wird NICHT gelöscht.`,
    unknown: (self: boolean) =>
      `${self ? 'Dein' : 'Das'} Home-Verzeichnis ${self ? '' : 'der Person '}wird von allen Arbeitsumgebungen geteilt und sollte NICHT betroffen sein.`,
  },
  en: {
    intro: (name: string) => `Are you sure you want to delete workspace "${name}"?`,
    scratch:
      'This workspace has its own scratch home directory, which will be ' +
      'DELETED with it. Any files that have not been pushed or downloaded will be lost.',
    shared: (self: boolean) =>
      `${self ? 'Your' : "The user's"} home directory is shared across workspaces and will NOT be deleted.`,
    unknown: (self: boolean) =>
      `${self ? 'Your' : "The user's"} home directory is shared across workspaces and should NOT be affected.`,
  },
};

/**
 * What deleting this workspace actually destroys.
 *
 * A workspace provisioned with `home_mode: "scratch"` mounts its own volume,
 * owned by Terraform and torn down with the workspace. Only the default shared
 * home survives. Both delete dialogs used to promise safety unconditionally,
 * which is a lie for the scratch workspaces lecturers hand out in bulk.
 *
 * `home_mode` is read from the latest build's parameters and may be absent (an
 * older build, or a failed lookup). Unknown is treated as shared, matching how
 * provisioning defaults — but say "should not" rather than "will not", because
 * we did not actually confirm it.
 */
export function workspaceDeleteMessage(
  workspaceName: string,
  workspace: CoderWorkspace | undefined,
  owner: 'self' | 'other' = 'self',
  language: UiLanguage = 'en',
): string {
  const t = COPY[language];
  const self = owner === 'self';
  const intro = t.intro(workspaceName);

  if (workspace?.home_mode === 'scratch') return `${intro} ${t.scratch}`;
  if (workspace?.home_mode === 'shared') return `${intro} ${t.shared(self)}`;
  return `${intro} ${t.unknown(self)}`;
}
