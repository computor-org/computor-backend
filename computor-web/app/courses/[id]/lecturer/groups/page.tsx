'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import type { CourseGroupList } from 'types/generated';
import { Table, Thead, Tbody, Th } from '@/src/components/ui/Table';
import { fetchCourseRoster } from '@/src/components/course-members/roster';

const groupsClient = new CourseGroupsClient();
const membersClient = new CourseMembersClient();

export default function CourseGroupsPage() {
  const courseId = useParams().id as string;
  const crumbs = useCourseCrumbs(courseId, 'Course groups');
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [actionError, setActionError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<CourseGroupList | null>(null);

  const { data, loading, error, reload } = useResource(
    async () => {
      const [groups, members] = await Promise.all([
        groupsClient.listCourseGroupsCourseGroupsGet({ courseId, limit: 500 }),
        // Member counts drive whether a group can be deleted (the FK is RESTRICT).
        fetchCourseRoster(membersClient, courseId),
      ]);
      return { groups, members };
    },
    [courseId],
    { enabled: canManage },
  );

  const groups = data?.groups ?? [];
  const memberCount = useMemo(() => {
    const map = new Map<string, number>();
    for (const m of data?.members ?? []) {
      if (m.course_group_id) map.set(m.course_group_id, (map.get(m.course_group_id) ?? 0) + 1);
    }
    return map;
  }, [data?.members]);

  async function deleteGroup(group: CourseGroupList) {
    setActionError(null);
    try {
      await groupsClient.deleteCourseGroupsCourseGroupsIdDelete({ id: group.id });
      setToDelete(null);
      await reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to delete group');
      setToDelete(null);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden
        message="You need lecturer access (or higher) on this course to manage its groups."
        backLink={`/courses/${courseId}`}
        backText="Back to course"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title="Course groups"
          subtitle="Groups (lab sections, tutorial cohorts) students are assigned to. Every student must belong to a group."
          actions={
            <Link
              href={`/courses/${courseId}/lecturer/groups/create`}
              className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover"
            >
              New group
            </Link>
          }
        />

        <ErrorBanner>{error || actionError}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading groups…</ListLoading>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <tr>
                  <Th>Group</Th>
                  <Th>Members</Th>
                  <th className="px-4 py-3" />
                </tr>
              </Thead>
              <Tbody>
                {groups.map((g) => {
                  const count = memberCount.get(g.id) ?? 0;
                  return (
                    <tr key={g.id} className="hover:bg-canvas">
                      <td className="px-4 py-3">
                        <Link
                          href={`/courses/${courseId}/lecturer/groups/${g.id}/edit`}
                          className="font-medium text-fg text-sm hover:text-accent-text"
                        >
                          {g.title || 'Untitled group'}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted">{count}</td>
                      <td className="px-4 py-3 text-right space-x-4">
                        <Link
                          href={`/courses/${courseId}/lecturer/groups/${g.id}/edit`}
                          className="text-sm text-accent-text hover:underline"
                        >
                          Edit
                        </Link>
                        {count === 0 ? (
                          <button
                            onClick={() => setToDelete(g)}
                            className="text-sm text-danger-text hover:underline"
                          >
                            Delete
                          </button>
                        ) : (
                          <span
                            className="text-sm text-faint cursor-not-allowed"
                            title="Reassign this group's members before deleting it."
                          >
                            Delete
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {groups.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-sm text-muted">
                      No groups yet. Create one so students can be assigned to it.
                    </td>
                  </tr>
                )}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}
      </ListPageLayout>

      {toDelete && (
        <ConfirmDeleteDialog
          title="Delete group"
          message={`Delete the group "${toDelete.title || 'Untitled group'}"? This cannot be undone.`}
          confirmWord={toDelete.title || 'Untitled group'}
          onConfirm={() => deleteGroup(toDelete)}
          onClose={() => setToDelete(null)}
        />
      )}
    </AuthenticatedLayout>
  );
}
