'use client';

import { useEffect, useRef, useState } from 'react';
import { ssoAuthService } from '@/src/services/authInstances';
import { safeInternalPath } from '@/src/utils/safeRedirect';

export default function AuthSuccessPage() {
  const [error, setError] = useState<string | null>(null);
  const [refused, setRefused] = useState(false);
  // One-shot: auth_redirect is consumed on read, so a second run of this effect
  // (React StrictMode in dev) would find it gone and override the first run's
  // redirect with /dashboard.
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;
    (async () => {
      // The backend bounces a refused sign-in back here rather than to /login,
      // which would redirect straight to Keycloak again and loop forever. It
      // carries the reason written for the user — an instance at its
      // concurrent-user cap, a banned account — so render it verbatim and
      // stop: there are no cookies to complete a session with.
      const params = new URLSearchParams(window.location.search);
      const description = params.get('error_description');
      if (params.get('error') && description) {
        setRefused(true);
        setError(description);
        return;
      }
      try {
        // Backend has already set ct_access_token / ct_refresh_token cookies on
        // the redirect response. Fetch /user (with credentials) to populate the
        // user record, then full-reload so AuthContext re-initializes.
        const result = await ssoAuthService.handleSSOCallback();
        if (!result.success) {
          throw new Error(result.error || 'Sign-in failed');
        }
        const stored = sessionStorage.getItem('auth_redirect');
        sessionStorage.removeItem('auth_redirect');
        // Only a canonical same-origin path: prefix checks alone let
        // "/\t/host" (tab stripped by the browser) through as "//host".
        let redirect = safeInternalPath(stored, window.location.origin) ?? '/dashboard';
        // Don't bounce back to single-use or pre-auth pages: an invite link is
        // consumed during this very sign-in (re-loading it 400s with "already
        // used"), and login/register/auth pages are meaningless once logged in.
        // Land on the dashboard instead. Genuine deep links (e.g. /courses/123)
        // are preserved.
        if (/^\/(invite|join|login|register|auth)(\/|$)/.test(redirect)) {
          redirect = '/dashboard';
        }
        window.location.replace(redirect);
      } catch (err) {
        console.error('SSO success handler failed:', err);
        setError(err instanceof Error ? err.message : 'Failed to complete sign-in.');
      }
    })();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas">
      <div className="text-center">
        {error ? (
          <>
            {/* A refusal is a paragraph, not a label: it names the limit, the
                current number and what to do instead (install VS Code
                locally). Give it room and left-align it so a URL in the text
                stays readable. */}
            <p
              className={
                refused
                  ? 'text-danger-text font-medium mb-3 max-w-lg text-left whitespace-pre-line break-words'
                  : 'text-danger-text font-medium mb-3'
              }
            >
              {error}
            </p>
            <a href="/login" className="px-4 py-2 bg-inverse text-on-accent rounded hover:bg-inverse-hover inline-block">
              {refused ? 'Try again' : 'Back to login'}
            </a>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto" />
            <p className="mt-4 text-muted">Completing sign-in…</p>
          </>
        )}
      </div>
    </div>
  );
}
