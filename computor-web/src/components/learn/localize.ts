import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';
import type { PublicLearningCourseOutline } from '@/src/types/publicLearning';

const UNIT_TITLE = /^Week (\d+)$/;

/**
 * Title of an outline item in `language`. Exercises take the first Markdown
 * heading of that language's variant; units named "Week N" become "Woche N".
 * Anything else keeps the published title.
 */
export function localizedTitle(
  outline: PublicLearningCourseOutline,
  id: string,
  title: string,
  language: UiLanguage,
): string {
  const markdown = Object.hasOwn(outline.materials, id)
    ? outline.materials[id].markdown_variants[language]
    : undefined;
  const heading = markdown?.match(/^#\s+(.+?)\s*#*\s*$/m)?.[1];
  if (heading) return heading;
  const unit = title.match(UNIT_TITLE);
  if (unit && language === 'de') return `Woche ${unit[1]}`;
  return title;
}
