'use client';

import { useParams } from 'next/navigation';
import ComingSoon from '@/src/components/ComingSoon';

export default function TutorGradingPage() {
  const courseId = useParams().id as string;

  return (
    <ComingSoon
      title="Tutor grading"
      message="Grading a student's work as a tutor is not built yet."
      backLink={`/courses/${courseId}`}
      backText="Back to course"
    />
  );
}
