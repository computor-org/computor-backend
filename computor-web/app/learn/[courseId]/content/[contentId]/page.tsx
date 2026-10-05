'use client';

import { useParams } from 'next/navigation';
import PublicCourseReader from '@/src/components/learn/PublicCourseReader';

export default function PublicCourseContentPage() {
  const params = useParams();
  return <PublicCourseReader courseId={params.courseId as string} contentId={params.contentId as string} />;
}
