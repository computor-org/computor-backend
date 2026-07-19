'use client';

import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import CourseProgressView from '@/src/components/progress/CourseProgressView';

export default function LecturerGradingPage() {
  const courseId = useParams().id as string;

  return (
    <AuthenticatedLayout>
      <CourseProgressView courseId={courseId} />
    </AuthenticatedLayout>
  );
}
