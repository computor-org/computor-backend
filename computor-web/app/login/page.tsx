'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { safeInternalPath } from '@/src/utils/safeRedirect';

/**
 * Optional `?next=/path` target (e.g. the landing page's catalog CTA), reduced
 * to a canonical same-origin path by safeInternalPath. /auth/success validates
 * the stored value again. Read from window.location instead of useSearchParams
 * so the page needs no Suspense boundary.
 */
function nextPath(): string | undefined {
  const next = new URLSearchParams(window.location.search).get('next');
  return safeInternalPath(next, window.location.origin) ?? undefined;
}

export default function LoginPage() {
  const router = useRouter();
  const { loginWithSSO, isAuthenticated, isLoading } = useAuth();
  const triggered = useRef(false);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.push(nextPath() ?? '/dashboard');
      return;
    }
    // Keycloak is the only identity provider — go straight there instead of
    // showing an intermediate button. Guard against double-trigger in StrictMode.
    if (!triggered.current) {
      triggered.current = true;
      loginWithSSO('keycloak', nextPath());
    }
  }, [isAuthenticated, isLoading, loginWithSSO, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto" />
        <p className="mt-4 text-muted">Redirecting to sign-in…</p>
        <button
          onClick={() => loginWithSSO('keycloak', nextPath())}
          className="mt-4 text-sm text-accent-text hover:underline"
        >
          Click here if you are not redirected automatically
        </button>
      </div>
    </div>
  );
}
