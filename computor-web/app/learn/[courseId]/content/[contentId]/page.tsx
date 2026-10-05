import { readFile } from 'node:fs/promises';
import path from 'node:path';
import PublicCourseReader from '@/src/components/learn/PublicCourseReader';

export const dynamicParams = false;

export async function generateStaticParams() {
  const root = path.join(process.cwd(), 'public/learning');
  const catalog: { id: string }[] = JSON.parse(await readFile(path.join(root, 'catalog.json'), 'utf8'));
  const result: { courseId: string; contentId: string }[] = [];
  for (const course of catalog) {
    const outline = JSON.parse(await readFile(path.join(root, 'courses', `${course.id}.json`), 'utf8'));
    result.push(...outline.contents.map((item: { id: string }) => ({ courseId: course.id, contentId: item.id })));
  }
  return result;
}

export default async function PublicCourseContentPage({ params }: { params: Promise<{ courseId: string; contentId: string }> }) {
  const { courseId, contentId } = await params;
  return <PublicCourseReader courseId={courseId} contentId={contentId} />;
}
