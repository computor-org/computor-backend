import type { UiLanguage } from '@/src/hooks/useBrowserLanguage';

/**
 * The formatting locale of a reading language: German as de-AT, English as the
 * browser's English variant, else en-US. Never the browser locale as such, which
 * put German dates beside English labels (computor-org/issues#552).
 */
export function localeFor(language: UiLanguage): string {
  if (language === 'de') return 'de-AT';
  const browser = typeof navigator === 'undefined' ? '' : navigator.language ?? '';
  return /^en(-|$)/i.test(browser) ? browser : 'en-US';
}

/** A language code as a name in the reading language ("de" -> "Deutsch" or "German"). */
export function languageName(code: string, language: UiLanguage): string {
  try {
    const name = new Intl.DisplayNames([language], { type: 'language' }).of(code.trim().toLowerCase());
    if (name && name.toLowerCase() !== code.trim().toLowerCase()) return name;
  } catch {
    // Not a language code Intl knows; show it as it is.
  }
  return code.toUpperCase();
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
