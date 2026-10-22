'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useSyncExternalStore } from 'react';
import { WAITLIST_URL } from '@/src/utils/registration';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const MESSAGES_EN: Record<string, { title: string; body: string }> = {
  full: {
    title: 'The pilot is full',
    body: 'All pilot places are taken, so no new account was created. Your invite link was not used up.',
  },
  closed: {
    title: 'Registration is closed',
    body: 'New accounts cannot be created right now.',
  },
  invite_required: {
    title: 'An invite is needed',
    body: 'Computor is invite-only during the pilot. Open the invite link a friend shared with you and sign in from there.',
  },
  invite_invalid: {
    title: 'Invite link invalid',
    body: 'That invite link is invalid, already used, or expired, so no account was created. Ask your friend for another one.',
  },
  email_unverified: {
    title: 'Please verify your email first',
    body: 'Click the link in the verification email we sent you, then open your invite link again to finish creating your account.',
  },
};

const MESSAGES_DE: Record<string, { title: string; body: string }> = {
  full: {
    title: 'Die Pilotphase ist voll',
    body: 'Alle Plätze der Pilotphase sind vergeben, deshalb wurde kein neues Konto angelegt. Dein Einladungslink wurde nicht verbraucht.',
  },
  closed: {
    title: 'Die Registrierung ist geschlossen',
    body: 'Im Moment können keine neuen Konten angelegt werden.',
  },
  invite_required: {
    title: 'Eine Einladung ist nötig',
    body: 'Computor ist während der Pilotphase nur mit Einladung zugänglich. Öffne den Einladungslink, den dir jemand geschickt hat, und melde dich dort an.',
  },
  invite_invalid: {
    title: 'Einladungslink ungültig',
    body: 'Dieser Einladungslink ist ungültig, bereits verwendet oder abgelaufen, deshalb wurde kein Konto angelegt. Bitte die Person, die dich eingeladen hat, um einen neuen Link.',
  },
  email_unverified: {
    title: 'Bestätige zuerst deine E-Mail-Adresse',
    body: 'Klicke auf den Link in der Bestätigungs-E-Mail, die wir dir geschickt haben. Öffne danach deinen Einladungslink erneut, um dein Konto fertig anzulegen.',
  },
};

const COPY = {
  de: {
    messages: MESSAGES_DE,
    waitlist: 'Du möchtest zugelassen werden, sobald wieder Plätze frei sind? Setz dich auf die Warteliste, indem du eine Nachricht hinterlässt unter',
    haveAccount: 'Du hast schon ein Konto?',
    signIn: 'Anmelden',
  },
  en: {
    messages: MESSAGES_EN,
    waitlist: 'Want to be let in when places open up? Join the waitlist by leaving a note at',
    haveAccount: 'Already have an account?',
    signIn: 'Sign in',
  },
};

const noSubscribe = () => () => {};

/**
 * Where the backend sends a first sign-in that may not create an account.
 * The reason arrives as ``reason`` (direct redirect) or ``state`` (after the
 * Keycloak logout round-trip). No account was created and the Keycloak
 * session has been ended.
 */
export default function JoinRefusedPage() {
  const t = COPY[useUiLanguage()];
  // The query string, read on the client only (null while pre-rendering).
  const search = useSyncExternalStore(
    noSubscribe,
    () => window.location.search,
    () => null,
  );
  const params = search == null ? null : new URLSearchParams(search);
  const reason = params ? (params.get('reason') ?? params.get('state') ?? 'invite_invalid') : null;

  const message = (reason && t.messages[reason]) || t.messages.invite_invalid;
  const waitlist = reason !== 'email_unverified';

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <div className="bg-surface rounded-xl shadow-sm border border-rule w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-6">
          <Image src="/computor_logo.png" alt="Computor" width={32} height={32} className="h-8 w-8" />
          <span className="text-lg font-semibold text-fg">Computor</span>
        </div>
        {reason && (
          <>
            <h1 className="text-xl font-semibold text-fg mb-2">{message.title}</h1>
            <p className="text-sm text-muted mb-4">{message.body}</p>
            {waitlist && (
              <p className="text-sm text-muted">
                {t.waitlist}{' '}
                <a href={WAITLIST_URL} className="text-accent-text underline">
                  github.com/computor-org/feedback
                </a>
                .
              </p>
            )}
            <p className="text-sm text-muted mt-4">
              {t.haveAccount}{' '}
              <Link href="/login" className="text-accent-text underline">
                {t.signIn}
              </Link>
              .
            </p>
          </>
        )}
      </div>
    </div>
  );
}
