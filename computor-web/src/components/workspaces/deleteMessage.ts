import type { CoderWorkspace } from '@/src/types/workspaces';

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
): string {
  const whose = owner === 'self' ? 'Your' : "The user's";
  const intro = `Are you sure you want to delete workspace "${workspaceName}"?`;

  if (workspace?.home_mode === 'scratch') {
    return (
      `${intro} This workspace has its own scratch home directory, which will be ` +
      'DELETED with it. Any files that have not been pushed or downloaded will be lost.'
    );
  }

  if (workspace?.home_mode === 'shared') {
    return `${intro} ${whose} home directory is shared across workspaces and will NOT be deleted.`;
  }

  return `${intro} ${whose} home directory is shared across workspaces and should NOT be affected.`;
}
