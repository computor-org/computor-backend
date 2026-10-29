'use client';

import { useBrowserLanguage } from '@/src/hooks/useBrowserLanguage';

const COPY = {
  de: {
    title: 'Etwas ist schiefgegangen',
    message: 'Beim Laden der Anwendung ist ein unerwarteter Fehler aufgetreten.',
    reference: 'Fehlerkennung:',
    retry: 'Erneut versuchen',
  },
  en: {
    title: 'Something went wrong',
    message: 'An unexpected error occurred while loading the application.',
    reference: 'Error reference:',
    retry: 'Try again',
  },
};

/**
 * Root error boundary — catches errors thrown by the root layout itself.
 * Must render its own <html>/<body> because the layout is gone at this point.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  // The root layout and its providers are gone here; the stored choice or the browser decides.
  const language = useBrowserLanguage();
  const t = COPY[language];
  return (
    <html lang={language}>
      <body style={{ fontFamily: 'system-ui, sans-serif' }}>
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1.5rem',
            background: '#f9fafb',
          }}
        >
          <div style={{ textAlign: 'center', maxWidth: '28rem' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#111827' }}>
              {t.title}
            </h1>
            <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#4b5563' }}>
              {t.message}
            </p>
            {error.digest && (
              <p style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#9ca3af' }}>
                {t.reference} {error.digest}
              </p>
            )}
            <button
              onClick={reset}
              style={{
                marginTop: '1.5rem',
                padding: '0.5rem 1rem',
                background: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              {t.retry}
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
