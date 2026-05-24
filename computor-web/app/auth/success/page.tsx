'use client';

import { useEffect, useState } from 'react';
import { SSOAuthService } from '@/src/services/ssoAuthService';

export default function AuthSuccessPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        // Backend has already set ct_access_token / ct_refresh_token cookies on
        // the redirect response. Fetch /user (with credentials) to populate the
        // user record, then full-reload so AuthContext re-initializes.
        const sso = new SSOAuthService();
        const result = await sso.handleSSOCallback();
        if (!result.success) {
          throw new Error(result.error || 'Sign-in failed');
        }
        const redirect = sessionStorage.getItem('auth_redirect') || '/dashboard';
        sessionStorage.removeItem('auth_redirect');
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
