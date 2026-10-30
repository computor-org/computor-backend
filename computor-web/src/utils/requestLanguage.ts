export type ReadingLanguage = 'de' | 'en';

/** The explicit choice made on a signed-out page; mirrors localStorage for the server. */
export const CHOSEN_LANGUAGE_COOKIE = 'computor_language';
/** The signed-in reading language, so the server renders a signed-in page in it. */
export const READING_LANGUAGE_COOKIE = 'computor_reading_language';

/** Set by proxy.ts on a page whose text has one fixed language. */
export const DOCUMENT_LANGUAGE_HEADER = 'x-computor-document-language';

/**
 * Legal texts with a fixed language: their pages say so in <html lang>
 * whatever the reader's language. Keep in step with the matcher in proxy.ts.
 */
const FIXED_LANGUAGE_PATHS: Record<string, ReadingLanguage> = {
  '/privacy/de': 'de',
  '/privacy/en': 'en',
  '/terms/de': 'de',
  '/terms/en': 'en',
  '/terms/changes': 'de',
  '/terms/en/changes': 'en',
};

export function fixedDocumentLanguage(pathname: string): ReadingLanguage | null {
  return FIXED_LANGUAGE_PATHS[pathname.replace(/\/+$/, '') || '/'] ?? null;
}

/** What the server can know about the reader's language from one request. */
export interface RequestLanguage {
  chosen: ReadingLanguage | null;
  reading: ReadingLanguage | null;
  browser: ReadingLanguage;
}

export function cookieLanguage(value?: string | null): ReadingLanguage | null {
  return value === 'de' || value === 'en' ? value : null;
}

/**
 * The browser language from Accept-Language, by the backend's rule
 * (computor_backend/utils/reading_language.py): the entry with the highest q
 * decides, any language but German reads English, no header reads German.
 */
export function acceptLanguage(header?: string | null): ReadingLanguage {
  if (!header?.trim()) return 'de';
  let bestQ = -Infinity;
  let bestTag = '';
  for (const entry of header.split(',')) {
    const [tag, ...params] = entry.split(';');
    let q = 1;
    for (const param of params) {
      const [key, value] = param.split('=');
      if (key.trim().toLowerCase() === 'q') {
        q = Number(value);
        if (Number.isNaN(q)) q = 0;
      }
    }
    if (q > bestQ) {
      bestQ = q;
      bestTag = tag.trim().toLowerCase();
    }
  }
  return bestTag.split('-')[0] === 'de' ? 'de' : 'en';
}

export function requestLanguage(
  chosenCookie: string | undefined,
  readingCookie: string | undefined,
  acceptLanguageHeader: string | null,
): RequestLanguage {
  return {
    chosen: cookieLanguage(chosenCookie),
    reading: cookieLanguage(readingCookie),
    browser: acceptLanguage(acceptLanguageHeader),
  };
}

/** Remember a language for the server render of the next request; null forgets it. */
export function writeLanguageCookie(name: string, language: ReadingLanguage | null): void {
  if (typeof document === 'undefined') return;
  document.cookie = language
    ? `${name}=${language}; path=/; max-age=31536000; samesite=lax`
    : `${name}=; path=/; max-age=0; samesite=lax`;
}
