import type { UiLanguage } from '@/src/hooks/useUiLanguage';

/**
 * The course group the backend creates for self-enrolled learners. The backend
 * has no other marker for it: it finds the group by this title, which is unique
 * per course (SELF_REGISTRATION_GROUP_TITLE, business_logic/course_registration.py).
 */
export const SELF_REGISTRATION_GROUP_TITLE = 'Selbsteinschreibung';

/** A course group's title for display; the self-enrolment group in the reading language. */
export function courseGroupTitle<T extends string | null | undefined>(title: T, language: UiLanguage): string | T {
  if (title === SELF_REGISTRATION_GROUP_TITLE) return language === 'de' ? 'Selbsteinschreibung' : 'Self-enrolment';
  return title;
}
