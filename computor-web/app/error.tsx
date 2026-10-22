'use client';

import Link from 'next/link';
import { useBrowserLanguage } from '@/src/hooks/useBrowserLanguage';

const COPY = {
  de: {
    title: 'Etwas ist schiefgegangen',
    message: 'Ein unerwarteter Fehler ist aufgetreten. Versuch es noch einmal oder geh zurück zur Übersicht.',
    reference: 'Fehlerreferenz',
    retry: 'Erneut versuchen',
    back: 'Zur Übersicht',
  },
  en: {
    title: 'Something went wrong',
    message: 'An unexpected error occurred. You can try again, or go back to the dashboard.',
    reference: 'Error reference',
    retry: 'Try again',
    back: 'Go to Dashboard',
  },
};

/**
 * Route-level error boundary. Catches uncaught render/runtime errors in any
 * page and offers a retry instead of Next.js's blank default error screen.
 */
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  // Outside the auth provider's guarantees: the stored or browser language.
  const t = COPY[useBrowserLanguage()];
  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas p-6">
      <div className="max-w-md w-full bg-surface rounded-lg border border-rule p-8 text-center">
        <svg
          className="mx-auto h-12 w-12 text-danger-text"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h1 className="mt-4 text-xl font-semibold text-fg">{t.title}</h1>
        <p className="mt-2 text-sm text-muted">
          {t.message}
        </p>
        {error.digest && (
          <p className="mt-2 text-xs text-subtle">{t.reference}: {error.digest}</p>
        )}
        <div className="mt-6 flex items-center justify-center gap-3">
          <button
            onClick={reset}
            className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover"
          >
            {t.retry}
          </button>
          <Link
            href="/dashboard"
            className="px-4 py-2 border border-rule-strong text-body rounded-lg text-sm font-medium hover:bg-canvas"
          >
            {t.back}
          </Link>
        </div>
      </div>
    </div>
  );
}
