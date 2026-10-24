'use client';

import { useMemo } from 'react';
import { useParams } from 'next/navigation';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useContentTree } from '@/src/hooks/useContentTree';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Badge from '@/src/components/Badge';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import Score from '@/src/components/ui/Score';
import GradingStatusBadge, { isGradingVerdict } from '@/src/components/student/gradingStatus';
import Toolbar from '@/src/components/ui/Toolbar';
import TreeRow, { TreeRows } from '@/src/components/ui/TreeRow';
import { formatUsageCompact } from '@/src/utils/limits';
import { courseProgress } from '@/src/utils/studentProgress';
import { CourseProgressSummary } from '@/src/components/student/CourseProgress';
import type { CourseContentStudentList } from 'types/generated';

const COPY = {
  de: {
    title: 'Aufgaben',
    fetchFailed: 'Kursinhalte konnten nicht geladen werden',
    subtitle: (units: number, assignments: number) =>
      `${units} ${units === 1 ? 'Einheit' : 'Einheiten'} · ${assignments} ${assignments === 1 ? 'Aufgabe' : 'Aufgaben'}`,
    emptyTitle: 'Noch keine Aufgaben',
    emptyDescription: 'Aufgaben erscheinen hier, sobald deine Lehrenden sie veröffentlichen.',
    collapseAll: 'Alle einklappen',
    expandAll: 'Alle ausklappen',
    items: (n: number) => (n === 1 ? '1 Element' : `${n} Elemente`),
    unitProgress: (s: number, n: number) => `${s}/${n} eingereicht`,
    unitProgressTitle: (s: number, n: number) => `${s} von ${n} Aufgaben dieser Einheit eingereicht`,
    nextUp: 'Weiter hier',
    submitted: 'Eingereicht',
    notSubmitted: 'Nicht eingereicht',
    usageTitle: 'Testläufe und Abgaben im Verhältnis zu deinem Kontingent',
    testsSuffix: 'T',
    submissionsSuffix: 'A',
    latestResult: 'Letztes Testergebnis',
    grade: 'Bewertung',
    open: 'Öffnen',
  },
  en: {
    title: 'Assignments',
    fetchFailed: 'Failed to fetch course contents',
    subtitle: (units: number, assignments: number) => `${units} units · ${assignments} assignments`,
    emptyTitle: 'No assignments yet',
    emptyDescription: 'Assignments will appear here once they are published by your instructor.',
    collapseAll: 'Collapse all',
    expandAll: 'Expand all',
    items: (n: number) => `${n} ${n === 1 ? 'item' : 'items'}`,
    unitProgress: (s: number, n: number) => `${s}/${n} submitted`,
    unitProgressTitle: (s: number, n: number) => `${s} of ${n} assignments in this unit submitted`,
    nextUp: 'Next up',
    submitted: 'Submitted',
    notSubmitted: 'Not submitted',
    usageTitle: 'Test runs and submissions used, against your budget',
    testsSuffix: 'T',
    submissionsSuffix: 'S',
    latestResult: 'Latest test result',
    grade: 'Grade',
    open: 'Open',
  },
};

/**
 * A student's view of the course content tree.
 *
 * Same data and same shape as the lecturer's Assignments page, drawn by the same
 * hook and the same row: they had been two unrelated implementations, disagreeing
 * on indent, marker, row height, separator and what starts expanded, so the two
 * roles saw what looked like two different products of the same course.
 *
 * What legitimately differs is the row's right-hand side — a student gets status,
 * score and their remaining budget; a lecturer gets deployment and release
 * controls — and that is all that differs now.
 */
