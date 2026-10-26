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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatNumber } from '@/src/utils/locale';

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

const REGISTRATION_MODE_VALUES: RegistrationMode[] = ['open', 'invite_only', 'closed'];

const COPY = {
  de: {
    modeOpen: 'Offen: Jeder, der sich anmeldet, erhält ein Konto',
    modeInviteOnly: 'Nur mit Einladung: Ein gültiger Einladungslink ist erforderlich',
    modeClosed: 'Geschlossen: Keine neuen Konten',
    modeBadgeOpen: 'offen',
    modeBadgeInviteOnly: 'nur mit Einladung',
    modeBadgeClosed: 'geschlossen',
    mustBeWhole: (label: string) => `${label} muss eine nicht negative ganze Zahl sein.`,
    labelIdle: 'Zeitfenster für Inaktivität bei der Anmeldung',
    labelReferrals: 'Empfehlungseinladungen pro Benutzer',
    labelMaxWorkspace: 'Maximale Benutzer mit Arbeitsumgebung',
    labelMaxLogins: 'Maximale gleichzeitige Anmeldungen',
    labelMaxRegistered: 'Maximale registrierte Benutzer',
    idleMin: 'Das Zeitfenster für Inaktivität bei der Anmeldung muss mindestens 1 Minute betragen.',
    saved: 'Limits gespeichert. Sie gelten ab der nächsten Anmeldung oder dem nächsten Start einer Arbeitsumgebung.',
    saveFailed: 'Limits konnten nicht gespeichert werden',
    denied: 'Zugriff verweigert',
    adminRequired: 'Für diese Seite sind Administratorrechte erforderlich.',
    title: 'Instanzlimits',
    subtitle: 'Wie viele Personen gleichzeitig angemeldet sein dürfen und wie viele gleichzeitig eine Arbeitsumgebung belegen dürfen.',
    inUse: 'Aktuell in Benutzung',
    inUseIntro1: 'Beide Zahlen zählen je ',
    inUseUser: 'Benutzer',
    inUseIntro2: ', nicht je Sitzung oder Arbeitsumgebung. Wer auf zwei Geräten angemeldet ist, zählt als eine Person, und wer zwei Arbeitsumgebungen hat, belegt einen Platz.',
    registeredUsers: 'Registrierte Benutzer',
    of: 'von',
    signedIn: 'Angemeldet',
    noLimit: 'kein Limit',
    limited: 'begrenzt',
    holdingWorkspace: 'Mit Arbeitsumgebung',
    coderUnreachable: 'Coder nicht erreichbar',
    limits: 'Limits',
    limitsIntro: 'Lass ein Feld leer, wenn es kein Limit geben soll. Administratoren und die integrierten Manager-Rollen werden von keinem der beiden Limits abgewiesen. Wird ein Limit unter die aktuelle Nutzung gesenkt, stoppt es den nächsten Neuankömmling, meldet aber niemanden ab und beendet keine laufende Arbeitsumgebung.',
    maxLogins: 'Maximale Zahl gleichzeitig angemeldeter Benutzer',
    unlimited: 'unbegrenzt',
    maxLoginsHint: 'Ein bereits angemeldeter Benutzer wird nie abgewiesen, daher betrifft eine Änderung dieses Werts nur neu ankommende Personen.',
    maxWorkspace: 'Maximale Zahl gleichzeitiger Benutzer mit Arbeitsumgebung',
    workspaceHintBefore: 'Abgewiesenen Benutzern wird empfohlen, lokal in VS Code zu arbeiten',
    workspaceHintLink: ', mit dem Download-Link',
    workspaceHintAfter: '. Unabhängig vom Platzkontingent einer Vorlage, das Lizenzplätze abbildet und für alle gilt.',
    idle: 'Anmeldeplatz wird freigegeben nach (Minuten Inaktivität)',
    idleHint: 'Wähle einen Wert über 15. Ein aktiver Client prüft seine Zugangsdaten höchstens alle 15 Minuten, ein kürzeres Zeitfenster würde also die Plätze von Personen freigeben, die noch arbeiten.',
    registration: 'Registrierung',
    registrationIntro: 'Wer bei der ersten Anmeldung (GitHub oder E-Mail) ein Konto anlegen darf. Bestehende Benutzer können sich immer anmelden. Die Obergrenze für Benutzer ist fest und zählt alle außer Mitarbeitende, Dienstkonten und archivierte Benutzer.',
    regMode: 'Registrierungsmodus',
    maxRegistered: 'Maximale registrierte Benutzer',
    maxRegisteredHint: 'Gilt in jedem Modus, auch für eine gültige Einladung.',
    referrals: 'Empfehlungseinladungen pro Benutzer',
    referralsHint: 'Einladungslinks zur einmaligen Verwendung, die jeder Benutzer weitergeben kann (Modus „Nur mit Einladung“). Die ersten Einladungen für die ersten Benutzer stammen von der Admin-Seite für Einladungen.',
    pilot: 'Pilotkurs-IDs',
    pilotPlaceholder: 'keine',
    pilotHint: 'Öffentliche Kurse, in die jeder neue Benutzer eingeschrieben wird, durch Kommas getrennt. Die Platzgrenze des jeweiligen Kurses gilt weiterhin.',
    saving: 'Wird gespeichert…',
    save: 'Limits speichern',
    discard: 'Änderungen verwerfen',
  },
  en: {
    modeOpen: 'Open — anyone who signs in gets an account',
    modeInviteOnly: 'Invite only — a valid invite link is required',
    modeClosed: 'Closed — no new accounts',
    modeBadgeOpen: 'open',
    modeBadgeInviteOnly: 'invite only',
    modeBadgeClosed: 'closed',
    mustBeWhole: (label: string) => `${label} must be a non-negative whole number.`,
    labelIdle: 'Login idle window',
    labelReferrals: 'Referral invites per user',
    labelMaxWorkspace: 'Max workspace users',
    labelMaxLogins: 'Max concurrent logins',
    labelMaxRegistered: 'Max registered users',
    idleMin: 'Login idle window must be at least 1 minute.',
    saved: 'Limits saved. They apply to the next sign-in or workspace launch.',
    saveFailed: 'Failed to save limits',
    denied: 'Access Denied',
    adminRequired: 'Admin privileges are required to access this page.',
    title: 'Instance limits',
    subtitle: 'How many people may be signed in, and how many may hold a workspace, at the same time.',
    inUse: 'In use right now',
    inUseIntro1: 'Both counts are per ',
    inUseUser: 'user',
    inUseIntro2: ', not per session or per workspace — someone signed in on two devices is one person, and someone with two workspaces holds one seat.',
    registeredUsers: 'Registered users',
    of: 'of',
    signedIn: 'Signed in',
    noLimit: 'no limit',
    limited: 'limited',
    holdingWorkspace: 'Holding a workspace',
    coderUnreachable: 'Coder unreachable',
    limits: 'Limits',
    limitsIntro: 'Leave a field empty for no limit. Administrators and the built-in manager roles are never refused by either limit. Lowering a limit below the current usage stops the next arrival — it never signs anyone out or stops a running workspace.',
    maxLogins: 'Max concurrent users signed in',
    unlimited: 'unlimited',
    maxLoginsHint: 'A user already signed in is never refused, so raising and lowering this only affects people arriving.',
    maxWorkspace: 'Max concurrent workspace users',
    workspaceHintBefore: 'Refused users are told to work locally in VS Code',
    workspaceHintLink: ', with the download link',
    workspaceHintAfter: '. Separate from a template\'s seat quota, which models licence seats and binds everyone.',
    idle: 'Sign-in seat is released after (minutes idle)',
    idleHint: 'Keep this above 15. An active client re-checks its credentials at most every 15 minutes, so a shorter window would release the seats of people who are still working.',
    registration: 'Registration',
    registrationIntro: 'Who may create an account on first sign-in (GitHub or email). Existing users always sign in. The user cap is hard and counts everyone except staff, service accounts and archived users.',
    regMode: 'Registration mode',
    maxRegistered: 'Max registered users',
    maxRegisteredHint: 'Applies in every mode, even to a valid invite.',
    referrals: 'Referral invites per user',
    referralsHint: 'Single-use invite links each user can share (invite-only mode). Seed invites for the first users come from the invite admin page.',
    pilot: 'Pilot course ids',
    pilotPlaceholder: 'none',
    pilotHint: 'Public courses every new user is enrolled in, comma separated. Each course\'s own seat cap still applies.',
    saving: 'Saving…',
    save: 'Save limits',
    discard: 'Discard changes',
  },
};
type Copy = (typeof COPY)[keyof typeof COPY];

