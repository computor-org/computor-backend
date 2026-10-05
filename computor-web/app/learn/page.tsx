'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import EmptyState from '@/src/components/EmptyState';
import PublicLearnShell from '@/src/components/learn/PublicLearnShell';
import { API_BASE_URL, apiFetch } from '@/src/utils/apiClient';
import type { PublicCourseCatalogEntry } from '@/src/types/publicLearning';

export default function LearnPage() {
  const [courses, setCourses] = useState<PublicCourseCatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiFetch(`${API_BASE_URL}/public/courses`)
      .then(async response => {
        if (!response.ok) throw new Error('catalog unavailable');
        return response.json() as Promise<PublicCourseCatalogEntry[]>;
      })
      .then(rows => {
        if (!cancelled) setCourses(rows);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <PublicLearnShell>
      <div className="container mx-auto max-w-6xl px-4 py-12">
        <header className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-accent-text">
            Free public learning material
          </p>
          <h1 className="mt-2 text-4xl font-bold text-fg">Data Science mit Python</h1>
          <p className="mt-4 text-lg leading-8 text-muted">
            Browse courses and exercises directly on Computor. No account is
            required to read the public material.
          </p>
        </header>

        <section className="mt-10" aria-labelledby="course-shelf-heading">
          <h2 id="course-shelf-heading" className="text-2xl font-semibold text-fg">Courses</h2>
          {loading ? (
            <p className="mt-5 rounded-lg border border-rule bg-surface p-10 text-center text-muted">
              Loading courses…
            </p>
          ) : failed ? (
            <div className="mt-5">
              <EmptyState
                title="Courses are temporarily unavailable"
                description="The public course catalog could not be loaded."
              />
            </div>
          ) : courses.length === 0 ? (
            <div className="mt-5">
              <EmptyState title="No public courses are available right now." />
            </div>
          ) : (
            <div className="mt-5 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {courses.map(course => (
                <article key={course.id} className="flex min-h-64 flex-col rounded-xl border border-rule bg-surface p-6">
                  <div className="flex-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                      {course.language_code ? course.language_code.toUpperCase() : 'Course'}
                    </p>
                    <h3 className="mt-2 text-xl font-semibold text-fg">
                      {course.title || 'Untitled course'}
                    </h3>
                    {course.description && (
                      <p className="mt-3 whitespace-pre-line text-sm leading-6 text-muted">
                        {course.description}
                      </p>
                    )}
                  </div>
                  <Link
                    href={`/learn/${course.id}`}
                    className="mt-5 inline-flex self-start rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent-hover"
                  >
                    Browse course
                  </Link>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="mt-12 rounded-xl border border-rule bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">Ready to practise?</h2>
          <p className="mt-2 text-sm text-muted">
            Sign in to join a course, keep progress, run official tests, or use a hosted workspace.
          </p>
          <Link href="/courses/catalog" className="mt-3 inline-block text-sm text-accent-text hover:underline">
            Open course catalog
          </Link>
        </section>
      </div>
    </PublicLearnShell>
  );
}
