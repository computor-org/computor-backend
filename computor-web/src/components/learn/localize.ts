import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';
import type { PublicLearningCourseOutline } from '@/src/types/publicLearning';
import { localizedText } from '@/src/utils/localizedText';

const UNIT_TITLE = /^(?:Week|Woche) (\d+)$/;

/**
 * Title of an outline item in `language`: its translated title, else for
 * exercises the first Markdown heading of that language's variant; units
 * named "Week N" or "Woche N" follow the language.
 * Anything else keeps the published title.
 */
export function localizedTitle(
  outline: PublicLearningCourseOutline,
  id: string,
  title: string,
  language: UiLanguage,
): string {
  const material = Object.hasOwn(outline.materials, id) ? outline.materials[id] : undefined;
  const translated = localizedText(material?.title_i18n, language, null);
  if (translated) return translated;
  const markdown = material?.markdown_variants[language];
  const heading = markdown?.match(/^#\s+(.+?)\s*#*\s*$/m)?.[1];
  if (heading) return heading;
  const unit = title.match(UNIT_TITLE);
  if (unit) return language === 'de' ? `Woche ${unit[1]}` : `Week ${unit[1]}`;
  return title;
}
