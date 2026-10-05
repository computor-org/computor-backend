import { readFile } from 'node:fs/promises';
import path from 'node:path';
import PublicCourseReader from '@/src/components/learn/PublicCourseReader';

export const dynamicParams = false;

export async function generateStaticParams() {
  const catalog = JSON.parse(await readFile(path.join(process.cwd(), 'public/learning/catalog.json'), 'utf8'));
  return catalog.map((course: { id: string }) => ({ courseId: course.id }));
}

export default async function PublicCoursePage({ params }: { params: Promise<{ courseId: string }> }) {
  const { courseId } = await params;
  return <PublicCourseReader courseId={courseId} />;
}
