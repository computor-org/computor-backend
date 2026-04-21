'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /tutor → /courses
 *
 * Tutor actions are always scoped to a specific course; the real dashboard
 * lives at /courses/[id]/tutor. Send the user to the course picker instead
 * of showing a cross-course aggregate that the API no longer supports.
 */
export default function TutorDashboardRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
