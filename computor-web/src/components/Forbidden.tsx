'use client';

import AuthenticatedLayout from './AuthenticatedLayout';
import NotFound from './NotFound';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

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
  const de = useUiLanguage() === 'de';
  return (
    <AuthenticatedLayout>
      <NotFound
        title={de ? 'Nicht verfügbar' : 'Not available'}
        message={message ?? (de ? 'Du hast keinen Zugriff auf diese Seite.' : 'You do not have access to this page.')}
        backLink={backLink}
        backText={backText}
      />
    </AuthenticatedLayout>
  );
}
