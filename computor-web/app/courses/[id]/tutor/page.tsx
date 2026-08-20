'use client';

import { useParams } from 'next/navigation';
import ComingSoon from '@/src/components/ComingSoon';

export default function TutorViewPage() {
  const courseId = useParams().id as string;

  return (
    <ComingSoon
      title="Tutor view"
      message="Tools for reviewing and grading your students' submissions will live here. Until then, grading is available through the lecturer view."
      backLink={`/courses/${courseId}`}
      backText="Back to course"
    />
  );
}
