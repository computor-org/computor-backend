// Titles and descriptions in the reading language (computor-org/issues#538).
//
// Courses, course contents, content types and examples keep `title` and
// `description` as the source text and may carry `title_i18n` /
// `description_i18n` maps keyed by language code. The student endpoints and
// the anonymous catalog resolve them for `?localize=<de|en>`; for responses
// without that parameter the client applies the same rule here.

type Translations = Record<string, string> | null | undefined;

export interface Translatable {
  title?: string | null;
  description?: string | null;
  title_i18n?: Translations;
  description_i18n?: Translations;
}

/** The entry for `language`, else `source`: the backend's `localized_text`. */
export function localizedText<S extends string | null | undefined>(
  translations: Translations,
  language: string | null | undefined,
  source: S,
): string | S {
  const value = language ? translations?.[language] : undefined;
  // A blank entry is a missing translation, not a blank title.
  return typeof value === 'string' && value.trim() ? value : source;
}

/**
 * `entity` with title and description in `language`, for display only: an edit
 * form must keep the source text it saves back.
 */
export function localized<T extends Translatable | null | undefined>(entity: T, language: string | null | undefined): T {
  if (!entity || !language) return entity;
  const title = localizedText(entity.title_i18n, language, entity.title);
  const description = localizedText(entity.description_i18n, language, entity.description);
  if (title === entity.title && description === entity.description) return entity;
  return { ...entity, title, description };
}
