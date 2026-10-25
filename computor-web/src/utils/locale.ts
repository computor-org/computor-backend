import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';

/** German formats as de-AT, English follows the browser, as the learner pages do. */
export function localeFor(language: UiLanguage): string | undefined {
  return language === 'de' ? 'de-AT' : undefined;
}

function toDate(value: string | number | Date | null | undefined): Date | null {
  if (value === null || value === undefined || value === '') return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** A date in the interface language, or `fallback` when there is none to show. */
export function formatDate(
  value: string | number | Date | null | undefined,
  language: UiLanguage,
  fallback = '—',
): string {
  const date = toDate(value);
  return date ? date.toLocaleDateString(localeFor(language)) : fallback;
}

/** A date and time in the interface language, or `fallback` when there is none to show. */
export function formatDateTime(
  value: string | number | Date | null | undefined,
  language: UiLanguage,
  fallback = '—',
): string {
  const date = toDate(value);
  return date ? date.toLocaleString(localeFor(language)) : fallback;
}

/** A number in the interface language (decimal comma in German). */
export function formatNumber(
  value: number,
  language: UiLanguage,
  options?: Intl.NumberFormatOptions,
): string {
  return value.toLocaleString(localeFor(language), options);
}
