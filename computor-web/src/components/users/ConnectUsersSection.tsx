'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Modal from '@/src/components/Modal';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import UserSearchPicker, { userDisplayName } from '@/src/components/users/UserSearchPicker';
import { useNotify } from '@/src/contexts/NotificationContext';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
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

const COPY = {
  de: {
    duplicateRemoved: 'doppelte Mitgliedschaft beim importierten Benutzer wird entfernt',
    moveGroup: 'Mitgliedschaft wird verschoben (Kursgruppe wird übernommen)',
    move: 'Mitgliedschaft wird verschoben',
    studentEmail: (email: string) => `Studierenden-E-Mail ${email} geht an den zu behaltenden Benutzer`,
    merged: 'wird mit dem bestehenden Profil des zu behaltenden Benutzers zusammengeführt',
    profileMoves: 'Profil wird zum zu behaltenden Benutzer verschoben',
    memberships: (n: number) => `${n} ${n === 1 ? 'Kursmitgliedschaft' : 'Kursmitgliedschaften'} verschoben`,
    duplicates: (n: number) => `${n} ${n === 1 ? 'doppelte Mitgliedschaft' : 'doppelte Mitgliedschaften'} entfernt`,
    profiles: (n: number) => `${n} ${n === 1 ? 'Studierendenprofil' : 'Studierendenprofile'} übernommen`,
    roles: (n: number) => `${n} ${n === 1 ? 'Rolle' : 'Rollen'} zusammengeführt`,
    noData: ' Es gab keine Kursdaten zu verschieben.',
    checkFailed: 'Prüfung der Zusammenführung fehlgeschlagen',
    userFallback: 'Benutzer',
    connected: (source: string, keeper: string, summary: string) => `${source} wurde mit ${keeper} zusammengeführt.${summary}`,
    connectFailed: 'Benutzer konnten nicht zusammengeführt werden',
    absorbHeading: 'Vorab angelegten Benutzer übernehmen',
    connectHeading: 'Mit bestehendem Konto zusammenführen',
    absorbIntro: 'Wähle einen vorab angelegten Benutzer (aus einer Kursliste importiert, noch nie angemeldet), der in dieses Konto übernommen werden soll. Seine Kursmitgliedschaften, Studierendenprofile und Rollen wechseln hierher, danach wird der importierte Benutzer gelöscht.',
    connectIntro: 'Dieser Benutzer hat kein Anmeldekonto, er wurde vermutlich aus einer Kursliste importiert. Wähle das echte, bereits angemeldete Konto, das seine Kursmitgliedschaften, Studierendenprofile und Rollen übernehmen soll. Dieser importierte Benutzer wird anschließend gelöscht.',
    absorb: 'Übernehmen',
    connect: 'Zusammenführen',
    checking: 'Es wird geprüft, was verschoben würde…',
    dialogTitle: 'Benutzer zusammenführen',
    willBeAbsorbed: 'wird übernommen in',
    courseMemberships: 'Kursmitgliedschaften',
    studentProfiles: 'Studierendenprofile',
    rolesGained: 'Rollen, die der zu behaltende Benutzer erhält',
    accountsMove: (n: number) => `${n} verknüpfte${n === 1 ? 's Konto wird' : ' Konten werden'} zum zu behaltenden Benutzer verschoben.`,
    messagesRepointed: (n: number) => `${n} ${n === 1 ? 'Nachrichtenverweis wird' : 'Nachrichtenverweise werden'} umgehängt.`,
    nothingToMove: 'Nichts zu verschieben, der importierte Benutzer hat keine Kursdaten. Beim Zusammenführen wird er einfach gelöscht.',
    deleteWarning: (name: string, email: string) => `Der Benutzer ${name}${email} wird endgültig gelöscht.`,
    irreversible: 'Das kann nicht rückgängig gemacht werden.',
    cancel: 'Abbrechen',
    connecting: 'Wird zusammengeführt…',
    connectAndDelete: 'Zusammenführen und Benutzer löschen',
  },
  en: {
    duplicateRemoved: 'duplicate membership on the imported user will be removed',
    moveGroup: 'membership moves (course group carried over)',
    move: 'membership moves',
    studentEmail: (email: string) => `student email ${email} lands on the keeper`,
    merged: 'merged into the keeper’s existing profile',
    profileMoves: 'profile moves to the keeper',
    memberships: (n: number) => `${n} course membership${n === 1 ? '' : 's'} moved`,
    duplicates: (n: number) => `${n} duplicate membership${n === 1 ? '' : 's'} removed`,
    profiles: (n: number) => `${n} student profile${n === 1 ? '' : 's'} carried over`,
    roles: (n: number) => `${n} role${n === 1 ? '' : 's'} merged`,
    noData: ' There was no course data to move.',
    checkFailed: 'Connection check failed',
    userFallback: 'user',
    connected: (source: string, keeper: string, summary: string) => `Connected ${source} into ${keeper}.${summary}`,
    connectFailed: 'Failed to connect users',
    absorbHeading: 'Absorb a pre-provisioned user',
    connectHeading: 'Connect into an existing account',
    absorbIntro: 'Pick a pre-provisioned user (imported from a course roster, never logged in) to absorb into this account. Their course memberships, student profiles and roles move here, then the imported user is deleted.',
    connectIntro: 'This user has no login account — it was likely imported from a course roster. Pick the real, logged-in account that should take over its course memberships, student profiles and roles. This imported user is deleted afterwards.',
    absorb: 'Absorb',
    connect: 'Connect',
    checking: 'Checking what would move…',
    dialogTitle: 'Connect users',
    willBeAbsorbed: 'will be absorbed into',
    courseMemberships: 'Course memberships',
    studentProfiles: 'Student profiles',
    rolesGained: 'Roles gained by the keeper',
    accountsMove: (n: number) => `${n} linked account${n === 1 ? '' : 's'} move to the keeper.`,
    messagesRepointed: (n: number) => `${n} message reference${n === 1 ? '' : 's'} will be re-pointed.`,
    nothingToMove: 'Nothing to move — the imported user carries no course data. Connecting simply deletes it.',
    deleteWarning: (name: string, email: string) => `The user ${name}${email} will be permanently deleted.`,
    irreversible: 'This cannot be undone.',
    cancel: 'Cancel',
    connecting: 'Connecting…',
    connectAndDelete: 'Connect and delete user',
  },
};

