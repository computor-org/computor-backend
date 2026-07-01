'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /student → /courses
 *
 * Student actions are always scoped to a specific course; the real view
 * lives at /courses/[id]/student. Send the user to the course picker instead
 * of a cross-course dashboard whose quick actions pointed at routes that
 * were never built.
 */
export default function StudentDashboardRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
