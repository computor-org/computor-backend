'use client';

import { useParams } from 'next/navigation';
import PublicCourseReader from '@/src/components/learn/PublicCourseReader';

export default function PublicCoursePage() {
  const params = useParams();
  return <PublicCourseReader courseId={params.courseId as string} />;
}
