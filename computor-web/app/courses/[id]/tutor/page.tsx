'use client';

import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';

export default function TutorViewPage() {
  const courseId = useParams().id as string;

  return (
    <AuthenticatedLayout>
      <NotFound
        title="Tutor - Coming Soon"
        message="The tutor view is not yet implemented."
        backLink={`/courses/${courseId}`}
        backText="Back to Course"
      />
    </AuthenticatedLayout>
  );
}
