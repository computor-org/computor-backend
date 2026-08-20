'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Modal from '@/src/components/Modal';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import UserSearchPicker, { userDisplayName } from '@/src/components/users/UserSearchPicker';
import { useNotify } from '@/src/contexts/NotificationContext';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type {
  UserConnectCourseMove,
  UserConnectProfileMove,
  UserConnectResponse,
  UserGet,
  UserList,
} from 'types/generated';

const usersClient = new UsersClient();

/** Both UserGet and UserList satisfy this — all the dialog needs to name a party. */
type UserRef = {
  id: string;
  given_name?: string | null;
  family_name?: string | null;
  email?: string | null;
};

function courseMoveText(m: UserConnectCourseMove): string {
  if (m.action === 'duplicate_removed') {
    return 'duplicate membership on the imported user will be removed';
  }
  return m.group_carried_over ? 'membership moves (course group carried over)' : 'membership moves';
}

function profileMoveText(p: UserConnectProfileMove): string {
  const email = p.student_email ? `student email ${p.student_email} lands on the keeper` : null;
  const how =
    p.action === 'merged' ? 'merged into the keeper’s existing profile' : 'profile moves to the keeper';
  return email ? `${how}; ${email}` : how;
}

/** Short "what moved" summary for the success toast. */
function summarize(res: UserConnectResponse): string {
  const moves = res.course_memberships ?? [];
  const moved = moves.filter((m) => m.action === 'moved').length;
  const removed = moves.length - moved;
  const profiles = (res.student_profiles ?? []).length;
  const roles = (res.roles_merged ?? []).length;
  const parts: string[] = [];
  if (moved) parts.push(`${moved} course membership${moved === 1 ? '' : 's'} moved`);
  if (removed) parts.push(`${removed} duplicate membership${removed === 1 ? '' : 's'} removed`);
  if (profiles) parts.push(`${profiles} student profile${profiles === 1 ? '' : 's'} carried over`);
  if (roles) parts.push(`${roles} role${roles === 1 ? '' : 's'} merged`);
  return parts.length ? ` ${parts.join(', ')}.` : ' There was no course data to move.';
}

/**
 * "Connect users" panel for the admin user detail page.
 *
 * Adapts to the viewed user: a real login account (has a builtin auth account)
 * absorbs a pre-provisioned roster import; a pre-provisioned user is connected
 * INTO a picked real account, after which the viewed row no longer exists and
 * we navigate to the keeper.
 *
 * Picking a candidate runs a `dry_run` first; server-side validation is
 * authoritative and its message is shown inline so the admin can pick someone
 * else. Only a successful dry run opens the confirmation dialog, which lists
 * the exact merge plan the server returned.
 */
