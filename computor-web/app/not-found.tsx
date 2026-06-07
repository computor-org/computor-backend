'use client';

import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';

/**
 * Global not-found boundary. Renders the unified NotFound inside the
 * authenticated app shell (sidebar + topbar) so an unmatched route shows a
 * consistent "nothing here" page rather than Next's full-screen error.
 */
export default function NotFoundPage() {
  return (
    <AuthenticatedLayout>
      <NotFound
        title="Nothing here yet"
        message="There is nothing to show on this page."
        backText="Back to Dashboard"
      />
    </AuthenticatedLayout>
  );
}
