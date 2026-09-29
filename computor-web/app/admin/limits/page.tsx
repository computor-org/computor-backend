'use client';

import { useMemo, useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import { InstanceLimitsClient } from '@/src/clients/InstanceLimitsClient';

const limitsClient = new InstanceLimitsClient();

interface FormState {
  maxWorkspaceUsers: string;
  maxConcurrentLogins: string;
  idleMinutes: string;
  registrationMode: RegistrationMode;
  maxRegisteredUsers: string;
  referralInvitesPerUser: string;
  pilotCourseIds: string;
}

type RegistrationMode = 'open' | 'invite_only' | 'closed';

const REGISTRATION_MODES: { value: RegistrationMode; label: string }[] = [
  { value: 'open', label: 'Open — anyone who signs in gets an account' },
  { value: 'invite_only', label: 'Invite only — a valid invite link is required' },
  { value: 'closed', label: 'Closed — no new accounts' },
];

/** '' → null, otherwise a non-negative integer (throws a user message). */
function parseLimit(label: string, raw: string): number | null {
  const text = raw.trim();
  if (!text) return null;
  const value = Number(text);
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(`${label} must be a non-negative whole number.`);
  }
  return value;
}

/** How close a count is to its ceiling, as a tone. */
function usageTone(used: number, limit: number | null | undefined) {
  if (limit == null) return 'muted' as const;
  if (used >= limit) return 'error' as const;
  if (limit > 0 && used / limit >= 0.8) return 'warning' as const;
  return 'success' as const;
}

/**
 * Instance limits (#351): how many people may be signed in, and how many may
 * hold a workspace, at the same time.
 *
 * Deliberately not on the workspace-templates page even though one of the two
 * is about workspaces: these are deployment-wide, they include a limit that has
 * nothing to do with workspaces, and the per-template quota over there is a
 * different kind of limit — a hard licence ceiling that binds admins too. Two
 * pages keeps the distinction visible instead of burying it in a paragraph.
 */