export default function StudentCourseContentsPage() {
  const courseId = useParams().id as string;
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, t.title);

  const { data, loading, error } = useResource(async () => {
    const response = await apiFetch(`${API_BASE_URL}/students/course-contents?course_id=${courseId}`);
    if (!response.ok) throw new Error(t.fetchFailed);
    return (await response.json()) as CourseContentStudentList[];
  }, [courseId]);
  const courseContents = useMemo(() => data ?? [], [data]);

  // synthesiseContainers: a student is served the assignments they can see, so a
  // unit that is itself hidden leaves its children with no parent row. Inventing
  // the container keeps the structure legible instead of flattening the tree.
  const { rows, setAllExpanded } = useContentTree(courseContents, { synthesiseContainers: true });

  const progress = useMemo(() => courseProgress(courseContents), [courseContents]);
  const nextId = progress.next?.item.id;

  const units = courseContents.filter((c) => c.course_content_kind_id === 'unit').length;
  const assignments = courseContents.filter((c) => c.course_content_kind_id === 'assignment').length;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={t.title}
          subtitle={loading ? undefined : t.subtitle(units, assignments)}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            {rows.length === 0 ? (
              <EmptyState
                icon={
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                }
                title={t.emptyTitle}
                description={t.emptyDescription}
              />
            ) : (
              <>
                <CourseProgressSummary courseId={courseId} progress={progress} language={language} compact />

                <Toolbar>
                  <Button variant="ghost" size="sm" onClick={() => setAllExpanded(false)}>
                    {t.collapseAll}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setAllExpanded(true)}>
                    {t.expandAll}
                  </Button>
                </Toolbar>

                <TreeRows>
                  {rows.map(({ key, item, depth, label, expanded, hasChildren, toggle, childCount }) => {
                    const isAssignment = item?.course_content_kind_id === 'assignment';
                    const unit = hasChildren ? progress.units.get(key) : undefined;

                    return (
                      <TreeRow
                        key={key}
                        depth={depth}
                        expandable={hasChildren}
                        expanded={expanded}
                        onToggle={toggle}
                        markerColor={item?.color}
                        markerTitle={item?.course_content_type?.slug}
                        label={label}
                      >
                        {!isAssignment && hasChildren && (
                          unit ? (
                            <Badge
                              tone={unit.submitted === unit.total ? 'success' : 'muted'}
                              className="shrink-0 tabular-nums"
                              title={t.unitProgressTitle(unit.submitted, unit.total)}
                            >
                              {t.unitProgress(unit.submitted, unit.total)}
                            </Badge>
                          ) : (
                            <Badge tone="muted" className="shrink-0">
                              {t.items(childCount)}
                            </Badge>
                          )
                        )}

                        {item && isAssignment && (
                          <>
                            {item.id === nextId && (
                              <Badge tone="info" className="shrink-0">
                                {t.nextUp}
                              </Badge>
                            )}

                            {/* Only a verdict a human reached. `not_reviewed` is
                                the default state of most of a semester, and a
                                grey chip on every row of 72 would say nothing. */}
                            {isGradingVerdict(item.status) && (
                              <GradingStatusBadge status={item.status} language={language} className="shrink-0" />
                            )}

                            {item.submitted ? (
                              <Badge tone="success" className="shrink-0">
                                {t.submitted}
                              </Badge>
                            ) : (
                              <Badge tone="warning" className="shrink-0">
                                {t.notSubmitted}
                              </Badge>
                            )}

                            <Badge
                              tone="muted"
                              className="shrink-0 tabular-nums"
                              title={t.usageTitle}
                            >
                              {formatUsageCompact(item.result_count, item.max_test_runs)}{t.testsSuffix} /{' '}
                              {formatUsageCompact(item.submission_count, item.max_submissions)}{t.submissionsSuffix}
                            </Badge>

                            {/* Two numbers, always in the same two slots: what
                                the tests said, then what a human said. */}
                            <span className="shrink-0 w-14 text-right" title={t.latestResult}>
                              <Score value={item.result ? (item.result.result ?? 0) : null} />
                            </span>
                            <span className="shrink-0 w-14 text-right" title={t.grade}>
                              <Score value={item.submission_group?.grading ?? null} />
                            </span>
                          </>
                        )}

                        {item && (
                          <ButtonLink
                            href={`/courses/${courseId}/student/assignments/${item.id}`}
                            variant="ghost"
                            size="xs"
                            className="shrink-0"
                          >
                            {t.open}
                          </ButtonLink>
                        )}
                      </TreeRow>
                    );
                  })}
                </TreeRows>
              </>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
