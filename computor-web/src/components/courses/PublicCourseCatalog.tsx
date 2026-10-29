'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { PublicCourseCatalogEntry } from '@/src/types/publicLearning';
import { useBrowserLanguage } from '@/src/hooks/useBrowserLanguage';
import { localizedText } from '@/src/utils/localizedText';

/**
 * Public courses as a compact link list for the landing page (issue #415).
 *
 * Reads the generated static catalog; anonymous course reading needs no API
 * request. Until the catalog arrives, or if it is unreachable, a single link
 * to `/learn` stands in for the list.
 */
export default function PublicCourseCatalog({ fallbackLabel }: { fallbackLabel: string }) {
  const [courses, setCourses] = useState<PublicCourseCatalogEntry[]>([]);
  const language = useBrowserLanguage();

  useEffect(() => {
    let cancelled = false;
    fetch('/learning/catalog.json', { credentials: 'omit' })
      .then((response) => (response.ok ? response.json() : []))
      .then((rows: PublicCourseCatalogEntry[]) => {
        if (!cancelled && Array.isArray(rows)) setCourses(rows);
      })
      .catch(() => {
        // The fallback link stays.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const links = courses.length > 0
    ? courses.map((course) => ({ href: `/learn/${course.id}`, label: localizedText(course.title_i18n, language, course.title) }))
    : [{ href: '/learn', label: fallbackLabel }];

  return (
    <ul className="space-y-1">
      {links.map((link) => (
        <li key={link.href}>
          <Link href={link.href} className="text-accent-text font-medium hover:underline">
            {link.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}
