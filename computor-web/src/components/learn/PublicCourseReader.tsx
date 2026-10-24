'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import {
  CODESPACES_URL,
  COMPUTOR_EXTENSION_URL,
  PUBLIC_COURSES_URL,
} from '@/src/components/courses/LearningOptions';
import EmptyState from '@/src/components/EmptyState';
import PublicLearnShell from '@/src/components/learn/PublicLearnShell';
import PublicMarkdown, { PublicMarkdownTitle } from '@/src/components/learn/PublicMarkdown';
import { localizedTitle } from '@/src/components/learn/localize';
import { setUiLanguage, useBrowserLanguage, type UiLanguage } from '@/src/hooks/useBrowserLanguage';
import type {
  PublicLearningContent,
  PublicLearningContentSummary,
  PublicLearningCourseOutline,
} from '@/src/types/publicLearning';

const LANGUAGE_LABEL: Record<string, string> = {
  de: 'Deutsch',
  en: 'English',
};

const COPY = {
  de: {
    outline: 'Kursübersicht',
    welcomeLink: 'Willkommen',
    practiseTitle: 'Selbst an den Aufgaben arbeiten?',
    catalog: 'Zum Kurskatalog',
    signIn: 'Anmelden und beitreten',
    notFound: 'Kurs nicht gefunden.',
    loadFailed: 'Der Kurs konnte nicht geladen werden.',
    loadingCourse: 'Kurs wird geladen…',
    unavailable: 'Kurs nicht verfügbar',
    courses: 'Kurse',
    counts: (units: number, exercises: number) => `${units} Wochen · ${exercises} Aufgaben`,
    startHere: 'Hier beginnen',
    welcome: 'Willkommen',
    noWelcome: 'Wähle links eine Aufgabe oder beginne mit der ersten.',
    startWith: (title: ReactNode) => <>Mit „{title}“ beginnen</>,
    loadingContent: 'Inhalt wird geladen…',
    contentUnavailable: 'Inhalt nicht verfügbar',
    itemFailed: 'Dieser Inhalt konnte nicht geladen werden.',
    exercise: 'Aufgabe',
    material: 'Kursmaterial',
    language: 'Sprache',
    noDescription: 'Für diesen Inhalt gibt es keine Beschreibung.',
    navigation: 'Aufgabennavigation',
    sourceTitle: 'Quelle, Lizenz und Weiterverwendung',
    source: <>Die Kursmaterialien liegen auf{' '}<a href={PUBLIC_COURSES_URL} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">GitHub</a>. Veröffentlichte Materialien stehen unter der{' '}<a href="/learning/LICENSE.txt" target="_blank" rel="noreferrer" className="text-accent-text hover:underline">MIT-Lizenz</a>.</>,
  },
  en: {
    outline: 'Course outline',
    welcomeLink: 'Welcome',
    practiseTitle: 'Want to work on the exercises?',
    catalog: 'Open the course catalog',
    signIn: 'Sign in to join',
    notFound: 'Course not found.',
    loadFailed: 'Could not load this course.',
    loadingCourse: 'Loading course…',
    unavailable: 'Course unavailable',
    courses: 'Courses',
    counts: (units: number, exercises: number) => `${units} weeks · ${exercises} exercises`,
    startHere: 'Start here',
    welcome: 'Welcome',
    noWelcome: 'Pick an exercise on the left or start with the first one.',
    startWith: (title: ReactNode) => <>Start with {title}</>,
    loadingContent: 'Loading content…',
    contentUnavailable: 'Course content unavailable',
    itemFailed: 'This item could not be loaded.',
    exercise: 'Exercise',
    material: 'Course material',
    language: 'Language',
    noDescription: 'No description is available for this item.',
    navigation: 'Exercise navigation',
    sourceTitle: 'Source, license and reuse',
    source: <>The course material is on{' '}<a href={PUBLIC_COURSES_URL} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">GitHub</a>. Published material is under the{' '}<a href="/learning/LICENSE.txt" target="_blank" rel="noreferrer" className="text-accent-text hover:underline">MIT license</a>.</>,
  },
};

type Copy = (typeof COPY)[UiLanguage];

/** Drop the leading Markdown heading; the page shows it as the item title. */
function withoutTitleHeading(markdown: string): string {
  return markdown.replace(/^(\s*(?:\[[^\]\r\n]+\]:[^\r\n]*(?:\r?\n|$)\s*)*)#\s+[^\r\n]*(?:\r?\n|$)/, '$1');
}

