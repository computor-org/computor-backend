'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import PublicCourseCatalog from '@/src/components/courses/PublicCourseCatalog';
import LearningOptions, { COMPUTOR_EXTENSION_URL } from '@/src/components/courses/LearningOptions';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';
import { useBrowserLanguage } from '@/src/hooks/useBrowserLanguage';

const GUIDE_URL = 'https://github.com/computor-org/computor-vscode/blob/main/docs/quick-start.md';
const guideLink = (label: string) => (
  <a href={GUIDE_URL} target="_blank" rel="noopener noreferrer" className="text-accent-text hover:underline font-medium">
    {label}
  </a>
);
const mention = (name: string) => <code className="bg-accent-wash text-accent-text px-1 rounded text-xs">{name}</code>;

const COPY = {
  de: {
    signIn: 'Anmelden',
    signOut: 'Abmelden',
    heroTitle: 'Programmieren lernen mit',
    heroLead: 'Lernen Sie Python Schritt für Schritt, mit automatischem Feedback zu jeder Abgabe und der KI-Tutorin Lena.',
    heroScope: 'Die Kurse reichen von den ersten Schritten über Funktionen, Datenstrukturen und Visualisierung bis zu Datenanalyse, Differentialgleichungen und objektorientierter Programmierung.',
    download: 'VS-Code-Erweiterung herunterladen',
    toCourses: 'Zu den Kursen →',
    startTitle: 'Erste Schritte',
    startHow: 'Sie arbeiten direkt im Browser oder in VS Code auf Ihrem eigenen Rechner. Legen Sie dazu ein Konto an und starten Sie die Kursumgebung.',
    startFirst: <>Beginnen Sie am besten mit <strong className="text-fg">Data Science mit Python &ndash; Grundlagen</strong>. Die erste Aufgabe, <em>&bdquo;Mathematische Konstanten&ldquo;</em> in Woche 1, führt in Variablen und Datentypen ein.</>,
    workflowTitle: 'Arbeitsablauf',
    workflow: <>Jede Aufgabe ist eine Python-Datei, die Sie bearbeiten und ausführen. Mit den Schaltflächen neben dem Aufgabennamen testen Sie Ihre Lösung und reichen sie ein. <em>Commit Assignment</em> speichert Ihren Zwischenstand, ohne zu testen oder einzureichen.</>,
    lenaTitle: 'KI-Tutorin Lena',
    lena: <>Lena beantwortet Fragen zu den Aufgaben und gibt Hinweise, aber keine fertigen Lösungen. Öffnen Sie im Aufgabenbaum <em>Show Messages</em> und erwähnen Sie in Ihrer Frage {mention('@lena')} oder {mention('@ai')}.</>,
    extensionTitle: 'Computor-Erweiterung für VS Code',
    extension: 'Aufgaben bearbeiten, testen und einreichen, ohne VS Code zu verlassen.',
    badges: ['Sofortiges Testen', 'Automatisches Einreichen', 'Live-Feedback', 'Git-Integration'],
    offlineTitle: 'Kursumgebung nicht erreichbar?',
    offline: <>Dann arbeiten Sie lokal in VS Code weiter. Die {guideLink('Kurzanleitung')} erklärt die Einrichtung.</>,
    features: [
      ['Interaktive Kurse', 'Strukturierte Programmierkurse mit praxisnahen Aufgaben und Projekten.'],
      ['Automatisiertes Testen', 'Code einreichen und sofort Feedback aus automatischen Tests erhalten.'],
      ['Gemeinsames Lernen', 'In Gruppen arbeiten, Lösungen teilen und gemeinsam mit anderen lernen.'],
    ],
    footer: 'Interaktive Lernplattform für Programmierung.',
  },
  en: {
    signIn: 'Sign in',
    signOut: 'Sign out',
    heroTitle: 'Learn programming with',
    heroLead: 'Learn Python step by step, with automatic feedback on every submission and Lena, the AI tutor.',
    heroScope: 'The courses range from first steps through functions, data structures and visualization to data analysis, differential equations and object-oriented programming.',
    download: 'Download the VS Code extension',
    toCourses: 'Browse courses →',
    startTitle: 'Getting started',
    startHow: 'Work directly in the browser or in VS Code on your own computer. Create an account, then start the course environment.',
    startFirst: <>We recommend starting with <strong className="text-fg">Data Science mit Python &ndash; Grundlagen</strong>. Its first task, <em>&ldquo;Mathematical Constants&rdquo;</em> in week 1, introduces variables and data types.</>,
    workflowTitle: 'How it works',
    workflow: <>Each task is a Python file that you edit and run. The buttons next to the task name test and submit your solution. <em>Commit Assignment</em> saves your progress without testing or submitting.</>,
    lenaTitle: 'Lena, the AI tutor',
    lena: <>Lena answers questions about the tasks and gives hints, but no complete solutions. Open <em>Show Messages</em> in the task tree and mention {mention('@lena')} or {mention('@ai')} in your question.</>,
    extensionTitle: 'Computor VS Code extension',
    extension: 'Edit, test and submit assignments without leaving VS Code.',
    badges: ['Instant testing', 'Automatic submission', 'Live feedback', 'Git integration'],
    offlineTitle: 'Course environment unavailable?',
    offline: <>Keep working locally in VS Code. The {guideLink('quick start guide')} explains the setup.</>,
    features: [
      ['Interactive courses', 'Structured programming courses with hands-on assignments and projects.'],
      ['Automated testing', 'Submit your code and get immediate feedback from automated tests.'],
      ['Learning together', 'Work in groups, share solutions and learn with your peers.'],
    ],
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
  const extensionUrl = COMPUTOR_EXTENSION_URL;
  const gettingStartedUrl = '/learn';

  // `/` is the public landing page and stays viewable when signed in (the header
  // shows Dashboard + Sign Out for authenticated users) — no auto-redirect, so a
  // signed-in user can switch back to this view.

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };

  const handleDownload = () => {
    if (extensionUrl) {
      window.open(extensionUrl, '_blank', 'noopener,noreferrer');
    }
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
            {extensionUrl ? (
              <button
                className="px-8 py-4 bg-accent text-on-accent rounded-lg hover:bg-accent-hover transition-all transform hover:scale-105 font-semibold text-lg shadow-lg flex items-center space-x-2"
                onClick={handleDownload}
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <span>{t.download}</span>
              </button>
            ) : null}
            {gettingStartedUrl ? (
              <button
                onClick={handleGettingStarted}
                className="px-8 py-4 bg-surface text-accent-text rounded-lg border-2 border-accent hover:bg-accent-wash transition-all font-semibold text-lg"
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

          {/* VS Code Extension Card */}
          <div className="mt-16 bg-surface rounded-2xl shadow-xl p-8 border border-rule">
            <div className="flex items-center justify-center space-x-3 mb-4">
              <svg className="h-10 w-10 text-accent-text" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <h3 className="text-2xl font-bold text-fg">
                {t.extensionTitle}
              </h3>
            </div>
            <p className="text-muted mb-6 max-w-2xl mx-auto">
              {t.extension}
            </p>
            <div className="flex flex-wrap gap-4 justify-center">
              {t.badges.map(badge => (
                <div key={badge} className="px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium">
                  ✓ {badge}
                </div>
              ))}
            </div>
            <div className="mt-6 pt-6 border-t border-rule text-left">
              <p className="text-sm font-semibold text-fg mb-1">{t.offlineTitle}</p>
              <p className="text-sm text-muted leading-relaxed">
                {t.offline}
              </p>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-3 gap-8 mt-16">
            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule">
              <svg className="h-12 w-12 text-accent-text mb-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <h3 className="text-xl font-bold text-fg mb-2">
                {t.features[0][0]}
              </h3>
              <p className="text-muted">
                {t.features[0][1]}
              </p>
            </div>
            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule">
              <svg className="h-12 w-12 text-accent-text mb-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <h3 className="text-xl font-bold text-fg mb-2">
                {t.features[1][0]}
              </h3>
              <p className="text-muted">
                {t.features[1][1]}
              </p>
            </div>
            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule">
              <svg className="h-12 w-12 text-accent-text mb-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <h3 className="text-xl font-bold text-fg mb-2">
                {t.features[2][0]}
              </h3>
              <p className="text-muted">
                {t.features[2][1]}
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
