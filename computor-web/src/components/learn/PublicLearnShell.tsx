'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import LanguageSwitch from '@/src/components/LanguageSwitch';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { applyDocumentLanguage } from '@/src/utils/documentLanguage';

const COPY = {
  de: { courses: 'Kurse', dashboard: 'Übersicht', signIn: 'Anmelden', signOut: 'Abmelden', report: 'Problem melden' },
  en: { courses: 'Courses', dashboard: 'Dashboard', signIn: 'Sign in', signOut: 'Sign out', report: 'Report a problem' },
};

export default function PublicLearnShell({
  children,
  signInNext = '/courses/catalog',
}: {
  children: ReactNode;
  /** Where sign-in returns to; a course page passes its own catalog entry. */
  signInNext?: string;
}) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const language = useUiLanguage();
  const t = COPY[language];
  useEffect(() => {
    applyDocumentLanguage(language);
  }, [language]);

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
            {/* Phones get "Computor" only, and only the logo once the signed-in
                links need the room. */}
            <span className={`font-bold text-xl truncate ${user ? 'sr-only sm:not-sr-only' : ''}`}>
              Computor<span className="hidden sm:inline"> Learn</span>
            </span>
          </Link>
          <div className="flex items-center gap-3 text-sm">
            {/* Signed in, the profile sets the language. */}
            {!user && <LanguageSwitch />}
            <Link href="/learn" className="text-accent-text hover:underline">{t.courses}</Link>
            {user ? (
              <>
                <Link href="/dashboard" className="text-accent-text hover:underline">{t.dashboard}</Link>
                <button type="button" onClick={signOut} className="text-muted hover:text-fg">
                  {t.signOut}
                </button>
              </>
            ) : (
              <Link href={`/login?next=${encodeURIComponent(signInNext)}`} className="text-accent-text hover:underline">
                {t.signIn}
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-rule bg-surface">
        <div className="container mx-auto px-4 py-5 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted">
          <span>&copy; 2026 Computor</span>
          <LegalLinks className="text-sm" language={language} />
          {user && (
            <Link href="/problem" className="hover:text-accent-text hover:underline underline-offset-2">
              {t.report}
            </Link>
          )}
          <NetideeNotice language={language} />
        </div>
      </footer>
    </div>
  );
}