/** '' → null, otherwise a non-negative integer (throws a user message). */
function parseLimit(label: string, raw: string, t: Copy): number | null {
  const text = raw.trim();
  if (!text) return null;
  const value = Number(text);
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(t.mustBeWhole(label));
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
  const language = useUiLanguage();
  const t = COPY[language];
  const num = (value: number) => formatNumber(value, language);
  const modeLabels: Record<RegistrationMode, string> = {
    open: t.modeOpen,
    invite_only: t.modeInviteOnly,
    closed: t.modeClosed,
  };
  const modeBadges: Record<RegistrationMode, string> = {
    open: t.modeBadgeOpen,
    invite_only: t.modeBadgeInviteOnly,
    closed: t.modeBadgeClosed,
  };
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
      const idle = parseLimit(t.labelIdle, form.idleMinutes, t);
      if (idle == null || idle < 1) {
        throw new Error(t.idleMin);
      }
      const referrals = parseLimit(t.labelReferrals, form.referralInvitesPerUser, t);
      await limitsClient.update({
        max_workspace_users: parseLimit(t.labelMaxWorkspace, form.maxWorkspaceUsers, t),
        max_concurrent_logins: parseLimit(t.labelMaxLogins, form.maxConcurrentLogins, t),
        login_idle_minutes: idle,
        registration_mode: form.registrationMode,
        max_registered_users: parseLimit(t.labelMaxRegistered, form.maxRegisteredUsers, t),
        referral_invites_per_user: referrals ?? 0,
        pilot_course_ids: form.pilotCourseIds
          .split(/[\s,]+/)
          .map((id) => id.trim())
          .filter(Boolean),
      });
      notify(t.saved, 'success');
      setDraft(null);
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.saveFailed, 'error');
    } finally {
      setSaving(false);
    }
  }

  if (!authLoading && !isAdmin) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-danger-wash border border-danger-line rounded-lg p-6 text-center">
            <h2 className="text-lg font-semibold text-danger-text">{t.denied}</h2>
            <p className="text-sm text-danger-text mt-2">
              {t.adminRequired}
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
          breadcrumbs={[{ label: t.title }]}
          title={t.title}
          subtitle={t.subtitle}
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
                  <h2 className="text-lg font-semibold text-fg">{t.inUse}</h2>
                  <p className="text-sm text-muted mt-1">
                    {t.inUseIntro1}<span className="font-medium">{t.inUseUser}</span>{t.inUseIntro2}
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="bg-sunken rounded p-4">
                    <div className="text-xs font-medium text-muted">{t.registeredUsers}</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-fg">
                        {num(usage?.registered_users ?? 0)}
                      </span>
                      <span className="text-sm text-muted">
                        {t.of} {data.max_registered_users != null ? num(data.max_registered_users) : '∞'}
                      </span>
                      <Badge
                        tone={usageTone(usage?.registered_users ?? 0, data.max_registered_users)}
                        pill
                      >
                        {modeBadges[data.registration_mode ?? 'open'] ?? data.registration_mode}
                      </Badge>
                    </div>
                  </div>

                  <div className="bg-sunken rounded p-4">
                    <div className="text-xs font-medium text-muted">{t.signedIn}</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-fg">{num(usage?.login_seats ?? 0)}</span>
                      <span className="text-sm text-muted">
                        {t.of} {data.max_concurrent_logins != null ? num(data.max_concurrent_logins) : '∞'}
                      </span>
                      <Badge tone={usageTone(usage?.login_seats ?? 0, data.max_concurrent_logins)} pill>
                        {data.max_concurrent_logins == null ? t.noLimit : t.limited}
                      </Badge>
                    </div>
                  </div>

                  <div className="bg-sunken rounded p-4">
                    <div className="text-xs font-medium text-muted">{t.holdingWorkspace}</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-3xl font-bold text-fg">
                        {workspaceCountKnown ? num(usage?.workspace_users ?? 0) : '—'}
                      </span>
                      <span className="text-sm text-muted">
                        {t.of} {data.max_workspace_users != null ? num(data.max_workspace_users) : '∞'}
                      </span>
                      {workspaceCountKnown ? (
                        <Badge
                          tone={usageTone(usage?.workspace_users ?? 0, data.max_workspace_users)}
                          pill
                        >
                          {data.max_workspace_users == null ? t.noLimit : t.limited}
                        </Badge>
                      ) : (
                        <Badge tone="warning" pill>
                          {t.coderUnreachable}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-fg">{t.limits}</h2>
                  <p className="text-sm text-muted mt-1">
                    {t.limitsIntro}
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="limit-logins"
                      className="block text-xs font-medium text-body mb-1"
                    >
                      {t.maxLogins}
                    </label>
                    <input
                      id="limit-logins"
                      value={form.maxConcurrentLogins}
                      onChange={(event) => update({ maxConcurrentLogins: event.target.value })}
                      placeholder={t.unlimited}
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      {t.maxLoginsHint}
                    </p>
                  </div>

                  <div>
                    <label
                      htmlFor="limit-workspaces"
                      className="block text-xs font-medium text-body mb-1"
                    >
                      {t.maxWorkspace}
                    </label>
                    <input
                      id="limit-workspaces"
                      value={form.maxWorkspaceUsers}
                      onChange={(event) => update({ maxWorkspaceUsers: event.target.value })}
                      placeholder={t.unlimited}
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      {t.workspaceHintBefore}
                      {data.local_install_url ? t.workspaceHintLink : ''}
                      {t.workspaceHintAfter}
                    </p>
                  </div>

                  <div>
                    <label htmlFor="limit-idle" className="block text-xs font-medium text-body mb-1">
                      {t.idle}
                    </label>
                    <input
                      id="limit-idle"
                      value={form.idleMinutes}
                      onChange={(event) => update({ idleMinutes: event.target.value })}
                      placeholder="30"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      {t.idleHint}
                    </p>
                  </div>
                </div>

                <div className="border-t border-rule pt-4">
                  <h3 className="text-sm font-semibold text-fg">{t.registration}</h3>
                  <p className="text-sm text-muted mt-1">
                    {t.registrationIntro}
                  </p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="reg-mode" className="block text-xs font-medium text-body mb-1">
                      {t.regMode}
                    </label>
                    <select
                      id="reg-mode"
                      value={form.registrationMode}
                      onChange={(event) =>
                        update({ registrationMode: event.target.value as RegistrationMode })
                      }
                      className={inputCls}
                    >
                      {REGISTRATION_MODE_VALUES.map((mode) => (
                        <option key={mode} value={mode}>
                          {modeLabels[mode]}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="reg-cap" className="block text-xs font-medium text-body mb-1">
                      {t.maxRegistered}
                    </label>
                    <input
                      id="reg-cap"
                      value={form.maxRegisteredUsers}
                      onChange={(event) => update({ maxRegisteredUsers: event.target.value })}
                      placeholder={t.unlimited}
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      {t.maxRegisteredHint}
                    </p>
                  </div>

                  <div>
                    <label
                      htmlFor="reg-referrals"
                      className="block text-xs font-medium text-body mb-1"
                    >
                      {t.referrals}
                    </label>
                    <input
                      id="reg-referrals"
                      value={form.referralInvitesPerUser}
                      onChange={(event) => update({ referralInvitesPerUser: event.target.value })}
                      placeholder="2"
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      {t.referralsHint}
                    </p>
                  </div>

                  <div>
                    <label htmlFor="reg-courses" className="block text-xs font-medium text-body mb-1">
                      {t.pilot}
                    </label>
                    <input
                      id="reg-courses"
                      value={form.pilotCourseIds}
                      onChange={(event) => update({ pilotCourseIds: event.target.value })}
                      placeholder={t.pilotPlaceholder}
                      className={inputCls}
                    />
                    <p className="text-xs text-muted mt-1">
                      {t.pilotHint}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-1">
                  <Button onClick={save} disabled={saving || draft === null}>
                    {saving ? t.saving : t.save}
                  </Button>
                  {draft !== null && (
                    <Button variant="secondary" onClick={() => setDraft(null)} disabled={saving}>
                      {t.discard}
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
