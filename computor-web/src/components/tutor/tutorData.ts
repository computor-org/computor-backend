/**
 * Shared data access for the tutor pages. Everything goes through the
 * `/tutors` endpoints, which enforce the `_tutor` floor per course.
 */

import { TutorsClient } from '@/src/generated/clients/TutorsClient';
import { CourseContentsClient } from '@/src/generated/clients/CourseContentsClient';
import type { TutorCourseMemberList } from 'types/generated';
import type { UiLanguage } from '@/src/hooks/useUiLanguage';
import { localizedText } from '@/src/utils/localizedText';

export const tutorsClient = new TutorsClient();
const contentsClient = new CourseContentsClient();

export function memberName(
  m: Pick<TutorCourseMemberList, 'user'> | null | undefined,
  language: UiLanguage = 'en',
): string {
  const u = m?.user;
  const name = [u?.given_name, u?.family_name].filter(Boolean).join(' ').trim();
  return name || u?.email || (language === 'de' ? 'Studierende/r' : 'Student');
}

/** Students of the course, by family name. */
export async function listCourseStudents(courseId: string): Promise<TutorCourseMemberList[]> {
  const members = await tutorsClient.tutorListCourseMembersEndpointTutorsCourseMembersGet({
    courseId,
    courseRoleId: '_student',
    limit: 1000,
  });
  return [...members].sort((a, b) =>
    `${a.user?.family_name ?? ''} ${a.user?.given_name ?? ''}`.localeCompare(
      `${b.user?.family_name ?? ''} ${b.user?.given_name ?? ''}`,
    ),
  );
}

/**
 * Assignment titles by id in the reading language, else the source title;
 * an empty map when the list is not readable.
 */
export async function contentTitles(courseId: string, language: UiLanguage): Promise<Map<string, string>> {
  try {
    const contents = await contentsClient.listCourseContentsCourseContentsGet({ courseId, limit: 1000 });
    return new Map(contents.map((c) => [c.id, localizedText(c.title_i18n, language, c.title) || c.path]));
  } catch {
    return new Map();
  }
}
