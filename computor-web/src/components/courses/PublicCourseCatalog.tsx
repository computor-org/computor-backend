'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import CourseCard from '@/src/components/courses/CourseCard';
import { HAS_OWN_LEGAL_PAGES, LEGAL_PROFILE } from '@/src/config/legal';
import { API_BASE_URL, apiFetch } from '@/src/utils/apiClient';
import type { CoursePublicCatalogEntry } from 'types/generated';

/** Where the CTA sends the visitor after sign-in: the self-registration catalog. */
const CATALOG_PATH = '/courses/catalog';

/**
 * "Kurse / Courses" section of the landing page (issue #415).
 *
 * Reads the anonymous GET /public/courses and renders nothing when it fails or
 * is empty, so an install without public courses (or with the backend down)
 * keeps the landing page as it was. Joining still happens in the signed-in
 * catalog: the CTA signs in and lands there.
 */
export default function PublicCourseCatalog({ signedIn }: { signedIn: boolean }) {
  const [courses, setCourses] = useState<CoursePublicCatalogEntry[]>([]);

  useEffect(() => {
    let cancelled = false;
    apiFetch(`${API_BASE_URL}/public/courses`)
      .then((response) => (response.ok ? response.json() : []))
      .then((rows: CoursePublicCatalogEntry[]) => {
        if (!cancelled && Array.isArray(rows)) setCourses(rows);
      })
      .catch(() => {
        // Best-effort teaser: no section when the catalog is unreachable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (courses.length === 0) return null;

  // computor.at runs an invite-only pilot: existing users sign in (GitHub or
  // email), new participants need an invite link (/join/<code>).
  const isPublicPilot = LEGAL_PROFILE === 'computor-at';
  const ctaLabel = signedIn ? 'Zum Kurskatalog / Open the catalog' : 'Anmelden / Sign in';
  const ctaHref = signedIn ? CATALOG_PATH : `/login?next=${encodeURIComponent(CATALOG_PATH)}`;

  return (
    <section aria-labelledby="public-courses-heading" className="mt-16 text-left">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-6">
        <div>
          <h3 id="public-courses-heading" className="text-2xl font-bold text-fg">
            Kurse / Courses
          </h3>
          <p className="text-muted mt-1">
            {isPublicPilot
              ? 'Pilotbetrieb – Teilnahme mit Einladungslink / Pilot – join with an invite link'
              : 'Offen zur Anmeldung / Open for registration'}
          </p>
          <p className="text-muted mt-1">
            <Link href="/learn" className="text-accent-text hover:underline">Read public courses without an account</Link>
            {' — practice in desktop VS Code or your own GitHub Codespace.'}
          </p>
        </div>
        <div className="flex flex-col items-start sm:items-end gap-1">
          <Link
            href={ctaHref}
            className="px-5 py-2.5 bg-accent text-on-accent rounded-lg hover:bg-accent-hover transition-colors font-semibold"
          >
            {ctaLabel}
          </Link>
          {!signedIn && HAS_OWN_LEGAL_PAGES ? (
            // The privacy notice must be reachable before GitHub collects anything.
            <p className="text-xs text-muted">
              <a href="/privacy" className="hover:underline">Datenschutz</a>
              {' · '}
              <a href="/terms" className="hover:underline">Nutzungsbedingungen</a>
            </p>
          ) : null}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {courses.map((course) => (
          <CourseCard key={course.id} course={course} />
        ))}
      </div>
    </section>
  );
}
