'use client';

import AuthenticatedLayout from './AuthenticatedLayout';
import NotFound from './NotFound';

/**
 * Standard "you may not see this page" state — the role-gate render repeated
 * across management pages. Use as an early return:
 *   if (!authLoading && isAuthenticated && !canManage) return <Forbidden message="…" />;
 */
export default function Forbidden({
  message,
  backLink,
  backText,
}: {
  message?: string;
  backLink?: string;
  backText?: string;
}) {
  return (
    <AuthenticatedLayout>
      <NotFound
        title="Not available"
        message={message ?? 'You do not have access to this page.'}
        backLink={backLink}
        backText={backText}
      />
    </AuthenticatedLayout>
  );
}
