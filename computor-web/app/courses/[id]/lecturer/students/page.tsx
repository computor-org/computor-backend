'use client';

import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import { useParams } from 'next/navigation';

export default function LecturerStudentsPage() {
  const params = useParams();
  const courseId = params.id as string;

  return (
    <AuthenticatedLayout>
      <NotFound
        title="Students - Coming Soon"
        message="The lecturer students management view is not yet implemented."
        backLink={`/courses/${courseId}`}
        backText="Back to Course"
      />
    </AuthenticatedLayout>
  );
}
