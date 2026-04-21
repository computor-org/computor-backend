'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /tutor/students → /courses
 *
 * The cross-course student roster has no backend counterpart — tutor actions
 * are per-course. Send the user to the course picker; from there the scoped
 * view under /courses/[id]/tutor lists that course's students with progress.
 */
export default function TutorStudentsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
