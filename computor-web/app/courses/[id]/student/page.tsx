'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

/**
 * Redirect /courses/[id]/student → /courses/[id]/student/course-contents
 *
 * The student view has no overview page yet; course contents is the only
 * destination, so land there instead of on a placeholder.
 */
export default function StudentViewRedirect() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.id as string;

  useEffect(() => {
    router.replace(`/courses/${courseId}/student/course-contents`);
  }, [router, courseId]);

  return null;
}