function courseMoveText(m: UserConnectCourseMove, t: (typeof COPY)[UiLanguage]): string {
  if (m.action === 'duplicate_removed') return t.duplicateRemoved;
  return m.group_carried_over ? t.moveGroup : t.move;
}

function profileMoveText(p: UserConnectProfileMove, t: (typeof COPY)[UiLanguage]): string {
  const email = p.student_email ? t.studentEmail(p.student_email) : null;
  const how = p.action === 'merged' ? t.merged : t.profileMoves;
  return email ? `${how}; ${email}` : how;
}

/** Short "what moved" summary for the success toast. */
function summarize(res: UserConnectResponse, t: (typeof COPY)[UiLanguage]): string {
  const moves = res.course_memberships ?? [];
  const moved = moves.filter((m) => m.action === 'moved').length;
  const removed = moves.length - moved;
  const profiles = (res.student_profiles ?? []).length;
  const roles = (res.roles_merged ?? []).length;
  const parts: string[] = [];
  if (moved) parts.push(t.memberships(moved));
  if (removed) parts.push(t.duplicates(removed));
  if (profiles) parts.push(t.profiles(profiles));
  if (roles) parts.push(t.roles(roles));
  return parts.length ? ` ${parts.join(', ')}.` : t.noData;
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
  const language = useUiLanguage();
  const t = COPY[language];
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
      setInlineError(e instanceof Error ? e.message : t.checkFailed);
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
        t.connected(
          source ? userDisplayName(source) : t.userFallback,
          keeper ? userDisplayName(keeper) : t.userFallback,
          summarize(res, t),
        ),
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
      const msg = e instanceof Error ? e.message : t.connectFailed;
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
        {hasBuiltinAccount ? t.absorbHeading : t.connectHeading}
      </h2>
      <p className="text-sm text-muted">
        {hasBuiltinAccount ? t.absorbIntro : t.connectIntro}
      </p>

      <ErrorBanner>{inlineError}</ErrorBanner>

      <UserSearchPicker
        excludeId={user.id}
        onPick={pick}
        busy={checking || executing}
        pickLabel={hasBuiltinAccount ? t.absorb : t.connect}
      />
      {checking && <p className="text-sm text-muted">{t.checking}</p>}

      {plan && picked && keeper && source && (
        <Modal title={t.dialogTitle} onClose={closeDialog} maxWidth="max-w-lg">
          <div className="px-6 pt-2 pb-6 space-y-4">
            <p className="text-sm text-muted">
              <span className="font-medium text-fg">{userDisplayName(source)}</span>
              {source.email ? <span className="text-muted"> ({source.email})</span> : null} {t.willBeAbsorbed}{' '}
              <span className="font-medium text-fg">{userDisplayName(keeper)}</span>
              {keeper.email ? <span className="text-muted"> ({keeper.email})</span> : null}.
            </p>

            <div className="max-h-80 overflow-y-auto space-y-4 text-sm">
              {courseMoves.length > 0 && (
                <div>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">
                    {t.courseMemberships}
                  </h3>
                  <ul className="space-y-1">
                    {courseMoves.map((m) => (
                      <li key={m.course_id}>
                        <span className="font-medium text-fg">{m.course_title ?? m.course_id}</span>
                        <span className="text-muted"> — {courseMoveText(m, t)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {profileMoves.length > 0 && (
                <div>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">
                    {t.studentProfiles}
                  </h3>
                  <ul className="space-y-1">
                    {profileMoves.map((p) => (
                      <li key={p.organization_id}>
                        <span className="font-medium text-fg">
                          {p.organization_title ?? p.organization_id}
                        </span>
                        <span className="text-muted"> — {profileMoveText(p, t)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {rolesMerged.length > 0 && (
                <div>
                  <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted mb-1">
                    {t.rolesGained}
                  </h3>
                  <p className="text-muted">{rolesMerged.join(', ')}</p>
                </div>
              )}

              {(plan.accounts_moved ?? 0) > 0 && (
                <p className="text-muted">
                  {t.accountsMove(plan.accounts_moved ?? 0)}
                </p>
              )}
              {(plan.messages_repointed ?? 0) > 0 && (
                <p className="text-muted">
                  {t.messagesRepointed(plan.messages_repointed ?? 0)}
                </p>
              )}

              {planEmpty && (
                <p className="text-muted">
                  {t.nothingToMove}
                </p>
              )}
            </div>

            <div className="p-3 bg-danger-wash border border-danger-line rounded-md text-sm text-danger-text">
              <span className="font-semibold">
                {t.deleteWarning(userDisplayName(source), source.email ? ` (${source.email})` : '')}
              </span>{' '}
              {t.irreversible}
            </div>

            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={closeDialog} disabled={executing}>
                {t.cancel}
              </Button>
              <Button
                variant="danger"
                onClick={execute}
                loading={executing}
                loadingLabel={t.connecting}
              >
                {t.connectAndDelete}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
