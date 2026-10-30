'use client';

import { useCallback } from 'react';
import { useResource } from '@/src/hooks/useResource';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { localizedText } from '@/src/utils/localizedText';

type Titled = { id: string; slug?: string; title?: string | null; title_i18n?: Record<string, string> | null };

async function list(url: string): Promise<Titled[]> {
  const response = await apiFetch(url);
  return response.ok ? response.json() : [];
}

/**
 * Titles of a course's contents and content types in the reading language, for
 * staff views whose own payload carries only the source title (typical errors,
 * progress by content type). Without an entry the given fallback stays.
 */
export function useCourseTitles(courseId: string) {
  const language = useUiLanguage();
  const { data } = useResource(async () => {
    const [contents, types] = await Promise.all([
      list(`${API_BASE_URL}/lecturers/course-contents?course_id=${courseId}&limit=500`).catch(() => []),
      list(`${API_BASE_URL}/course-content-types?course_id=${courseId}&limit=200`).catch(() => []),
    ]);
    return {
      contents: new Map(contents.map((c) => [c.id, c])),
      types: new Map(types.map((t) => [t.slug ?? t.id, t])),
    };
  }, [courseId]);

  const contentTitle = useCallback(
    (id: string, fallback: string) => localizedText(data?.contents.get(id)?.title_i18n, language, fallback),
    [data, language],
  );
  const typeTitle = useCallback(
    (slug: string, fallback: string) => localizedText(data?.types.get(slug)?.title_i18n, language, fallback),
    [data, language],
  );
  return { contentTitle, typeTitle };
}
