'use client';

import { useParams } from 'next/navigation';
import ComingSoon from '@/src/components/ComingSoon';

export default function TutorSubmissionsPage() {
  const courseId = useParams().id as string;

  return (
    <ComingSoon
      title="Submission queue"
      message="The queue of submissions waiting for a tutor's review is not built yet."
      backLink={`/courses/${courseId}`}
      backText="Back to course"
    />
  );
}