export default function ConnectUsersSection({
  user,
  hasBuiltinAccount,
  onConnected,
}: {
  /** The user whose detail page this section sits on. */
  user: UserGet;
  /** Whether the viewed user has a builtin (SSO / git) account, i.e. has really logged in. */
  hasBuiltinAccount: boolean;
  /** Called after a successful absorb in keeper-direction (refresh page data). */
  onConnected: () => void | Promise<void>;
}) {
  const router = useRouter();
  const notify = useNotify();

  const [picked, setPicked] = useState<UserList | null>(null);
  const [plan, setPlan] = useState<UserConnectResponse | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [executing, setExecuting] = useState(false);

  // Direction 1 (viewed user is the keeper): absorb the picked import.
  // Direction 2 (viewed user is the import): connect into the picked keeper.
  const keeper: UserRef | null = hasBuiltinAccount ? user : picked;
  const source: UserRef | null = hasBuiltinAccount ? picked : user;

  async function connect(counterpart: UserList, dryRun: boolean): Promise<UserConnectResponse> {
    const keeperId = hasBuiltinAccount ? user.id : counterpart.id;
    const sourceId = hasBuiltinAccount ? counterpart.id : user.id;
    return usersClient.connectUserUsersUserIdConnectPost({
      userId: keeperId,
      body: { source_user_id: sourceId, dry_run: dryRun },
    });
  }

  async function pick(candidate: UserList) {
    setInlineError(null);
    setChecking(true);
    try {
      const res = await connect(candidate, true);
      setPicked(candidate);
      setPlan(res);
    } catch (e) {
      setInlineError(e instanceof Error ? e.message : 'Connection check failed');
    } finally {
      setChecking(false);
    }
  }

  function closeDialog() {
    if (executing) return;
    setPlan(null);
    setPicked(null);
  }

  async function execute() {
    if (!picked) return;
    setExecuting(true);
    try {
      const res = await connect(picked, false);
      const keeperId = res.target_user_id;
      notify(
        `Connected ${source ? userDisplayName(source) : 'user'} into ${keeper ? userDisplayName(keeper) : 'user'}.${summarize(res)}`,
        'success',
      );
      setPlan(null);
      setPicked(null);
      if (hasBuiltinAccount) {
        await onConnected();
      } else {
        // The viewed user no longer exists — go to the account that absorbed it.
        router.push(`/admin/users/${keeperId}`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to connect users';
      setInlineError(msg);
      notify(msg, 'error');
      // Close the dialog; the plan may no longer be valid.
      setPlan(null);
      setPicked(null);
    } finally {
      setExecuting(false);
    }
  }

  const courseMoves = plan?.course_memberships ?? [];
  const profileMoves = plan?.student_profiles ?? [];
  const rolesMerged = plan?.roles_merged ?? [];
  const planEmpty =
    courseMoves.length === 0 &&
    profileMoves.length === 0 &&
    rolesMerged.length === 0 &&
    !(plan?.accounts_moved ?? 0) &&
    !(plan?.messages_repointed ?? 0);

  return (
    <section className="bg-surface border border-rule rounded-md p-6 space-y-3">
      <h2 className="text-lg font-semibold text-fg">
        {hasBuiltinAccount ? 'Absorb a pre-provisioned user' : 'Connect into an existing account'}
      </h2>
      <p className="text-sm text-muted">
        {hasBuiltinAccount
          ? 'Pick a pre-provisioned user (imported from a course roster, never logged in) to absorb into ' +
            'this account. Their course memberships, student profiles and roles move here, then the ' +
            'imported user is deleted.'
          : 'This user has no login account — it was likely imported from a course roster. Pick the real, ' +
            'logged-in account that should take over its course memberships, student profiles and roles. ' +
            'This imported user is deleted afterwards.'}
      </p>

      <ErrorBanner>{inlineError}</ErrorBanner>

      <UserSearchPicker
        excludeId={user.id}
        onPick={pick}
        busy={checking || executing}
        pickLabel={hasBuiltinAccount ? 'Absorb' : 'Connect'}
      />
      {checking && <p className="text-sm text-muted">Checking what would move…</p>}

      {plan && picked && keeper && source && (
        <Modal title="Connect users" onClose={closeDialog} maxWidth="max-w-lg">
          <div className="px-6 pt-2 pb-6 space-y-4">
            <p className="text-sm text-muted">
              <span className="font-medium text-fg">{userDisplayName(source)}</span>
              {source.email ? <span className="text-muted"> ({source.email})</span> : null} will be
              absorbed into <span className="font-medium text-fg">{userDisplayName(keeper)}</span>
              {keeper.email ? <span className="text-muted"> ({keeper.email})</span> : null}.
            </p>

            <div className="max-h-80 overflow-y-auto space-y-4 text-sm">
              {courseMoves.length > 0 && (
                <div>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">
                    Course memberships
                  </h3>
                  <ul className="space-y-1">
                    {courseMoves.map((m) => (
                      <li key={m.course_id}>
                        <span className="font-medium text-fg">{m.course_title ?? m.course_id}</span>
                        <span className="text-muted"> — {courseMoveText(m)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {profileMoves.length > 0 && (
                <div>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">
                    Student profiles
                  </h3>
                  <ul className="space-y-1">
                    {profileMoves.map((p) => (
                      <li key={p.organization_id}>
                        <span className="font-medium text-fg">
                          {p.organization_title ?? p.organization_id}
                        </span>
                        <span className="text-muted"> — {profileMoveText(p)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {rolesMerged.length > 0 && (
                <div>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">
                    Roles gained by the keeper
                  </h3>
                  <p className="text-muted">{rolesMerged.join(', ')}</p>
                </div>
              )}

              {(plan.accounts_moved ?? 0) > 0 && (
                <p className="text-muted">
                  {plan.accounts_moved} linked account{plan.accounts_moved === 1 ? '' : 's'} move to the
                  keeper.
                </p>
              )}
              {(plan.messages_repointed ?? 0) > 0 && (
                <p className="text-muted">
                  {plan.messages_repointed} message reference
                  {plan.messages_repointed === 1 ? '' : 's'} will be re-pointed.
                </p>
              )}

              {planEmpty && (
                <p className="text-muted">
                  Nothing to move — the imported user carries no course data. Connecting simply deletes
                  it.
                </p>
              )}
            </div>

            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
              <span className="font-semibold">
                The user {userDisplayName(source)}
                {source.email ? ` (${source.email})` : ''} will be permanently deleted.
              </span>{' '}
              This cannot be undone.
            </div>

            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={closeDialog} disabled={executing}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={execute}
                loading={executing}
                loadingLabel="Connecting…"
              >
                Connect and delete user
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
