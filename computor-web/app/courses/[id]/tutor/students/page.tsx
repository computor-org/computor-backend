'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

/**
 * Redirect /courses/[id]/tutor/students → /courses/[id]/tutor
 * The main tutor page already has the students table with progress data.
 */
export default function TutorStudentsPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.id as string;

  useEffect(() => {
    router.replace(`/courses/${courseId}/tutor`);
  }, [courseId, router]);

  return null;
}
