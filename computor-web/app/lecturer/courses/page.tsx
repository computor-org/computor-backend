'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Redirect /lecturer/courses → /courses
 *
 * The generic course list already covers lectured courses; this page
 * rendered a `name` field the /lecturers/courses API does not return and
 * linked to a /lecturer/courses/[id] detail route that does not exist.
 */
export default function LecturerCoursesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/courses');
  }, [router]);

  return null;
}
