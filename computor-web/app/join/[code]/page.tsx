'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { InvitesClient } from '@/src/generated/clients/InvitesClient';
import type { InviteStatusPublic } from 'types/generated';
import { ssoAuthService } from '@/src/services/authInstances';
import { WAITLIST_URL } from '@/src/utils/registration';

const invitesClient = new InvitesClient();

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
  const [status, setStatus] = useState<InviteStatusPublic | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    invitesClient
      .getInviteStatusInvitesTokenStatusGet({ token: code })
      .then(setStatus)
      .catch((e) =>
        setLoadError(e instanceof Error ? e.message : 'Could not check this invite link.'),
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

  let problem: string | null = loadError;
  if (!problem && status && !usable) {
    if (status.registration_mode === 'closed') problem = 'Registration is closed right now.';
    else if (status.full) problem = 'The pilot is full — no new accounts can be created right now.';
    else if (status.status === 'used') problem = 'This invite link has already been used.';
    else if (status.status === 'expired') problem = 'This invite link has expired.';
    else problem = 'This invite link is not valid.';
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
      <div className="bg-surface rounded-xl shadow-sm border border-rule w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-6">
          <Image src="/computor_logo.png" alt="Computor" width={32} height={32} className="h-8 w-8" />
          <span className="text-lg font-semibold text-fg">Computor</span>
        </div>

        {!status && !loadError && <div className="text-muted text-sm">Checking your invite…</div>}

        {usable && (
          <>
            <h1 className="text-2xl font-bold text-fg mb-1">You&apos;re invited</h1>
            <p className="text-sm text-muted mb-6">
              Create your Computor account with GitHub or with your email address. This invite
              link works once.
            </p>
            <div className="space-y-3">
              <button
                onClick={() => start('github')}
                className="w-full py-2.5 px-4 bg-accent text-on-accent text-sm font-medium rounded-lg hover:bg-accent-hover transition-colors"
              >
                Sign in with GitHub
              </button>
              <button
                onClick={() => start('email')}
                className="w-full py-2.5 px-4 border border-rule text-body text-sm font-medium rounded-lg hover:bg-sunken transition-colors"
              >
                Register with email
              </button>
            </div>
            <p className="text-xs text-muted mt-4">
              With email you will be asked to confirm your address before the account is
              created.
            </p>
          </>
        )}

        {problem && (
          <>
            <h1 className="text-xl font-semibold text-fg mb-2">This invite can&apos;t be used</h1>
            <p className="text-sm text-muted mb-4">{problem}</p>
            <p className="text-sm text-muted">
              Want in? Join the waitlist by leaving a note at{' '}
              <a href={WAITLIST_URL} className="text-accent-text underline">
                github.com/computor-org/feedback
              </a>
              . Already have an account?{' '}
              <Link href="/login" className="text-accent-text underline">
                Sign in
              </Link>
              .
            </p>
          </>
        )}
      </div>
    </div>
  );
}
