'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import {
  CODESPACES_URL,
  COMPUTOR_EXTENSION_URL,
  PUBLIC_COURSES_URL,
} from '@/src/components/courses/LearningOptions';
import EmptyState from '@/src/components/EmptyState';
import PublicLearnShell from '@/src/components/learn/PublicLearnShell';
import PublicMarkdown from '@/src/components/learn/PublicMarkdown';
import type {
  PublicLearningContent,
  PublicLearningContentSummary,
  PublicLearningCourseOutline,
} from '@/src/types/publicLearning';

const LANGUAGE_LABEL: Record<string, string> = {
  de: 'Deutsch',
  en: 'English',
};

function OutlineLinks({
  outline,
  activeContentId,
}: {
  outline: PublicLearningCourseOutline;
  activeContentId?: string;
}) {
  return (
    <nav aria-label="Course outline" className="space-y-0.5">
      <Link
        href={`/learn/${outline.id}`}
        className={`block rounded-md px-3 py-2 text-sm font-medium ${
          !activeContentId || activeContentId === outline.welcome_content_id
            ? 'bg-accent-wash text-accent-text'
            : 'text-body hover:bg-sunken'
        }`}
      >
        Welcome / Start here
      </Link>
      {outline.contents.filter(item => item.id !== outline.welcome_content_id).map((item) => (
        <Link
          key={item.id}
          href={`/learn/${outline.id}/content/${item.id}`}
          className={`block rounded-md py-2 pr-3 text-sm ${
            activeContentId === item.id
              ? 'bg-accent-wash text-accent-text font-medium'
              : item.is_submittable
                ? 'text-body hover:bg-sunken'
                : 'text-fg font-semibold hover:bg-sunken'
          }`}
          style={{ paddingLeft: `${0.75 + item.depth * 1.1}rem` }}
        >
          <span className="block truncate">{item.title}</span>
        </Link>
      ))}
    </nav>
  );
}

function ReaderActions({ signedIn }: { signedIn: boolean }) {
  const computorHref = signedIn
    ? '/courses/catalog'
    : `/login?next=${encodeURIComponent('/courses/catalog')}`;
  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <p className="text-sm font-semibold text-fg">Want to work on the exercises?</p>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm">
        <Link href={computorHref} className="text-accent-text hover:underline">
          {signedIn ? 'Open course catalog' : 'Sign in to join'}
        </Link>
        <a href={COMPUTOR_EXTENSION_URL} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">
          Desktop VS Code
        </a>
        <a href={CODESPACES_URL} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">
          GitHub Codespaces
        </a>
      </div>
    </div>
  );
}

