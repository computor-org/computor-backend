'use client';

import { useMemo } from 'react';
import { useParams } from 'next/navigation';
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
import Toolbar from '@/src/components/ui/Toolbar';
import TreeRow, { TreeRows } from '@/src/components/ui/TreeRow';
import { formatUsageCompact } from '@/src/utils/limits';
import type { CourseContentStudentList } from 'types/generated';

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
  const crumbs = useCourseCrumbs(courseId, 'Assignments');

  const { data, loading, error } = useResource(async () => {
    const response = await apiFetch(`${API_BASE_URL}/students/course-contents?course_id=${courseId}`);
    if (!response.ok) throw new Error('Failed to fetch course contents');
    return (await response.json()) as CourseContentStudentList[];
  }, [courseId]);
  const courseContents = useMemo(() => data ?? [], [data]);

  // synthesiseContainers: a student is served the assignments they can see, so a
  // unit that is itself hidden leaves its children with no parent row. Inventing
  // the container keeps the structure legible instead of flattening the tree.
  const { rows, setAllExpanded } = useContentTree(courseContents, { synthesiseContainers: true });

  const units = courseContents.filter((c) => c.course_content_kind_id === 'unit').length;
  const assignments = courseContents.filter((c) => c.course_content_kind_id === 'assignment').length;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title="Assignments"
          subtitle={loading ? undefined : `${units} units · ${assignments} assignments`}
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
                title="No assignments yet"
                description="Assignments will appear here once they are published by your instructor."
              />
            ) : (
              <>
                <Toolbar>
                  <Button variant="ghost" size="sm" onClick={() => setAllExpanded(false)}>
                    Collapse all
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setAllExpanded(true)}>
                    Expand all
                  </Button>
                </Toolbar>

                <TreeRows>
                  {rows.map(({ key, item, depth, label, expanded, hasChildren, toggle, childCount }) => {
                    const isAssignment = item?.course_content_kind_id === 'assignment';

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
                          <Badge tone="muted" className="shrink-0">
                            {childCount} {childCount === 1 ? 'item' : 'items'}
                          </Badge>
                        )}

                        {item && isAssignment && (
                          <>
                            {item.submitted ? (
                              <Badge tone="success" className="shrink-0">
                                Submitted
                              </Badge>
                            ) : (
                              <Badge tone="warning" className="shrink-0">
                                Not submitted
                              </Badge>
                            )}

                            <Badge
                              tone="muted"
                              className="shrink-0 tabular-nums"
                              title="Test runs and submissions used, against your budget"
                            >
                              {formatUsageCompact(item.result_count, item.max_test_runs)}T /{' '}
                              {formatUsageCompact(item.submission_count, item.max_submissions)}S
                            </Badge>

                            <span className="shrink-0 w-14 text-right">
                              <Score value={item.result ? (item.result.result ?? 0) : null} />
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
                            Open
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
