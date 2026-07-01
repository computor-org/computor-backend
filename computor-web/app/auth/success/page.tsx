'use client';

import { useEffect, useState } from 'react';
import { ssoAuthService } from '@/src/services/authInstances';

export default function AuthSuccessPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        // Backend has already set ct_access_token / ct_refresh_token cookies on
        // the redirect response. Fetch /user (with credentials) to populate the
        // user record, then full-reload so AuthContext re-initializes.
        const result = await ssoAuthService.handleSSOCallback();
        if (!result.success) {
          throw new Error(result.error || 'Sign-in failed');
        }
        let redirect = sessionStorage.getItem('auth_redirect') || '/dashboard';
        sessionStorage.removeItem('auth_redirect');
        // Only accept same-origin absolute paths: anything not starting with a
        // single "/" (e.g. a protocol-relative "//host" planted in storage)
        // would send the user off-site.
        if (!redirect.startsWith('/') || redirect.startsWith('//')) {
          redirect = '/dashboard';
        }
        // Don't bounce back to single-use or pre-auth pages: an invite link is
        // consumed during this very sign-in (re-loading it 400s with "already
        // used"), and login/register/auth pages are meaningless once logged in.
        // Land on the dashboard instead. Genuine deep links (e.g. /courses/123)
        // are preserved.
        if (/^\/(invite|login|register|auth)(\/|$)/.test(redirect)) {
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
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        {error ? (
          <>
            <p className="text-red-600 font-medium mb-3">{error}</p>
            <a href="/login" className="px-4 py-2 bg-gray-900 text-white rounded hover:bg-gray-800 inline-block">
              Back to login
            </a>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
            <p className="mt-4 text-gray-600">Completing sign-in…</p>
          </>
        )}
      </div>
    </div>
  );
}
