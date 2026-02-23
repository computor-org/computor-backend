'use client';

import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import { useParams } from 'next/navigation';

export default function TutorGradingPage() {
  const params = useParams();
  const courseId = params.id as string;

  return (
    <AuthenticatedLayout>
      <NotFound
        title="Grading - Coming Soon"
        message="The tutor grading view is not yet implemented."
        backLink={`/courses/${courseId}`}
        backText="Back to Course"
      />
    </AuthenticatedLayout>
  );
}
