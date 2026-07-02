'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /assignments → /courses
 *
 * Assignments live per course at /courses/[id]/student/assignments;
 * this route was an unlinked placeholder.
 */
export default function AssignmentsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
