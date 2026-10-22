'use client';

import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

/**
 * Global not-found boundary. Renders the unified NotFound inside the
 * authenticated app shell (sidebar + topbar) so an unmatched route shows a
 * consistent "nothing here" page rather than Next's full-screen error.
 */
export default function NotFoundPage() {
  const de = useUiLanguage() === 'de';
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
