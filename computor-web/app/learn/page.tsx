'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import EmptyState from '@/src/components/EmptyState';
import PublicLearnShell from '@/src/components/learn/PublicLearnShell';
import { CODESPACES_URL, COMPUTOR_EXTENSION_URL } from '@/src/components/courses/LearningOptions';
import { useBrowserLanguage } from '@/src/hooks/useBrowserLanguage';
import type { PublicCourseCatalogEntry } from '@/src/types/publicLearning';
import { languageName } from '@/src/utils/locale';

const COPY = {
  de: {
    kicker: 'Offene Lernmaterialien',
    lead: 'Alle Kurse und Aufgaben sind ohne Konto lesbar.',
    courses: 'Kurse',
    loading: 'Kurse werden geladen…',
    unavailable: 'Kurse vorübergehend nicht verfügbar',
    unavailableDetail: 'Der Kurskatalog konnte nicht geladen werden.',
    empty: 'Derzeit sind keine öffentlichen Kurse verfügbar.',
    course: 'Kurs',
    untitled: 'Kurs ohne Titel',
    counts: (units: number, exercises: number) => `${units} Wochen · ${exercises} Aufgaben`,
    browse: 'Kurs öffnen',
    practiseTitle: 'Selbst üben?',
    practise: 'Mit Konto trittst du einem Kurs bei, testest und reichst Aufgaben ein und arbeitest im Browser.',
    catalog: 'Zum Kurskatalog',
  },
  en: {
    kicker: 'Open learning material',
    lead: 'All courses and exercises are readable without an account.',
    courses: 'Courses',
    loading: 'Loading courses…',
    unavailable: 'Courses are temporarily unavailable',
    unavailableDetail: 'The public course catalog could not be loaded.',
    empty: 'No public courses are available right now.',
    course: 'Course',
    untitled: 'Untitled course',
    counts: (units: number, exercises: number) => `${units} weeks · ${exercises} exercises`,
    browse: 'Open course',
    practiseTitle: 'Ready to practise?',
    practise: 'With an account you join a course, test and submit exercises and work in the browser.',
    catalog: 'Open the course catalog',
  },
};

export default function LearnPage() {
  const language = useBrowserLanguage();
  const t = COPY[language];
  const [courses, setCourses] = useState<PublicCourseCatalogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch('/learning/catalog.json', { credentials: 'omit' })
      .then(async response => {
        if (!response.ok) throw new Error('catalog unavailable');
        return response.json() as Promise<PublicCourseCatalogEntry[]>;
      })
      .then(rows => {
        if (cancelled) return;
        setCourses(rows);
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
            {t.kicker}
          </p>
          <h1 className="mt-2 text-4xl font-bold text-fg">Data Science mit Python</h1>
          <p className="mt-4 text-lg leading-8 text-muted">
            {t.lead}
          </p>
        </header>

        <section className="mt-10" aria-labelledby="course-shelf-heading">
          <h2 id="course-shelf-heading" className="text-2xl font-semibold text-fg">{t.courses}</h2>
          {loading ? (
            <p className="mt-5 rounded-lg border border-rule bg-surface p-10 text-center text-muted">
              {t.loading}
            </p>
          ) : failed ? (
            <div className="mt-5">
              <EmptyState
                title={t.unavailable}
                description={t.unavailableDetail}
              />
            </div>
          ) : courses.length === 0 ? (
            <div className="mt-5">
              <EmptyState title={t.empty} />
            </div>
          ) : (
            <div className="mt-5 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {courses.map(course => {
                const outline = course;
                return (
                <article key={course.id} className="flex min-h-64 flex-col rounded-xl border border-rule bg-surface p-6">
                  <div className="flex-1">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                      {course.language_code ? languageName(course.language_code, language) : t.course}
                    </p>
                    <h3 className="mt-2 text-xl font-semibold text-fg">
                      {course.title || t.untitled}
                    </h3>
                    {course.description && (
                      <p className="mt-3 whitespace-pre-line text-sm leading-6 text-muted">
                        {course.description}
                      </p>
                    )}
                  </div>
                  {outline && (
                    <p className="mt-4 text-xs text-subtle">
                      {t.counts(outline.unit_count, outline.exercise_count)}
                    </p>
                  )}
                  <Link
                    href={`/learn/${course.id}`}
                    className="mt-5 inline-flex self-start rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent-hover"
                  >
                    {t.browse}
                  </Link>
                </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="mt-12 rounded-xl border border-rule bg-surface p-6">
          <h2 className="text-lg font-semibold text-fg">{t.practiseTitle}</h2>
          <p className="mt-2 text-sm text-muted">
            {t.practise}
          </p>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm">
            <Link href="/courses/catalog" className="text-accent-text hover:underline">
              {t.catalog}
            </Link>
            <a href={COMPUTOR_EXTENSION_URL} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">
              Desktop VS Code
            </a>
            <a href={CODESPACES_URL} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">
              GitHub Codespaces
            </a>
          </div>
        </section>
      </div>
    </PublicLearnShell>
  );
}
