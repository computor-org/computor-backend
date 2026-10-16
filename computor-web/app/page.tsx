'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import PublicCourseCatalog from '@/src/components/courses/PublicCourseCatalog';
import LearningOptions, { COMPUTOR_EXTENSION_URL } from '@/src/components/courses/LearningOptions';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';

export default function Home() {
  const router = useRouter();
  const { user, logout } = useAuth();
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
                Sign Out
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              <Link
                href="/login"
                className="px-4 py-2 bg-accent text-on-accent rounded-lg hover:bg-accent-hover transition-colors font-medium"
              >
                Sign In
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
              Programmieren lernen mit{' '}
              <span className="text-accent-text">Computor</span>
            </h2>
            <p className="text-xl text-muted max-w-2xl mx-auto">
              Wir bieten Ihnen eine interaktive Lernumgebung, in der Sie die Grundlagen der Programmierung
              mit Python erlernen können — <em>Schritt für Schritt</em>, mit automatisiertem Feedback
              und einer integrierten <em>AI-Assistentin</em>.
            </p>
            <p className="text-base text-muted max-w-2xl mx-auto">
              Die Kurse decken Python-Grundlagen, Funktionen, Datenstrukturen, Visualisierungen
              und Datenanalyse ab — von den ersten Schritten bis hin zu Differentialgleichungen
              und objektorientierter Programmierung.
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
                <span>VS Code Extension herunterladen</span>
              </button>
            ) : null}
            {gettingStartedUrl ? (
              <button
                onClick={handleGettingStarted}
                className="px-8 py-4 bg-surface text-accent-text rounded-lg border-2 border-accent hover:bg-accent-wash transition-all font-semibold text-lg"
              >
                Get Started →
              </button>
            ) : null}
          </div>
          <p className="text-muted text-base">
            Unsere verfügbaren Kurse finden Sie unter der Schaltfläche „Get Started →".
          </p>

          {/* Getting Started */}
          <div className="bg-surface rounded-2xl shadow-lg p-8 border border-rule space-y-4 text-left">
            <h3 className="text-2xl font-bold text-fg">Getting Started</h3>
            <p className="text-muted leading-relaxed">
              Zur Bearbeitung der Aufgaben benötigen Sie unsere <em>Kursumgebung</em>. Sie können entweder
              direkt hier im Browser arbeiten oder die lokale VS Code-Installation verwenden. Dafür
              müssen Sie zuerst einen Account auf der Computor-Plattform erstellen. Danach können Sie
              die <em>Kursumgebung</em> starten und die Aufgaben bearbeiten.
            </p>
            <p className="text-muted leading-relaxed">
              Als erstes empfehlen wir Ihnen den Kurs <strong className="text-fg">Data Science mit Python &ndash; Grundlagen</strong>.
              Die erste Aufgabe finden Sie in <strong className="text-fg">Woche 1</strong> unter dem Titel{' '}
              <em>&ldquo;Mathematische Konstanten&rdquo;</em> und führt Sie in Variablen und Datentypen in Python ein.
            </p>
          </div>

          {/* Info cards: Arbeitsablauf, AI-Assistenz */}
          <div className="grid md:grid-cols-2 gap-6 text-left">
            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule space-y-3">
              <div className="flex items-center space-x-3">
                <svg className="h-7 w-7 text-accent-text shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <h4 className="text-lg font-bold text-fg">Arbeitsablauf</h4>
              </div>
              <p className="text-muted text-sm leading-relaxed">
                In der <em>Kursumgebung</em> werden Ihnen die Aufgaben in Form von <em>Python-Dateien</em> bereitgestellt,
                die Sie bearbeiten und ausführen können. Sie können diese auch direkt testen und einreichen.
                Verwenden Sie dafür die Schaltflächen im Aufgabenbaum neben dem jeweiligen Aufgabennamen.
                Um Ihre Arbeitsfortschritte ohne Testen/Einreichen zu speichern, können Sie die Schaltfläche{' '}
                <em>Commit Assignment</em> verwenden.
              </p>
            </div>

            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule space-y-3">
              <div className="flex items-center space-x-3">
                <svg className="h-7 w-7 text-accent-text shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <h4 className="text-lg font-bold text-fg">AI-Assistenz</h4>
              </div>
              <p className="text-muted text-sm leading-relaxed">
                Für Hilfe bei der Bearbeitung der Aufgaben stellen wir Ihnen unsere AI-Assistentin{' '}
                <em className="text-fg">Lena</em> zur Verfügung. Sie können sie direkt in der Kursumgebung
                nutzen, um Fragen zu stellen oder <em>Hinweise</em> zu erhalten. Gehen Sie dafür bei den
                Schaltflächen im Aufgabenbaum auf <em>Show Messages</em>.
                Markieren Sie dann in Ihrer Frage mittels{' '}
                <code className="bg-accent-wash text-accent-text px-1 rounded text-xs">@ai</code> oder{' '}
                <code className="bg-accent-wash text-accent-text px-1 rounded text-xs">@lena</code> die
                AI-Assistentin, um eine Antwort zu erhalten. Beachten Sie, dass Lena nur als Hilfsmittel
                dient und keine vollständigen Lösungen liefert.
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
                Computor VS Code Extension
              </h3>
            </div>
            <p className="text-muted mb-6 max-w-2xl mx-auto">
              Programmieren Sie direkt in VS Code mit unserer Extension. Aufgaben einreichen, Tests ausführen und sofortiges Feedback erhalten — ohne den Editor zu verlassen.
            </p>
            <div className="flex flex-wrap gap-4 justify-center">
              <div className="px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium">
                ✓ Sofortiges Testen
              </div>
              <div className="px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium">
                ✓ Automatisches Einreichen
              </div>
              <div className="px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium">
                ✓ Live-Feedback
              </div>
              <div className="px-4 py-2 bg-accent-wash rounded-lg text-accent-text font-medium">
                ✓ Git-Integration
              </div>
            </div>
            <div className="mt-6 pt-6 border-t border-rule text-left">
              <p className="text-sm font-semibold text-fg mb-1">Troubleshooting</p>
              <p className="text-sm text-muted leading-relaxed">
                Sollte die Kursumgebung nicht verfügbar sein, können Sie weiterhin Ihre lokalen
                Arbeitsumgebungen nutzen. Nehmen Sie dafür den{' '}
                <a
                  href="https://gitlab.tugraz.at/computor/vscode-extension/-/blob/main/GETTING_STARTED.md?ref_type=heads"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent-text hover:underline font-medium"
                >
                  Getting Started Guide
                </a>{' '}
                zur Hilfe.
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
                Interaktive Kurse
              </h3>
              <p className="text-muted">
                Strukturierte Programmierkurse mit praxisnahen Aufgaben und Projekten.
              </p>
            </div>
            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule">
              <svg className="h-12 w-12 text-accent-text mb-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <h3 className="text-xl font-bold text-fg mb-2">
                Automatisiertes Testen
              </h3>
              <p className="text-muted">
                Code einreichen und sofortiges Feedback durch automatisierte Tests erhalten.
              </p>
            </div>
            <div className="bg-surface rounded-xl shadow-lg p-6 border border-rule">
              <svg className="h-12 w-12 text-accent-text mb-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <h3 className="text-xl font-bold text-fg mb-2">
                Gemeinsames Lernen
              </h3>
              <p className="text-muted">
                In Gruppen arbeiten, Lösungen teilen und gemeinsam mit anderen lernen.
              </p>
            </div>
          </div>

          <div className="mt-12"><LearningOptions /></div>
          <PublicCourseCatalog signedIn={!!user} />

        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 inset-x-0 z-40 border-t bg-surface">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-center text-muted">
            <p>&copy; 2026 Computor. Interaktive Lernplattform für Programmierung.</p>
            <LegalLinks className="text-sm" />
            <NetideeNotice />
          </div>
        </div>
      </footer>
    </div>
  );
}
