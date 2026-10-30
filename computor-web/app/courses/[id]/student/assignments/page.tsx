'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import CourseWorkspaceLaunchButtons from '@/src/components/workspaces/CourseWorkspaceLaunchButtons';
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
import { courseProgress, STUDENT_CONTENTS_REFRESH_MS } from '@/src/utils/studentProgress';
import { CourseProgressSummary } from '@/src/components/student/CourseProgress';
import {
  ASSIGNMENT_STATES, ASSIGNMENT_STATE_COLOR, assignmentState, assignmentStateLabel, unitState,
} from '@/src/utils/assignmentStatus';
import type { CourseContentStudentList } from 'types/generated';

const COPY = {
  de: {
    title: 'Aufgaben',
    workspaces: 'Arbeitsumgebungen',
    fetchFailed: 'Kursinhalte konnten nicht geladen werden',
    subtitle: (units: number, assignments: number, weekly: boolean) =>
      `${units} ${weekly ? (units === 1 ? 'Woche' : 'Wochen') : (units === 1 ? 'Einheit' : 'Einheiten')} · ${assignments} ${assignments === 1 ? 'Aufgabe' : 'Aufgaben'}`,
    emptyTitle: 'Noch keine Aufgaben',
    emptyDescription: 'Aufgaben erscheinen hier, sobald deine Lehrenden sie veröffentlichen.',
    collapseAll: 'Alle einklappen',
    expandAll: 'Alle ausklappen',
    assignments: (n: number) => (n === 1 ? '1 Aufgabe' : `${n} Aufgaben`),
    items: (n: number) => (n === 1 ? '1 Element' : `${n} Elemente`),
    unitProgress: (s: number, n: number) => `${s}/${n} eingereicht`,
    unitProgressTitle: (s: number, n: number, weekly: boolean) => `${s} von ${n} Aufgaben ${weekly ? 'dieser Woche' : 'dieser Einheit'} eingereicht`,
    submitted: 'Eingereicht',
    notSubmitted: 'Nicht eingereicht',
    usageTitle: 'T: Testläufe, A: Abgaben, jeweils verbraucht im Verhältnis zum Kontingent',
    testsSuffix: 'T',
    submissionsSuffix: 'A',
    latestResult: 'Letztes Testergebnis',
    grade: 'Bewertung',
    open: 'Öffnen',
    results: 'Ergebnisse',
    targetUnavailable: 'Dieser Inhalt ist in diesem Kurs nicht verfügbar.',
    legend: 'Legende',
  },
  en: {
    title: 'Assignments',
    workspaces: 'Workspaces',
    fetchFailed: 'Failed to fetch course contents',
    subtitle: (units: number, assignments: number, weekly: boolean) =>
      `${units} ${weekly ? (units === 1 ? 'week' : 'weeks') : (units === 1 ? 'unit' : 'units')} · ${assignments} ${assignments === 1 ? 'assignment' : 'assignments'}`,
    emptyTitle: 'No assignments yet',
    emptyDescription: 'Assignments will appear here once they are published by your instructor.',
    collapseAll: 'Collapse all',
    expandAll: 'Expand all',
    assignments: (n: number) => `${n} ${n === 1 ? 'assignment' : 'assignments'}`,
    items: (n: number) => `${n} ${n === 1 ? 'item' : 'items'}`,
    unitProgress: (s: number, n: number) => `${s}/${n} submitted`,
    unitProgressTitle: (s: number, n: number, weekly: boolean) => `${s} of ${n} assignments in this ${weekly ? 'week' : 'unit'} submitted`,
    submitted: 'Submitted',
    notSubmitted: 'Not submitted',
    usageTitle: 'T: test runs, S: submissions, each used against the budget',
    testsSuffix: 'T',
    submissionsSuffix: 'S',
    latestResult: 'Latest test result',
    grade: 'Grade',
    open: 'Open',
    results: 'Results',
    targetUnavailable: 'This content is not available in this course.',
    legend: 'Legend',
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
  const requestedPaths = useSearchParams().getAll('contentPath');
  const crumbs = useCourseCrumbs(courseId, t.title);
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();
  const isOrdinaryLearner = !isAdmin && !isOrganizationManager &&
    courseHasAtLeast(courseId, '_student') && !courseHasAtLeast(courseId, '_tutor');

  const { data, loading, error } = useResource(async () => {
    const response = await apiFetch(`${API_BASE_URL}/students/course-contents?course_id=${courseId}&localize=${language}`);
    if (!response.ok) throw new Error(t.fetchFailed);
    return (await response.json()) as CourseContentStudentList[];
  }, [courseId, language], { refreshOnFocus: true, refetchInterval: STUDENT_CONTENTS_REFRESH_MS });
  const courseContents = useMemo(() => data ?? [], [data]);

  const progress = useMemo(() => courseProgress(courseContents), [courseContents]);
  const nextId = progress.next?.item.id;
  const nextPath = progress.next?.item.path;
  const nextGroups = useMemo(() => {
    const parts = nextPath?.split('.') ?? [];
    return parts.slice(0, -1).map((_, i) => parts.slice(0, i + 1).join('.'));
  }, [nextPath]);

  // Open the next task's groups initially; the learner can still toggle any unit.
  // Staff keep the existing full tree and its expand/collapse controls.
  const { rows, setAllExpanded } = useContentTree(courseContents, {
    synthesiseContainers: true,
    language,
    ...(isOrdinaryLearner ? { collapseBelowDepth: 0, defaultExpandedPaths: nextGroups } : {}),
  });
  const workspaceAction = isOrdinaryLearner ? (
    <CourseWorkspaceLaunchButtons courseId={courseId} courseContentId={progress.started ? nextId : undefined} />
  ) : undefined;

  const requestedTargets = requestedPaths.length === 1 && /^[a-z0-9_]+(\.[a-z0-9_]+)*$/.test(requestedPaths[0])
    ? courseContents.filter((item) => item.path === requestedPaths[0] && item.course_id === courseId && item.visible_effective !== false && ['unit', 'assignment'].includes(item.course_content_kind_id) &&
      (item.course_content_kind_id === 'assignment'
        ? Boolean(item.has_deployment || item.deployment)
        : Boolean(item.description?.trim() || item.has_deployment || item.deployment))) : [];
  const requestedTarget = requestedTargets.length === 1 ? requestedTargets[0] : null;
  const hasRequestedTarget = isOrdinaryLearner && requestedPaths.length > 0;

  const unitRows = courseContents.filter((c) => c.course_content_kind_id === 'unit');
  const units = unitRows.length;
  // A course whose units are all weeks says so, as /learn does for the same course.
  const weekly = units > 0 && unitRows.every((c) => c.course_content_type?.slug === 'weekly');
  const assignments = courseContents.filter((c) => c.course_content_kind_id === 'assignment').length;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={t.title}
          subtitle={loading ? undefined : t.subtitle(units, assignments, weekly)}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            {hasRequestedTarget ? (
              requestedTarget ? <CourseWorkspaceLaunchButtons courseId={courseId} courseContentId={requestedTarget.id} autoLaunch />
                : <ErrorBanner>{t.targetUnavailable}</ErrorBanner>
            ) : rows.length === 0 ? (
              <>
              {workspaceAction}
              <EmptyState
                icon={
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                }
                title={t.emptyTitle}
                description={t.emptyDescription}
              />
              </>
            ) : (
              <>
                <CourseProgressSummary
                  courseId={courseId} progress={progress} language={language} compact
                  workspaceAction={workspaceAction}
                />

                {!isOrdinaryLearner && <Toolbar>
                  <Button variant="ghost" size="sm" onClick={() => setAllExpanded(false)}>
                    {t.collapseAll}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setAllExpanded(true)}>
                    {t.expandAll}
                  </Button>
                </Toolbar>}

                <ul aria-label={t.legend} data-testid="status-legend" className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-subtle">
                  {ASSIGNMENT_STATES.map((state) => (
                    <li key={state} className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: ASSIGNMENT_STATE_COLOR[state] }} aria-hidden="true" />
                      {assignmentStateLabel(state, language)}
                    </li>
                  ))}
                </ul>

                <TreeRows>
                  {rows.map(({ key, item, depth, label, expanded, hasChildren, toggle, childCount }) => {
                    const isAssignment = item?.course_content_kind_id === 'assignment';
                    const isAuthoredContent = isAssignment || Boolean(item?.description?.trim() || item?.has_deployment || item?.deployment);
                    const unit = hasChildren ? progress.units.get(key) : undefined;
                    const hasResults = item && (item.result != null || item.submitted ||
                      item.submission_group?.grading != null || isGradingVerdict(item.status) || (item.unread_message_count ?? 0) > 0 ||
                      (item.result_count ?? 0) > 0 || (item.submission_count ?? 0) > 0);
                    const state = hasChildren ? unitState(unit) : isAssignment ? assignmentState(item) : undefined;

                    return (
                      <TreeRow
                        key={key}
                        depth={depth}
                        expandable={hasChildren}
                        expanded={expanded}
                        onToggle={toggle}
                        markerColor={state && ASSIGNMENT_STATE_COLOR[state]}
                        markerTitle={state && assignmentStateLabel(state, language)}
                        label={isOrdinaryLearner && hasChildren ? (
                          <button
                            type="button"
                            className="text-left hover:underline"
                            onClick={toggle}
                            aria-expanded={expanded}
                          >{label}</button>
                        ) : isOrdinaryLearner && isAuthoredContent && item ? (
                          // The title opens the task page, as on main; VS Code opens from there.
                          <Link href={`/courses/${courseId}/student/assignments/${item.id}`} className="hover:underline">
                            {label}
                          </Link>
                        ) : label}
                      >
                        {!isAssignment && hasChildren && (
                          unit && (!isOrdinaryLearner || unit.submitted > 0) ? (
                            <Badge
                              tone={unit.submitted === unit.total ? 'success' : 'muted'}
                              className="shrink-0 tabular-nums"
                              title={t.unitProgressTitle(unit.submitted, unit.total, weekly)}
                            >
                              {t.unitProgress(unit.submitted, unit.total)}
                            </Badge>
                          ) : (
                            <Badge tone="muted" className="shrink-0">
                              {/* A unit with no assignment below it has no progress entry, so its children are counted instead. */}
                              {unit ? t.assignments(unit.total) : t.items(childCount)}
                            </Badge>
                          )
                        )}

                        {item && isAssignment && (
                          <>
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
                            ) : isOrdinaryLearner ? null : (
                              <Badge tone="warning" className="shrink-0">
                                {t.notSubmitted}
                              </Badge>
                            )}

                            {/* Staff only: learners find the counts on the results page. */}
                            {!isOrdinaryLearner && <Badge
                              tone="muted"
                              className="shrink-0 tabular-nums"
                              title={t.usageTitle}
                            >
                              {formatUsageCompact(item.result_count, item.max_test_runs)}{t.testsSuffix} /{' '}
                              {formatUsageCompact(item.submission_count, item.max_submissions)}{t.submissionsSuffix}
                            </Badge>}

                            {/* Two numbers, always in the same two slots: what
                                the tests said, then what a human said. */}
                            {(!isOrdinaryLearner || item.result != null) && <span className="shrink-0 w-14 text-right" title={t.latestResult}>
                              <Score value={item.result ? (item.result.result ?? 0) : null} />
                            </span>}
                            {(!isOrdinaryLearner || item.submission_group?.grading != null) && <span className="shrink-0 w-14 text-right" title={t.grade}>
                              <Score value={item.submission_group?.grading ?? null} />
                            </span>}
                          </>
                        )}

                        {item && (!isOrdinaryLearner || (isAssignment && hasResults)) && (
                          <ButtonLink
                            href={`/courses/${courseId}/student/assignments/${item.id}`}
                            variant="ghost"
                            size="xs"
                            className="shrink-0"
                          >
                            {isOrdinaryLearner ? t.results : t.open}
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
