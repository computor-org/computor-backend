'use client';

import Image from 'next/image';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';

export default function PublicLearnShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, logout } = useAuth();

  async function signOut() {
    await logout();
    router.push('/');
  }

  return (
    <div className="min-h-screen bg-canvas text-fg flex flex-col">
      <header className="border-b border-rule bg-surface/95 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3 min-w-0">
            <Image src="/computor_logo.png" alt="" width={36} height={36} className="h-9 w-9 shrink-0" />
            <span className="font-bold text-xl truncate">Computor Learn</span>
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <Link href="/learn" className="text-accent-text hover:underline">Courses</Link>
            {user ? (
              <>
                <Link href="/dashboard" className="text-accent-text hover:underline">Dashboard</Link>
                <button type="button" onClick={signOut} className="text-muted hover:text-fg">
                  Sign out
                </button>
              </>
            ) : (
              <Link href="/login?next=%2Fcourses%2Fcatalog" className="text-accent-text hover:underline">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-rule bg-surface">
        <div className="container mx-auto px-4 py-5 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted">
          <span>&copy; 2026 Computor</span>
          <LegalLinks className="text-sm" />
          <NetideeNotice />
        </div>
      </footer>
    </div>
  );
}
