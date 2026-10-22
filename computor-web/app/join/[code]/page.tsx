'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { InvitesClient } from '@/src/generated/clients/InvitesClient';
import type { InviteStatusPublic } from 'types/generated';
import { ssoAuthService } from '@/src/services/authInstances';
import { WAITLIST_ADDRESS, WAITLIST_URL } from '@/src/utils/registration';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const invitesClient = new InvitesClient();

const COPY = {
  de: {
    checkFailed: 'Dieser Einladungslink konnte nicht geprüft werden.',
    closed: 'Die Registrierung ist im Moment geschlossen.',
    full: 'Die Pilotphase ist voll. Im Moment können keine neuen Konten angelegt werden.',
    used: 'Dieser Einladungslink wurde bereits verwendet.',
    expired: 'Dieser Einladungslink ist abgelaufen.',
    invalid: 'Dieser Einladungslink ist ungültig.',
    checking: 'Einladung wird geprüft …',
    invited: 'Du bist eingeladen',
    intro: 'Erstelle dein Computor-Konto mit GitHub oder mit deiner E-Mail-Adresse. Dieser Einladungslink funktioniert nur einmal.',
    github: 'Mit GitHub anmelden',
    email: 'Mit E-Mail registrieren',
    emailNote: 'Bei der Registrierung mit E-Mail musst du deine Adresse bestätigen, bevor das Konto angelegt wird.',
    unusable: 'Diese Einladung kann nicht verwendet werden',
    waitlist: 'Du möchtest dabei sein? Setz dich auf die Warteliste, indem du eine Mail schreibst an',
    haveAccount: 'Du hast schon ein Konto?',
    signIn: 'Anmelden',
  },
  en: {
    checkFailed: 'Could not check this invite link.',
    closed: 'Registration is closed right now.',
    full: 'The pilot is full — no new accounts can be created right now.',
    used: 'This invite link has already been used.',
    expired: 'This invite link has expired.',
    invalid: 'This invite link is not valid.',
    checking: 'Checking your invite…',
    invited: "You're invited",
    intro: 'Create your Computor account with GitHub or with your email address. This invite link works once.',
    github: 'Sign in with GitHub',
    email: 'Register with email',
    emailNote: 'With email you will be asked to confirm your address before the account is created.',
    unusable: "This invite can't be used",
    waitlist: 'Want in? Join the waitlist by writing to',
    haveAccount: 'Already have an account?',
    signIn: 'Sign in',
  },
};

/**
 * Where an invite link lands (/join/<code>).
 *
 * Checks the code (the public status endpoint says only valid/used/expired,
 * never who issued it) and then starts the Keycloak login with the code in
 * the server-side login state, where the first-login callback checks and
 * spends it. GitHub goes straight to the GitHub broker; email opens
 * Keycloak's registration form. Existing users can sign in from here too —
 * the code is simply ignored for them.
 */
export default function JoinPage() {
  const { code } = useParams<{ code: string }>();
  const t = COPY[useUiLanguage()];
  const [status, setStatus] = useState<InviteStatusPublic | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    invitesClient
      .getInviteStatusInvitesTokenStatusGet({ token: code })
      .then(setStatus)
      .catch((e) =>
        setLoadError(e instanceof Error ? e.message : ''),
      );
  }, [code]);

  function start(kind: 'github' | 'email') {
    ssoAuthService.initiateSSO(
      'keycloak',
      undefined,
      kind === 'github' ? { invite: code, idp_hint: 'github' } : { invite: code, action: 'register' },
    );
  }

  const usable =
    status?.status === 'valid' && status.registration_mode !== 'closed' && !status.full;

  let problem: string | null = loadError === null ? null : loadError || t.checkFailed;
  if (!problem && status && !usable) {
    if (status.registration_mode === 'closed') problem = t.closed;
    else if (status.full) problem = t.full;
    else if (status.status === 'used') problem = t.used;
    else if (status.status === 'expired') problem = t.expired;
    else problem = t.invalid;
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <div className="bg-surface rounded-xl shadow-sm border border-rule w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-6">
          <Image src="/computor_logo.png" alt="Computor" width={32} height={32} className="h-8 w-8" />
          <span className="text-lg font-semibold text-fg">Computor</span>
        </div>

        {!status && loadError === null && <div className="text-muted text-sm">{t.checking}</div>}

        {usable && (
          <>
            <h1 className="text-2xl font-bold text-fg mb-1">{t.invited}</h1>
            <p className="text-sm text-muted mb-6">
              {t.intro}
            </p>
            <div className="space-y-3">
              <button
                onClick={() => start('github')}
                className="w-full py-2.5 px-4 bg-accent text-on-accent text-sm font-medium rounded-lg hover:bg-accent-hover transition-colors"
              >
                {t.github}
              </button>
              <button
                onClick={() => start('email')}
                className="w-full py-2.5 px-4 border border-rule text-body text-sm font-medium rounded-lg hover:bg-sunken transition-colors"
              >
                {t.email}
              </button>
            </div>
            <p className="text-xs text-muted mt-4">
              {t.emailNote}
            </p>
          </>
        )}

        {problem && (
          <>
            <h1 className="text-xl font-semibold text-fg mb-2">{t.unusable}</h1>
            <p className="text-sm text-muted mb-4">{problem}</p>
            <p className="text-sm text-muted">
              {t.waitlist}{' '}
              <a href={WAITLIST_URL} className="text-accent-text underline">
                {WAITLIST_ADDRESS}
              </a>
              . {t.haveAccount}{' '}
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
