'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import SocialLoginButtons from '@/src/components/auth/SocialLoginButtons';

export default function RegisterPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && isAuthenticated) router.push('/dashboard');
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-gray-50 text-gray-600">Loading…</div>;
  }

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-12">
      <div className="mx-auto max-w-md">
        <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-xl">
          <div className="mb-8 text-center">
            <Image src="/computor_logo.png" alt="Computor" width={48} height={48} className="mx-auto h-12 w-12" />
            <h1 className="mt-4 text-2xl font-bold text-gray-900">Create your student account</h1>
            <p className="mt-2 text-sm text-gray-600">Choose an account provider to get started.</p>
          </div>

          <SocialLoginButtons registration />

          <p className="mt-6 rounded-lg bg-blue-50 p-3 text-center text-xs leading-5 text-blue-900">
            Self-registration creates only a student account. You can join courses that have been marked public; it does not grant teaching or administrator access.
          </p>

          <p className="mt-6 text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link href="/login" className="font-medium text-blue-600 hover:underline">Sign in</Link>
          </p>
        </div>
        <Link href="/" className="mt-6 block text-center text-sm text-gray-600 hover:text-gray-900">← Back to home</Link>
      </div>
    </main>
  );
}
