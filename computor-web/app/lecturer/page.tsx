'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /lecturer → /courses
 *
 * Lecturer actions are always scoped to a specific course; the real dashboard
 * lives at /courses/[id]/lecturer. The cross-course dashboard showed a
 * hardcoded student count and quick actions pointing at routes that were
 * never built.
 */
export default function LecturerDashboardRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
