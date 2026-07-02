'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /student/assignments → /courses
 *
 * Assignments are viewed per course at /courses/[id]/student/course-contents.
 * This cross-course list rendered fields the API does not return (due date,
 * grade) and linked to a detail route that does not exist.
 */
export default function StudentAssignmentsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
