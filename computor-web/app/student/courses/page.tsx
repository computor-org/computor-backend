'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /student/courses → /courses
 *
 * The generic course list already covers enrolled courses; this page
 * rendered fields the /students/courses API does not return and linked to
 * a /student/courses/[id] detail route that does not exist.
 */
export default function StudentCoursesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
