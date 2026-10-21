'use client';

import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import TypicalErrorsView from '@/src/components/progress/TypicalErrorsView';

export default function LecturerTypicalErrorsPage() {
  const courseId = useParams().id as string;

  return (
    <AuthenticatedLayout>
      <TypicalErrorsView courseId={courseId} />
    </AuthenticatedLayout>
  );
}
