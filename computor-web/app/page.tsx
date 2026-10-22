'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import PublicCourseCatalog from '@/src/components/courses/PublicCourseCatalog';
import LearningOptions from '@/src/components/courses/LearningOptions';
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
    heroScope: 'Die Kurse reichen von den ersten Schritten über Funktionen, Datenstrukturen und Visualisierung bis zu Datenanalyse, Differentialgleichungen und objektorientierter Programmierung.',
    toCourses: 'Zu den Kursen →',
    startTitle: 'Erste Schritte',
    startHow: 'Alles läuft im Browser, ohne Installation. Leg ein Konto an, öffne einen Kurs und starte die Kursumgebung.',
    startFirst: <>Beginne am besten mit <strong className="text-fg">Data Science mit Python &ndash; Grundlagen</strong>. Die erste Aufgabe, <em>&bdquo;Mathematische Konstanten&ldquo;</em> in Woche 1, führt in Variablen und Datentypen ein.</>,
    workflowTitle: 'Arbeitsablauf',
    workflow: <>Jede Aufgabe ist eine Python-Datei, die du bearbeitest und ausführst. Mit den Schaltflächen neben dem Aufgabennamen testest du deine Lösung und reichst sie ein. <em>Commit Assignment</em> speichert deinen Zwischenstand, ohne zu testen oder einzureichen.</>,
    lenaTitle: 'KI-Tutorin Lena',
    lena: <>Lena beantwortet Fragen zu den Aufgaben und gibt Hinweise, aber keine fertigen Lösungen. Öffne im Aufgabenbaum <em>Show Messages</em> und erwähne in deiner Frage {mention('@lena')} oder {mention('@ai')}.</>,
    footer: 'Interaktive Lernplattform für Programmierung.',
  },
  en: {
    signIn: 'Sign in',
    signOut: 'Sign out',
    heroTitle: 'Learn programming with',
    heroLead: 'Programming step by step.',
    heroScope: 'The courses range from first steps through functions, data structures and visualization to data analysis, differential equations and object-oriented programming.',
    toCourses: 'Browse courses →',
    startTitle: 'Getting started',
    startHow: 'Everything runs in the browser, no installation needed. Create an account, open a course and start the course environment.',
    startFirst: <>We recommend starting with <strong className="text-fg">Data Science mit Python &ndash; Grundlagen</strong>. Its first task, <em>&ldquo;Mathematical Constants&rdquo;</em> in week 1, introduces variables and data types.</>,
    workflowTitle: 'How it works',
    workflow: <>Each task is a Python file that you edit and run. The buttons next to the task name test and submit your solution. <em>Commit Assignment</em> saves your progress without testing or submitting.</>,
    lenaTitle: 'Lena, the AI tutor',
    lena: <>Lena answers questions about the tasks and gives hints, but no complete solutions. Open <em>Show Messages</em> in the task tree and mention {mention('@lena')} or {mention('@ai')} in your question.</>,
    footer: 'Interactive learning platform for programming.',
  },
};

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


  const handleGettingStarted = () => {
    if (gettingStartedUrl) {
      router.push(gettingStartedUrl);
    }
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
      <main className="container mx-auto px-4 pt-16 pb-32">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          {/* Hero Title */}
          <div className="space-y-4">
            <h2 className="text-5xl md:text-6xl font-bold text-fg">
              {t.heroTitle}{' '}
              <span className="text-accent-text">Computor</span>
            </h2>
            <p className="text-xl text-muted max-w-2xl mx-auto">
              {t.heroLead}
            </p>
            <p className="text-base text-muted max-w-2xl mx-auto">
              {t.heroScope}
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            {gettingStartedUrl ? (
              <button
                onClick={handleGettingStarted}
                className="px-8 py-4 bg-accent text-on-accent rounded-lg hover:bg-accent-hover transition-all transform hover:scale-105 font-semibold text-lg shadow-lg"
              >
                {t.toCourses}
              </button>
            ) : null}
          </div>

          {/* Getting Started */}
          <div className="bg-surface rounded-2xl shadow-lg p-8 border border-rule space-y-4 text-left">
            <h3 className="text-2xl font-bold text-fg">{t.startTitle}</h3>
            <p className="text-muted leading-relaxed">
              {t.startHow}
            </p>
            <p className="text-muted leading-relaxed">
              {t.startFirst}
            </p>
          </div>

          {/* Info cards: workflow, Lena */}
          <div className="grid md:grid-cols-2 gap-6 text-left">
            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule space-y-3">
              <div className="flex items-center space-x-3">
                <svg className="h-7 w-7 text-accent-text shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <h4 className="text-lg font-bold text-fg">{t.workflowTitle}</h4>
              </div>
              <p className="text-muted text-sm leading-relaxed">
                {t.workflow}
              </p>
            </div>

            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule space-y-3">
              <div className="flex items-center space-x-3">
                <svg className="h-7 w-7 text-accent-text shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <h4 className="text-lg font-bold text-fg">{t.lenaTitle}</h4>
              </div>
              <p className="text-muted text-sm leading-relaxed">
                {t.lena}
              </p>
            </div>
          </div>

          <div className="mt-12"><LearningOptions language={language} /></div>
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