export default function InstanceLimitsPage() {
  const { isLoading: authLoading } = useAuth();
  const { isAdmin } = usePermissions();
  const notify = useNotify();
  const [draft, setDraft] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);

  // Poll: the usage half of this page is live state, and an admin watching a
  // workshop fill up is the reason the numbers are here at all.
  const { data, loading, error, reload } = useResource(
    () => limitsClient.get(),
    [],
    { refetchInterval: 10000 },
  );

  const stored = useMemo<FormState>(
    () => ({
      maxWorkspaceUsers: data?.max_workspace_users != null ? String(data.max_workspace_users) : '',
      maxConcurrentLogins:
        data?.max_concurrent_logins != null ? String(data.max_concurrent_logins) : '',
      idleMinutes: data?.login_idle_minutes != null ? String(data.login_idle_minutes) : '30',
      registrationMode: data?.registration_mode ?? 'open',
      maxRegisteredUsers:
        data?.max_registered_users != null ? String(data.max_registered_users) : '',
      referralInvitesPerUser:
        data?.referral_invites_per_user != null ? String(data.referral_invites_per_user) : '2',
      pilotCourseIds: (data?.pilot_course_ids ?? []).join(', '),
    }),
    [data],
  );

  // Overlay pattern: `stored` is derived from the fetch, `draft` holds local
  // edits — so the 10s poll cannot overwrite what the admin is typing.
  const form = draft ?? stored;

  function update(changes: Partial<FormState>) {
    setDraft({ ...form, ...changes });
  }

  async function save() {
    setSaving(true);
    try {
      const idle = parseLimit('Login idle window', form.idleMinutes);
      if (idle == null || idle < 1) {
        throw new Error('Login idle window must be at least 1 minute.');
      }
      const referrals = parseLimit('Referral invites per user', form.referralInvitesPerUser);
      await limitsClient.update({
        max_workspace_users: parseLimit('Max workspace users', form.maxWorkspaceUsers),
        max_concurrent_logins: parseLimit('Max concurrent logins', form.maxConcurrentLogins),
        login_idle_minutes: idle,
        registration_mode: form.registrationMode,
        max_registered_users: parseLimit('Max registered users', form.maxRegisteredUsers),
        referral_invites_per_user: referrals ?? 0,
        pilot_course_ids: form.pilotCourseIds
          .split(/[\s,]+/)
          .map((id) => id.trim())
          .filter(Boolean),
      });
      notify('Limits saved. They apply to the next sign-in or workspace launch.', 'success');
      setDraft(null);
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to save limits', 'error');
    } finally {
      setSaving(false);
    }
  }

  if (!authLoading && !isAdmin) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-danger-wash border border-danger-line rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-danger-text">Access Denied</h2>
            <p className="text-sm text-danger-text mt-2">
              Admin privileges are required to access this page.
            </p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const usage = data?.usage;
  const workspaceCountKnown = usage?.workspace_users_available !== false;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Instance limits' }]}
          title="Instance limits"
          subtitle="How many people may be signed in, and how many may hold a workspace, at the same time."
        />

        <ErrorBanner>{error}</ErrorBanner>

        <ScrollArea>
          {loading && !data && (
            <div className="bg-surface rounded-lg border border-rule p-6 animate-pulse">
              <div className="h-6 bg-sunken rounded w-1/4 mb-4" />
              <div className="h-4 bg-sunken rounded w-1/2" />
            </div>
          )}

          {data && (
            <div className="space-y-4">
              <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-fg">In use right now</h2>
                  <p className="text-sm text-muted mt-1">
                    Both counts are per <span className="font-medium">user</span>, not per
                    session or per workspace — someone signed in on two devices is one
                    person, and someone with two workspaces holds one seat.
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="bg-sunken rounded p-4">
                    <div className="text-xs font-medium text-muted">Registered users</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-fg">
                        {usage?.registered_users ?? 0}
                      </span>
                      <span className="text-sm text-muted">
                        of {data.max_registered_users ?? '∞'}
                      </span>
                      <Badge
                        tone={usageTone(usage?.registered_users ?? 0, data.max_registered_users)}
                        pill
                      >
                        {data.registration_mode === 'invite_only'
                          ? 'invite only'
                          : data.registration_mode ?? 'open'}
                      </Badge>
                    </div>
                  </div>

                  <div className="bg-sunken rounded p-4">
                    <div className="text-xs font-medium text-muted">Signed in</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-fg">{usage?.login_seats ?? 0}</span>
                      <span className="text-sm text-muted">
                        of {data.max_concurrent_logins ?? '∞'}
                      </span>
                      <Badge tone={usageTone(usage?.login_seats ?? 0, data.max_concurrent_logins)} pill>
                        {data.max_concurrent_logins == null ? 'no limit' : 'limited'}
                      </Badge>
                    </div>
                  </div>

                  <div className="bg-sunken rounded p-4">
                    <div className="text-xs font-medium text-muted">Holding a workspace</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-fg">
                        {workspaceCountKnown ? usage?.workspace_users ?? 0 : '—'}
                      </span>
                      <span className="text-sm text-muted">
                        of {data.max_workspace_users ?? '∞'}
                      </span>
                      {workspaceCountKnown ? (
                        <Badge
                          tone={usageTone(usage?.workspace_users ?? 0, data.max_workspace_users)}
                          pill
                        >
                          {data.max_workspace_users == null ? 'no limit' : 'limited'}
                        </Badge>
                      ) : (
                        <Badge tone="warning" pill>
                          Coder unreachable
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-fg">Limits</h2>
                  <p className="text-sm text-muted mt-1">
                    Leave a field empty for no limit. Administrators and the built-in
                    manager roles are never refused by either limit. Lowering a limit below
                    the current usage stops the next arrival — it never signs anyone out or
                    stops a running workspace.
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="limit-logins"
                      className="block text-xs font-medium text-body mb-1"
                    >
                      Max concurrent users signed in
                    </label>
                    <input
                      id="limit-logins"
                      value={form.maxConcurrentLogins}
                      onChange={(event) => update({ maxConcurrentLogins: event.target.value })}
                      placeholder="unlimited"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      A user already signed in is never refused, so raising and lowering this
                      only affects people arriving.
                    </p>
                  </div>

                  <div>
                    <label
                      htmlFor="limit-workspaces"
                      className="block text-xs font-medium text-body mb-1"
                    >
                      Max concurrent workspace users
                    </label>
                    <input
                      id="limit-workspaces"
                      value={form.maxWorkspaceUsers}
                      onChange={(event) => update({ maxWorkspaceUsers: event.target.value })}
                      placeholder="unlimited"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      Refused users are told to work locally in VS Code
                      {data.local_install_url ? ', with the download link' : ''}. Separate from
                      a template&apos;s seat quota, which models licence seats and binds
                      everyone.
                    </p>
                  </div>

                  <div>
                    <label htmlFor="limit-idle" className="block text-xs font-medium text-body mb-1">
                      Sign-in seat is released after (minutes idle)
                    </label>
                    <input
                      id="limit-idle"
                      value={form.idleMinutes}
                      onChange={(event) => update({ idleMinutes: event.target.value })}
                      placeholder="30"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      Keep this above 15. An active client re-checks its credentials at most
                      every 15 minutes, so a shorter window would release the seats of people
                      who are still working.
                    </p>
                  </div>
                </div>

                <div className="border-t border-rule pt-4">
                  <h3 className="text-sm font-semibold text-fg">Registration</h3>
                  <p className="text-sm text-muted mt-1">
                    Who may create an account on first sign-in (GitHub or email). Existing
                    users always sign in. The user cap is hard and counts everyone except
                    staff, service accounts and archived users.
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="reg-mode" className="block text-xs font-medium text-body mb-1">
                      Registration mode
                    </label>
                    <select
                      id="reg-mode"
                      value={form.registrationMode}
                      onChange={(event) =>
                        update({ registrationMode: event.target.value as RegistrationMode })
                      }
                      className={inputCls}
                    >
                      {REGISTRATION_MODES.map((mode) => (
                        <option key={mode.value} value={mode.value}>
                          {mode.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="reg-cap" className="block text-xs font-medium text-body mb-1">
                      Max registered users
                    </label>
                    <input
                      id="reg-cap"
                      value={form.maxRegisteredUsers}
                      onChange={(event) => update({ maxRegisteredUsers: event.target.value })}
                      placeholder="unlimited"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      Applies in every mode, even to a valid invite.
                    </p>
                  </div>

                  <div>
                    <label
                      htmlFor="reg-referrals"
                      className="block text-xs font-medium text-body mb-1"
                    >
                      Referral invites per user
                    </label>
                    <input
                      id="reg-referrals"
                      value={form.referralInvitesPerUser}
                      onChange={(event) => update({ referralInvitesPerUser: event.target.value })}
                      placeholder="2"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      Single-use invite links each user can share (invite-only mode). Seed
                      invites for the first users come from the invite admin page.
                    </p>
                  </div>

                  <div>
                    <label htmlFor="reg-courses" className="block text-xs font-medium text-body mb-1">
                      Pilot course ids
                    </label>
                    <input
                      id="reg-courses"
                      value={form.pilotCourseIds}
                      onChange={(event) => update({ pilotCourseIds: event.target.value })}
                      placeholder="none"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      Public courses every new user is enrolled in, comma separated. Each
                      course&apos;s own seat cap still applies.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-1">
                  <Button onClick={save} disabled={saving || draft === null}>
                    {saving ? 'Saving…' : 'Save limits'}
                  </Button>
                  {draft !== null && (
                    <Button variant="secondary" onClick={() => setDraft(null)} disabled={saving}>
                      Discard changes
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
