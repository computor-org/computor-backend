'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import PublicCourseCatalog from '@/src/components/courses/PublicCourseCatalog';
import { CODESPACES_URL, COMPUTOR_EXTENSION_URL } from '@/src/components/courses/LearningOptions';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';
import { useBrowserLanguage } from '@/src/hooks/useBrowserLanguage';

const mention = (name: string) => <code className="bg-accent-wash text-accent-text px-1 rounded text-xs">{name}</code>;

const COPY = {
  de: {
    signIn: 'Anmelden',
    signOut: 'Abmelden',
    heroTitle: 'Programmieren lernen mit',
    heroLead: 'Programmieren Schritt für Schritt.',
    heroScope: 'Offene Kurse zu Python und Data Science, von den ersten Schritten bis zu Datenanalyse und Differentialgleichungen.',
    toCourses: 'Kurse ohne Anmeldung entdecken →',
    toWork: 'Anmelden und üben',
    steps: [
      ['1', 'Kurse lesen', <>Alle Kurse sind ohne Konto lesbar. Beginne mit <strong className="text-fg">Data Science mit Python &ndash; Grundlagen</strong>, Woche 1.</>],
      ['2', 'Im Browser üben', <>Mit Konto startest du die Kursumgebung im Browser, ohne Installation. Dort bearbeitest du die Aufgaben, testest sie und reichst sie ein.</>],
      ['3', 'Lena fragen', <>Die KI-Tutorin Lena gibt Hinweise statt fertiger Lösungen. Erwähne {mention('@lena')} in den Nachrichten zu einer Aufgabe.</>],
    ],
    local: 'Lieber lokal arbeiten?',
    footer: 'Interaktive Lernplattform für Programmierung.',
  },
  en: {
    signIn: 'Sign in',
    signOut: 'Sign out',
    heroTitle: 'Learn programming with',
    heroLead: 'Programming step by step.',
    heroScope: 'Open courses on Python and data science, from first steps to data analysis and differential equations.',
    toCourses: 'Explore courses without an account →',
    toWork: 'Sign in and practise',
    steps: [
      ['1', 'Read the courses', <>All courses are readable without an account. Start with <strong className="text-fg">Data Science mit Python &ndash; Grundlagen</strong>, week 1.</>],
      ['2', 'Practise in the browser', <>With an account you start the course environment in the browser, no installation needed. There you edit, test and submit the tasks.</>],
      ['3', 'Ask Lena', <>Lena, the AI tutor, gives hints instead of complete solutions. Mention {mention('@lena')} in the messages of a task.</>],
    ],
    local: 'Prefer to work locally?',
    footer: 'Interactive learning platform for programming.',
  },
} as const;

export default function Home() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const language = useBrowserLanguage();
  const t = COPY[language];
  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);
  const gettingStartedUrl = '/learn';

  // `/` is the public landing page and stays viewable when signed in (the header
  // shows Dashboard + Sign Out for authenticated users) — no auto-redirect, so a
  // signed-in user can switch back to this view.

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };



  return (
    <div className="min-h-screen bg-gradient-to-br from-accent-wash via-canvas to-accent-wash">
      {/* Header */}
      <header className="border-b bg-surface/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Image src="/computor_logo.png" alt="Computor" width={40} height={40} className="h-10 w-10" />
            <h1 className="text-2xl font-bold text-fg">Computor</h1>
          </div>
          {user ? (
            <div className="flex items-center space-x-4">
              <Link
                href="/dashboard"
                className="px-4 py-2 text-accent-text hover:text-accent-text transition-colors font-medium"
              >
                Dashboard
              </Link>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-surface text-danger-text border-2 border-danger rounded-lg hover:bg-danger-wash transition-colors font-medium"
              >
                {t.signOut}
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              <Link
                href="/login"
                className="px-4 py-2 bg-accent text-on-accent rounded-lg hover:bg-accent-hover transition-colors font-medium"
              >
                {t.signIn}
              </Link>
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 pt-10 pb-28">
        <div className="max-w-5xl mx-auto text-center space-y-8">
          <div className="space-y-3">
            <h2 className="text-4xl md:text-5xl font-bold text-fg">
              {t.heroTitle}{' '}
              <span className="text-accent-text">Computor</span>
            </h2>
            <p className="text-xl text-muted">{t.heroLead}</p>
            <p className="text-base text-muted max-w-2xl mx-auto">{t.heroScope}</p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link
              href={gettingStartedUrl}
              className="px-8 py-4 bg-accent text-on-accent rounded-lg hover:bg-accent-hover transition-all transform hover:scale-105 font-semibold text-lg shadow-lg"
            >
              {t.toCourses}
            </Link>
            {!user && (
              <Link
                href="/login"
                className="px-8 py-4 bg-surface text-accent-text rounded-lg border-2 border-accent hover:bg-accent-wash transition-all font-semibold text-lg"
              >
                {t.toWork}
              </Link>
            )}
          </div>

          <ol className="grid md:grid-cols-3 gap-6 text-left">
            {t.steps.map(([number, title, body]) => (
              <li key={number} className="bg-surface rounded-xl shadow-lg p-6 border border-rule space-y-2">
                <div className="flex items-center space-x-3">
                  <span className="h-8 w-8 shrink-0 rounded-full bg-accent-wash text-accent-text font-bold flex items-center justify-center">
                    {number}
                  </span>
                  <h3 className="text-lg font-bold text-fg">{title}</h3>
                </div>
                <p className="text-muted text-sm leading-relaxed">{body}</p>
              </li>
            ))}
          </ol>

          <p className="text-sm text-muted">
            {t.local}{' '}
            <a href={COMPUTOR_EXTENSION_URL} target="_blank" rel="noopener noreferrer" className="text-accent-text hover:underline">Desktop VS Code</a>
            {' · '}
            <a href={CODESPACES_URL} target="_blank" rel="noopener noreferrer" className="text-accent-text hover:underline">GitHub Codespaces</a>
          </p>

          <PublicCourseCatalog signedIn={!!user} />
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 inset-x-0 z-40 border-t bg-surface">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-center text-muted">
            <p>&copy; 2026 Computor. {t.footer}</p>
            <LegalLinks className="text-sm" />
            <NetideeNotice />
          </div>
        </div>
      </footer>
    </div>
  );
}