export default function PublicCourseReader({
  courseId,
  contentId,
}: {
  courseId: string;
  contentId?: string;
}) {
  const { user } = useAuth();
  const [loaded, setLoaded] = useState<{
    courseId: string; outline: PublicLearningCourseOutline | null; error: string | null;
  } | null>(null);
  const [requestedLanguage, setRequestedLanguage] = useState<string | null>(() => {
    const lang = typeof navigator === 'undefined' ? '' : navigator.language.split('-')[0].toLowerCase();
    return ['de', 'en'].includes(lang) ? lang : null;
  });
  const outline = loaded?.courseId === courseId ? loaded.outline : null;
  const outlineLoading = loaded?.courseId !== courseId;
  const error = loaded?.courseId === courseId ? loaded.error : null;
  const contentLoading = false;

  useEffect(() => {
    let cancelled = false;
    fetch(`/learning/courses/${encodeURIComponent(courseId)}.json`, { credentials: 'omit' })
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 404 ? 'Course not found.' : 'Could not load this course.');
        return response.json() as Promise<PublicLearningCourseOutline>;
      })
      .then(data => {
        if (!cancelled) setLoaded({ courseId, outline: data, error: null });
      })
      .catch(err => {
        if (!cancelled) setLoaded({ courseId, outline: null, error: err instanceof Error ? err.message : 'Could not load this course.' });
      });
    return () => { cancelled = true; };
  }, [courseId]);

  const activeContentId = contentId ?? outline?.welcome_content_id ?? undefined;

  const material = activeContentId && outline && Object.hasOwn(outline.materials, activeContentId)
    ? outline.materials[activeContentId] : undefined;
  const languages = Object.keys(material?.markdown_variants ?? {});
  const language = [requestedLanguage, outline?.language_code, 'en', 'de']
    .find(value => value && languages.includes(value)) ?? languages[0];
  const content: PublicLearningContent | null = material ? {
    ...material, markdown: material.markdown_variants[language ?? ''] ?? '',
    selected_language: language, available_languages: languages,
  } : null;

  const exercises = useMemo(
    () => outline?.contents.filter(item => item.is_submittable) ?? [],
    [outline],
  );
  const exerciseIndex = activeContentId
    ? exercises.findIndex(item => item.id === activeContentId)
    : -1;
  const previous = exerciseIndex > 0 ? exercises[exerciseIndex - 1] : undefined;
  const next = exerciseIndex >= 0 && exerciseIndex < exercises.length - 1
    ? exercises[exerciseIndex + 1]
    : undefined;

  const firstExercise: PublicLearningContentSummary | undefined = outline?.first_exercise_id
    ? outline.contents.find(item => item.id === outline.first_exercise_id)
    : exercises[0];

  return (
    <PublicLearnShell>
      <div className="container mx-auto max-w-7xl px-4 py-8">
        {outlineLoading ? (
          <div className="py-24 text-center text-muted">Loading course…</div>
        ) : !outline ? (
          <EmptyState title="Course unavailable" description={error ?? 'This public course could not be loaded.'} />
        ) : (
          <>
            <div className="mb-6">
              <div className="text-sm text-muted">
                <Link href="/learn" className="text-accent-text hover:underline">Courses</Link>
                <span className="mx-2">/</span>
                <span>{outline.title}</span>
              </div>
              <h1 className="mt-2 text-3xl font-bold text-fg">{outline.title}</h1>
              <p className="mt-2 text-sm text-muted">
                {outline.unit_count} units · {outline.exercise_count} exercises
                {outline.language_code ? ` · ${outline.language_code.toUpperCase()}` : ''}
              </p>
            </div>

            <details className="md:hidden mb-5 rounded-lg border border-rule bg-surface p-3">
              <summary className="cursor-pointer font-medium">Course outline</summary>
              <div className="mt-3 max-h-[55vh] overflow-y-auto">
                <OutlineLinks outline={outline} activeContentId={activeContentId} />
              </div>
            </details>

            <div className="grid gap-8 md:grid-cols-[18rem_minmax(0,1fr)]">
              <aside className="hidden md:block">
                <div className="sticky top-20 max-h-[calc(100vh-7rem)] overflow-y-auto rounded-lg border border-rule bg-surface p-3 scroll-slim">
                  <OutlineLinks outline={outline} activeContentId={activeContentId} />
                </div>
              </aside>

              <article className="min-w-0 space-y-6">
                {error && (
                  <div className="rounded-lg border border-danger bg-danger-wash p-4 text-danger-text">
                    {error}
                  </div>
                )}

                {!activeContentId ? (
                  <section className="rounded-lg border border-rule bg-surface p-6 md:p-8">
                    <p className="text-xs font-semibold uppercase tracking-wide text-accent-text">Start here</p>
                    <h2 className="mt-2 text-2xl font-bold text-fg">Welcome</h2>
                    {outline.description ? (
                      <div className="mt-4 whitespace-pre-wrap text-body leading-7">{outline.description}</div>
                    ) : (
                      <p className="mt-4 text-muted">Browse the course outline and start with the first exercise.</p>
                    )}
                    {firstExercise && (
                      <Link
                        href={`/learn/${outline.id}/content/${firstExercise.id}`}
                        className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent-hover"
                      >
                        Start with {firstExercise.title}
                      </Link>
                    )}
                  </section>
                ) : contentLoading ? (
                  <div className="rounded-lg border border-rule bg-surface p-10 text-center text-muted">
                    Loading content…
                  </div>
                ) : !content ? (
                  <EmptyState compact title="Course content unavailable" description={error ?? 'This item could not be loaded.'} />
                ) : (
                  <section className="rounded-lg border border-rule bg-surface p-6 md:p-8">
                    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                          {content.is_submittable ? 'Exercise' : 'Course material'}
                        </p>
                        <h2 className="mt-1 text-2xl font-bold text-fg">{content.title}</h2>
                      </div>
                      {content.available_languages.length > 1 && (
                        <div className="flex rounded-lg border border-rule-strong p-1" aria-label="Language">
                          {content.available_languages.map(language => (
                            <button
                              type="button"
                              key={language}
                              onClick={() => setRequestedLanguage(language)}
                              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                                (requestedLanguage ?? content.selected_language) === language
                                  ? 'bg-accent text-on-accent'
                                  : 'text-muted hover:bg-sunken'
                              }`}
                            >
                              {LANGUAGE_LABEL[language] ?? language.toUpperCase()}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    {content.markdown ? (
                      <PublicMarkdown assetBaseUrl={content.asset_base_url} mediaFiles={content.media_files} markdown={content.markdown} />
                    ) : content.description ? (
                      <p className="whitespace-pre-wrap leading-7 text-body">{content.description}</p>
                    ) : (
                      <EmptyState compact title="No learner-facing description is available for this item." />
                    )}
                  </section>
                )}

                {activeContentId && (
                  <nav aria-label="Exercise navigation" className="flex items-center justify-between gap-4">
                    <div>
                      {previous && (
                        <Link href={`/learn/${outline.id}/content/${previous.id}`} className="text-sm text-accent-text hover:underline">
                          ← {previous.title}
                        </Link>
                      )}
                    </div>
                    <div className="text-right">
                      {next && (
                        <Link href={`/learn/${outline.id}/content/${next.id}`} className="text-sm text-accent-text hover:underline">
                          {next.title} →
                        </Link>
                      )}
                    </div>
                  </nav>
                )}

                <ReaderActions signedIn={Boolean(user)} />

                <details className="text-sm text-muted">
                  <summary className="cursor-pointer hover:text-fg">Source, license and reuse</summary>
                  <p className="mt-2">
                    The learner-facing source mirror is available on{' '}
                    <a href={PUBLIC_COURSES_URL} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">
                      GitHub
                    </a>
                    . Published material retains its{' '}
                    <a href="/learning/LICENSE.txt" target="_blank" rel="noreferrer" className="text-accent-text hover:underline">
                      MIT copyright and permission notice
                    </a>
                    .
                  </p>
                </details>
              </article>
            </div>
          </>
        )}
      </div>
    </PublicLearnShell>
  );
}
