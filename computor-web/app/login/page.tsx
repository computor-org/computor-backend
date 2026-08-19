'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import Link from 'next/link';
import Image from 'next/image';
import SocialLoginButtons from '@/src/components/auth/SocialLoginButtons';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, loginWithSSO } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.push('/dashboard');
      return;
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-12">
      <div className="mx-auto max-w-md">
        <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-xl">
          <div className="mb-8 text-center">
            <Image src="/computor_logo.png" alt="Computor" width={48} height={48} className="mx-auto h-12 w-12" />
            <h1 className="mt-4 text-2xl font-bold text-gray-900">Sign in to Computor</h1>
            <p className="mt-2 text-sm text-gray-600">Use your institution or social account.</p>
          </div>

          <SocialLoginButtons />

          <div className="my-6 flex items-center gap-3 text-xs text-gray-400">
            <div className="h-px flex-1 bg-gray-200" />
            <span>or</span>
            <div className="h-px flex-1 bg-gray-200" />
          </div>

          <button
            type="button"
            onClick={() => loginWithSSO('keycloak')}
            className="w-full rounded-lg bg-gray-900 px-4 py-3 text-sm font-medium text-white transition hover:bg-gray-800"
          >
            Continue with Computor SSO
          </button>

          <p className="mt-6 text-center text-sm text-gray-600">
            New here?{' '}
            <Link href="/register" className="font-medium text-blue-600 hover:underline">Create a student account</Link>
          </p>
        </div>
        <Link href="/" className="mt-6 block text-center text-sm text-gray-600 hover:text-gray-900">← Back to home</Link>
      </div>
    </div>
  );
}