function LanguageSwitch({ content, label }: { content: PublicLearningContent; label: string }) {
  if (content.available_languages.length < 2) return null;
  return (
    <div className="flex rounded-lg border border-rule-strong p-1" aria-label={label}>
      {content.available_languages.map(language => (
        <button
          type="button"
          key={language}
          onClick={() => setUiLanguage(language as UiLanguage)}
          className={`rounded-md px-3 py-1.5 text-xs font-medium ${
            content.selected_language === language
              ? 'bg-accent text-on-accent'
              : 'text-muted hover:bg-sunken'
          }`}
        >
          {LANGUAGE_LABEL[language] ?? language.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function OutlineLinks({
  outline,
  activeContentId,
  language,
  t,
}: {
  outline: PublicLearningCourseOutline;
  activeContentId?: string;
  language: UiLanguage;
  t: Copy;
}) {
  return (
    <nav aria-label={t.outline} className="space-y-0.5">
      <Link
        href={`/learn/${outline.id}`}
        className={`block rounded-md px-3 py-2 text-sm font-medium ${
          !activeContentId || activeContentId === outline.welcome_content_id
            ? 'bg-accent-wash text-accent-text'
            : 'text-body hover:bg-sunken'
        }`}
      >
        {t.welcomeLink}
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
          <span className="block truncate"><PublicMarkdownTitle markdown={localizedTitle(outline, item.id, item.title, language)} /></span>
        </Link>
      ))}
    </nav>
  );
}

function ReaderActions({ signedIn, t }: { signedIn: boolean; t: Copy }) {
  const computorHref = signedIn
    ? '/courses/catalog'
    : `/login?next=${encodeURIComponent('/courses/catalog')}`;
  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <p className="text-sm font-semibold text-fg">{t.practiseTitle}</p>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm">
        <Link href={computorHref} className="text-accent-text hover:underline">
          {signedIn ? t.catalog : t.signIn}
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
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [loaded, setLoaded] = useState<{
    courseId: string; outline: PublicLearningCourseOutline | null; error: string | null;
  } | null>(null);
  const uiLanguage = useBrowserLanguage();
  const t = COPY[uiLanguage];
  const outline = loaded?.courseId === courseId ? loaded.outline : null;
  const outlineLoading = loaded?.courseId !== courseId;
  const errorCode = loaded?.courseId === courseId ? loaded.error : null;
  const error = errorCode === 'not-found' ? t.notFound : errorCode ? t.loadFailed : null;
  const contentLoading = false;

  useEffect(() => {
    let cancelled = false;
    fetch(`/learning/courses/${encodeURIComponent(courseId)}.json`, { credentials: 'omit' })
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 404 ? 'not-found' : 'load-failed');
        return response.json() as Promise<PublicLearningCourseOutline>;
      })
      .then(data => {
        if (!cancelled) setLoaded({ courseId, outline: data, error: null });
      })
      .catch(err => {
        if (!cancelled) setLoaded({ courseId, outline: null, error: err instanceof Error && err.message === 'not-found' ? 'not-found' : 'load-failed' });
      });
    return () => { cancelled = true; };
  }, [courseId]);

  const activeContentId = contentId ?? outline?.welcome_content_id ?? undefined;

  const material = activeContentId && outline && Object.hasOwn(outline.materials, activeContentId)
    ? outline.materials[activeContentId] : undefined;
  const activeItem = outline?.contents.find(item => item.id === activeContentId);
  const authenticatedReader = Boolean(user);
  const nativeCoursePath = outline?.course_path;
  const validCoursePath = typeof nativeCoursePath === 'string'
    && /^[a-z0-9_]+(?:\.[a-z0-9_]+)*$/.test(nativeCoursePath);
  const validItemPath = activeItem && material
    && /^[a-z0-9_]+(?:\.[a-z0-9_]+)*$/.test(activeItem.path)
    && material.path === activeItem.path;
  const hasAuthoredContent = activeItem?.is_submittable || Boolean(material?.description?.trim())
    || Object.values(material?.markdown_variants ?? {}).some(text => Boolean(text.trim()));
  const handoffTarget = authenticatedReader && outline && validCoursePath
    && (!contentId || validItemPath)
    ? `/courses/catalog?${new URLSearchParams({ join: nativeCoursePath,
      ...(validItemPath && hasAuthoredContent ? { contentPath: activeItem.path } : {}) })}`
    : null;

  useEffect(() => {
    if (!authLoading && handoffTarget) router.replace(handoffTarget);
  }, [authLoading, handoffTarget, router]);

  const languages = Object.keys(material?.markdown_variants ?? {});
  const language = [uiLanguage, outline?.language_code, 'en', 'de']
    .find(value => value && languages.includes(value)) ?? languages[0];
  const content: PublicLearningContent | null = material ? {
    ...material, markdown: withoutTitleHeading(material.markdown_variants[language ?? ''] ?? ''),
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
        {outlineLoading || authLoading || (!authLoading && Boolean(handoffTarget)) ? (
          <div className="py-24 text-center text-muted">{t.loadingCourse}</div>
        ) : authenticatedReader && outline ? (
          <EmptyState title={t.contentUnavailable} description={t.itemFailed} />
        ) : !outline ? (
          <EmptyState title={t.unavailable} description={error ?? t.loadFailed} />
        ) : (
          <>
            <div className="mb-6">
              <div className="text-sm text-muted">
                <Link href="/learn" className="text-accent-text hover:underline">{t.courses}</Link>
                <span className="mx-2">/</span>
                <span>{outline.title}</span>
              </div>
              <h1 className="mt-2 text-3xl font-bold text-fg">{outline.title}</h1>
              <p className="mt-2 text-sm text-muted">
                {t.counts(outline.unit_count, outline.exercise_count)}
                {outline.language_code ? ` · ${outline.language_code.toUpperCase()}` : ''}
              </p>
            </div>

            <details className="md:hidden mb-5 rounded-lg border border-rule bg-surface p-3">
              <summary className="cursor-pointer font-medium">{t.outline}</summary>
              <div className="mt-3 max-h-[55vh] overflow-y-auto">
                <OutlineLinks outline={outline} activeContentId={activeContentId} language={uiLanguage} t={t} />
              </div>
            </details>

            <div className="grid gap-8 md:grid-cols-[18rem_minmax(0,1fr)]">
              <aside className="hidden md:block">
                <div className="sticky top-20 max-h-[calc(100vh-7rem)] overflow-y-auto rounded-lg border border-rule bg-surface p-3 scroll-slim">
                  <OutlineLinks outline={outline} activeContentId={activeContentId} language={uiLanguage} t={t} />
                </div>
              </aside>

              <article className="min-w-0 space-y-6">
                {error && (
                  <div className="rounded-lg border border-danger bg-danger-wash p-4 text-danger-text">
                    {error}
                  </div>
                )}

                {!contentId ? (
                  <section className="rounded-lg border border-rule bg-surface p-6 md:p-8">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-accent-text">{t.startHere}</p>
                        <h2 className="mt-2 text-2xl font-bold text-fg">{t.welcome}</h2>
                      </div>
                      {content && <LanguageSwitch content={content} label={t.language} />}
                    </div>
                    {content?.markdown ? (
                      <div className="mt-4">
                        <PublicMarkdown assetBaseUrl={content.asset_base_url} mediaFiles={content.media_files} markdown={content.markdown} />
                      </div>
                    ) : outline.description ? (
                      <div className="mt-4 whitespace-pre-wrap text-body leading-7">{outline.description}</div>
                    ) : (
                      <p className="mt-4 text-muted">{t.noWelcome}</p>
                    )}
                    {firstExercise && (
                      <Link
                        href={`/learn/${outline.id}/content/${firstExercise.id}`}
                        className="mt-6 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent-hover"
                      >
                        {t.startWith(<PublicMarkdownTitle markdown={localizedTitle(outline, firstExercise.id, firstExercise.title, uiLanguage)} />)}
                      </Link>
                    )}
                  </section>
                ) : contentLoading ? (
                  <div className="rounded-lg border border-rule bg-surface p-10 text-center text-muted">
                    {t.loadingContent}
                  </div>
                ) : !content ? (
                  <EmptyState compact title={t.contentUnavailable} description={error ?? t.itemFailed} />
                ) : (
                  <section className="rounded-lg border border-rule bg-surface p-6 md:p-8">
                    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                          {content.is_submittable ? t.exercise : t.material}
                        </p>
                        <h2 className="mt-1 text-2xl font-bold text-fg"><PublicMarkdownTitle markdown={localizedTitle(outline, content.id, content.title, (content.selected_language ?? uiLanguage) as UiLanguage)} /></h2>
                      </div>
                      <LanguageSwitch content={content} label={t.language} />
                    </div>
                    {content.markdown ? (
                      <PublicMarkdown assetBaseUrl={content.asset_base_url} mediaFiles={content.media_files} markdown={content.markdown} />
                    ) : content.description ? (
                      <p className="whitespace-pre-wrap leading-7 text-body">{content.description}</p>
                    ) : (
                      <EmptyState compact title={t.noDescription} />
                    )}
                  </section>
                )}

                {activeContentId && (
                  <nav aria-label={t.navigation} className="flex items-center justify-between gap-4">
                    <div>
                      {previous && (
                        <Link href={`/learn/${outline.id}/content/${previous.id}`} className="text-sm text-accent-text hover:underline">
                          ← <PublicMarkdownTitle markdown={localizedTitle(outline, previous.id, previous.title, uiLanguage)} />
                        </Link>
                      )}
                    </div>
                    <div className="text-right">
                      {next && (
                        <Link href={`/learn/${outline.id}/content/${next.id}`} className="text-sm text-accent-text hover:underline">
                          <PublicMarkdownTitle markdown={localizedTitle(outline, next.id, next.title, uiLanguage)} /> →
                        </Link>
                      )}
                    </div>
                  </nav>
                )}

                <ReaderActions signedIn={Boolean(user)} t={t} />

                <details className="text-sm text-muted">
                  <summary className="cursor-pointer hover:text-fg">{t.sourceTitle}</summary>
                  <p className="mt-2">{t.source}</p>
                </details>
              </article>
            </div>
          </>
        )}
      </div>
    </PublicLearnShell>
  );
}
