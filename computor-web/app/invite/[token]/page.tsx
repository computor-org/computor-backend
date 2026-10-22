'use client';

import Image from 'next/image';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { InvitesClient } from '@/src/generated/clients/InvitesClient';
import type { InviteLinkPublic } from 'types/generated';
import { OnboardingClient } from '@/src/clients/OnboardingClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const invitesClient = new InvitesClient();
const onboarding = new OnboardingClient();

const COPY = {
  de: {
    invalidLink: 'Ungültiger oder abgelaufener Einladungslink',
    mismatch: 'Die Passwörter stimmen nicht überein',
    tooShort: 'Das Passwort muss mindestens 8 Zeichen lang sein',
    failed: 'Die Registrierung ist fehlgeschlagen',
    loading: 'Einladung wird geladen …',
    notFound: 'Einladung nicht gefunden',
    notFoundBody: 'Dieser Einladungslink ist ungültig oder abgelaufen.',
    ready: 'Konto bereit',
    signInWith: 'Melde dich mit',
    andPassword: 'und dem Passwort an, das du gerade gewählt hast. Falls du deine E-Mail-Adresse bestätigen musst, verwende zuerst den Link, den wir dorthin schicken.',
    continue: 'Weiter zur Anmeldung',
    create: 'Dein Konto erstellen',
    createButton: 'Konto erstellen',
    invited: 'Du wurdest zu Computor eingeladen.',
    expires: 'Gültig bis:',
    forEmail: 'Diese Einladung gilt für',
    enterFull: 'Gib genau diese Adresse ein.',
    firstName: 'Vorname *',
    lastName: 'Nachname *',
    email: 'E-Mail *',
    password: 'Passwort *',
    confirm: 'Passwort bestätigen *',
    creating: 'Konto wird erstellt …',
    dateLocale: 'de-AT' as string | undefined,
  },
  en: {
    invalidLink: 'Invalid or expired invite link',
    mismatch: 'Passwords do not match',
    tooShort: 'Password must be at least 8 characters',
    failed: 'Registration failed',
    loading: 'Loading invite…',
    notFound: 'Invite Not Found',
    notFoundBody: 'This invite link is invalid or has expired.',
    ready: 'Account ready',
    signInWith: 'Sign in with',
    andPassword: 'and the password you just chose. If you are asked to verify your email address, use the link we send there first.',
    continue: 'Continue to sign in',
    create: 'Create your account',
    createButton: 'Create account',
    invited: "You've been invited to join Computor.",
    expires: 'Expires:',
    forEmail: 'This invite is for',
    enterFull: 'enter that full address.',
    firstName: 'First name *',
    lastName: 'Last name *',
    email: 'Email *',
    password: 'Password *',
    confirm: 'Confirm password *',
    creating: 'Creating account…',
    dateLocale: undefined as string | undefined,
  },
};

export default function InvitePage() {
  const { token } = useParams<{ token: string }>();
  const { loginWithSSO } = useAuth();
  const t = COPY[useUiLanguage()];

  const [invite, setInvite] = useState<InviteLinkPublic | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [form, setForm] = useState({
    givenName: '',
    familyName: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) return;
    invitesClient.getInvitePublicInvitesTokenGet({ token })
      .then(data => setInvite(data))
      .catch(e => setLoadError(e instanceof Error ? e.message : ''))
      .finally(() => setLoading(false));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (form.password !== form.confirmPassword) {
      setSubmitError(t.mismatch);
      return;
    }
    if (form.password.length < 8) {
      setSubmitError(t.tooShort);
      return;
    }

    setSubmitting(true);
    try {
      await onboarding.acceptInvite(token, {
        given_name: form.givenName,
        family_name: form.familyName,
        email: form.email,
        password: form.password,
      });
      // The account now exists in Keycloak, but no session is established here.
      // The user signs in via Keycloak SSO with the password they just set.
      setDone(true);
    } catch (e) {
      setSubmitError(extractError(e, t.failed));
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(t.dateLocale, { year: 'numeric', month: 'long', day: 'numeric' });

  if (loading) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center">
        <div className="text-muted">{t.loading}</div>
      </div>
    );
  }

  if (loadError || !invite) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
        <div className="bg-surface rounded-xl shadow-sm border border-rule w-full max-w-md p-8 text-center">
          <div className="text-4xl mb-4">🔗</div>
          <h1 className="text-xl font-semibold text-fg mb-2">{t.notFound}</h1>
          <p className="text-sm text-muted">{loadError === null ? t.notFoundBody : loadError || t.invalidLink}</p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
        <div className="bg-surface rounded-xl shadow-sm border border-rule w-full max-w-md p-8 text-center">
          <div className="text-4xl mb-4">✅</div>
          <h1 className="text-xl font-semibold text-fg mb-2">{t.ready}</h1>
          <p className="text-sm text-muted mb-6">
            {t.signInWith} <strong>{form.email}</strong> {t.andPassword}
          </p>
          <button
            onClick={() => loginWithSSO('keycloak')}
            className="w-full py-2.5 px-4 bg-accent text-on-accent text-sm font-medium rounded-lg hover:bg-accent-hover transition-colors"
          >
            {t.continue}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <div className="bg-surface rounded-xl shadow-sm border border-rule w-full max-w-md">
        {/* Header */}
        <div className="p-8 pb-0">
          <div className="flex items-center gap-3 mb-6">
            <Image src="/computor_logo.png" alt="Computor" width={32} height={32} className="h-8 w-8" />
            <span className="text-lg font-semibold text-fg">Computor</span>
          </div>
          <h1 className="text-2xl font-bold text-fg mb-1">{t.create}</h1>
          <p className="text-sm text-muted mb-2">{t.invited}</p>

          {/* Invite metadata */}
          <div className="bg-accent-wash border border-accent-line rounded-lg p-3 mb-6 text-xs text-accent-text space-y-1">
            <div>{t.expires} <strong>{formatDate(invite.expires_at)}</strong></div>
            {invite.email && (
              <div>
                {t.forEmail} <strong>{invite.email}</strong> — {t.enterFull}
              </div>
            )}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-8 pt-0 space-y-4">
          {submitError && (
            <div className="p-3 bg-danger-wash border border-danger-line rounded-lg text-sm text-danger-text">{submitError}</div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-body mb-1">{t.firstName}</label>
              <input
                type="text"
                required
                value={form.givenName}
                onChange={e => setForm(f => ({ ...f, givenName: e.target.value }))}
                className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-body mb-1">{t.lastName}</label>
              <input
                type="text"
                required
                value={form.familyName}
                onChange={e => setForm(f => ({ ...f, familyName: e.target.value }))}
                className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-body mb-1">{t.email}</label>
            <input
              type="email"
              required
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-body mb-1">{t.password}</label>
            <input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-body mb-1">{t.confirm}</label>
            <input
              type="password"
              required
              value={form.confirmPassword}
              onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))}
              className="w-full px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 bg-accent text-on-accent text-sm font-medium rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-50 mt-2"
          >
            {submitting ? t.creating : t.createButton}
          </button>
        </form>
      </div>
    </div>
  );
}

/** FastAPI returns errors as `{ "detail": ... }`; the API client throws that text as Error.message. */
function extractError(e: unknown, fallback: string): string {
  if (e instanceof Error && e.message) {
    try {
      const parsed = JSON.parse(e.message);
      if (parsed?.detail) return typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
    } catch {
      return e.message;
    }
    return e.message;
  }
  return fallback;
}
