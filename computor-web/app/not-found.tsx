'use client';

import { useEffect } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { applyDocumentLanguage } from '@/src/utils/documentLanguage';

/**
 * Global not-found boundary. Signed in, it renders the unified NotFound inside
 * the authenticated app shell (sidebar + topbar) so an unmatched route shows a
 * consistent "nothing here" page rather than Next's full-screen error.
 *
 * Anonymous visitors get a plain 404 instead. The app shell sends them to
 * sign-in, which for a URL that does not exist promised a page behind the
 * login that was never there. Real protected routes are matched routes, so
 * they never reach this boundary and keep their sign-in redirect.
 */
export default function NotFoundPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const language = useUiLanguage();
  const de = language === 'de';

  useEffect(() => {
    if (!isLoading && !isAuthenticated) applyDocumentLanguage(language);
  }, [isLoading, isAuthenticated, language]);

  if (isLoading) return <div className="min-h-screen bg-canvas" />;

  if (!isAuthenticated) {
    return (
      <main className="min-h-screen bg-canvas flex items-center justify-center">
        <NotFound
          message={de ? 'Diese Seite gibt es nicht.' : 'This page does not exist.'}
          backLink="/"
          backText={de ? 'Zur Startseite' : 'Go to the home page'}
        />
      </main>
    );
  }

  return (
    <AuthenticatedLayout>
      <NotFound
        title={de ? 'Hier gibt es nichts' : 'Nothing here yet'}
        message={de ? 'Auf dieser Seite gibt es nichts anzuzeigen.' : 'There is nothing to show on this page.'}
        backText={de ? 'Zur Übersicht' : 'Back to Dashboard'}
      />
    </AuthenticatedLayout>
  );
}
