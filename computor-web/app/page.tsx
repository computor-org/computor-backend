'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import PublicCourseCatalog from '@/src/components/courses/PublicCourseCatalog';
import { CODESPACES_URL, COMPUTOR_EXTENSION_URL } from '@/src/components/courses/LearningOptions';
import LanguageSwitch from '@/src/components/LanguageSwitch';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';
import { useBrowserLanguage } from '@/src/hooks/useBrowserLanguage';

const mention = (name: string) => <code className="bg-accent-wash text-accent-text px-1 rounded text-xs">{name}</code>;

const ICON_PATHS = {
  book: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
  code: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4',
  chat: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z',
};

const Icon = ({ name, className }: { name: keyof typeof ICON_PATHS; className: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICON_PATHS[name]} />
  </svg>
);

const COPY = {
  de: {
    signIn: 'Anmelden',
    signOut: 'Abmelden',
    heroTitle: 'Programmieren lernen mit',
    heroLead: 'Programmieren Schritt für Schritt.',
    heroScope: 'Offene Kurse zu Python und Data Science, von den ersten Schritten bis zu Datenanalyse und Differentialgleichungen.',
    toCourses: 'Kurse ohne Anmeldung entdecken →',
    allCourses: 'Alle Kurse',
    createAccount: 'Konto erstellen',
    toCatalog: 'Kurs beitreten',
    steps: [
      ['book', 'Kurse lesen', <>Ohne Konto lesbar. Beginne mit den Grundlagen, Woche 1.</>],
      ['code', 'Im Browser üben', <>Mit Konto startest du die Kursumgebung im Browser, ohne Installation. Dort bearbeitest du die Aufgaben, testest sie und reichst sie ein.</>],
      ['chat', 'Lena fragen', <>Die KI-Tutorin Lena gibt Hinweise statt fertiger Lösungen. Erwähne {mention('@lena')} in den Nachrichten zu einer Aufgabe.</>],
    ],
    local: 'Lieber lokal arbeiten?',
    footer: 'Interaktive Lernplattform für Programmierung.',
    report: 'Problem melden',
  },
  en: {
    signIn: 'Sign in',
    signOut: 'Sign out',
    heroTitle: 'Learn programming with',
    heroLead: 'Programming step by step.',
    heroScope: 'Open courses on Python and data science, from first steps to data analysis and differential equations.',
    toCourses: 'Explore courses without an account →',
    allCourses: 'All courses',
    createAccount: 'Create an account',
    toCatalog: 'Join a course',
    steps: [
      ['book', 'Read the courses', <>Readable without an account. Start with the basics, week 1.</>],
      ['code', 'Practise in the browser', <>With an account you start the course environment in the browser, no installation needed. There you edit, test and submit the tasks.</>],
      ['chat', 'Ask Lena', <>Lena, the AI tutor, gives hints instead of complete solutions. Mention {mention('@lena')} in the messages of a task.</>],
    ],
    local: 'Prefer to work locally?',
    footer: 'Interactive learning platform for programming.',
    report: 'Report a problem',
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
        <div className="container mx-auto px-4 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <Image src="/computor_logo.png" alt="Computor" width={40} height={40} className="h-10 w-10" />
            {/* On phones the hero names Computor right below; the header keeps the
                logo so the language switch and sign-in fit beside it. */}
            <h1 className="sr-only sm:not-sr-only text-2xl font-bold text-fg">Computor</h1>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitch />
            {user ? (
              <div className="flex items-center gap-2 sm:gap-4">
                <Link
                  href="/dashboard"
                  className="px-2 sm:px-4 py-2 text-accent-text hover:text-accent-text transition-colors font-medium"
                >
                  Dashboard
                </Link>
                <button
                  onClick={handleLogout}
                  className="px-3 sm:px-4 py-2 bg-surface text-danger-text border-2 border-danger rounded-lg hover:bg-danger-wash transition-colors font-medium"
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
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 pt-10 pb-10 md:pb-28">
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
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {t.steps.map(([icon, title, body]) => (
              <div key={icon} className="bg-surface rounded-xl shadow-lg p-6 border border-rule">
                <Icon name={icon} className="h-12 w-12 text-accent-text mb-4 mx-auto" />
                <h3 className="text-xl font-bold text-fg mb-2">{title}</h3>
                <p className="text-muted">{body}</p>
                {icon === 'book' && <div className="mt-3"><PublicCourseCatalog fallbackLabel={t.allCourses} /></div>}
                {icon === 'code' && (
                  <Link
                    href={user ? '/courses/catalog' : '/login?action=register&next=%2Fcourses%2Fcatalog'}
                    className="mt-4 inline-block px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium hover:underline"
                  >
                    {user ? t.toCatalog : t.createAccount}
                  </Link>
                )}
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 text-muted">
            <Icon name="code" className="h-5 w-5 text-accent-text" />
            <span>{t.local}</span>
            <a href={COMPUTOR_EXTENSION_URL} target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium hover:underline">Desktop VS Code</a>
            <a href={CODESPACES_URL} target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium hover:underline">GitHub Codespaces</a>
          </div>

        </div>
      </main>

      {/* Footer: pinned on wide screens, where the page fits one screen; on
          phones it would cover a fifth of the viewport, so it follows the content. */}
      <footer className="md:fixed md:bottom-0 md:inset-x-0 md:z-40 border-t bg-surface">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-center text-muted">
            <p>&copy; 2026 Computor. {t.footer}</p>
            <LegalLinks className="text-sm" language={language} />
            {user && (
              <Link href="/problem" className="text-sm hover:text-accent-text hover:underline underline-offset-2">
                {t.report}
              </Link>
            )}
            <NetideeNotice language={language} />
          </div>
        </div>
      </footer>
    </div>
  );
}
