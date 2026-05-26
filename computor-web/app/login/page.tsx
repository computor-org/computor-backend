'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';

export default function LoginPage() {
  const router = useRouter();
  const { loginWithSSO, isAuthenticated, isLoading } = useAuth();
  const triggered = useRef(false);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.push('/dashboard');
      return;
    }
    // Keycloak is the only identity provider — go straight there instead of
    // showing an intermediate button. Guard against double-trigger in StrictMode.
    if (!triggered.current) {
      triggered.current = true;
      loginWithSSO('keycloak');
    }
  }, [isAuthenticated, isLoading, loginWithSSO, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
        <p className="mt-4 text-gray-600">Redirecting to sign-in…</p>
        <button
          onClick={() => loginWithSSO('keycloak')}
          className="mt-4 text-sm text-blue-600 hover:underline"
        >
          Click here if you are not redirected automatically
        </button>
        <p className="mt-6 text-sm text-gray-500">
          First time here?{' '}
          <a href="/register/gitlab" className="text-blue-600 hover:underline">
            Set up your login
          </a>
        </p>
      </div>
    </div>
  );
}
