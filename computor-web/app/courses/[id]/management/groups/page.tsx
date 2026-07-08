'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import type { CourseGroupList } from 'types/generated';
import { Table, Thead, Tbody, Th } from '@/src/components/ui/Table';

const groupsClient = new CourseGroupsClient();
const membersClient = new CourseMembersClient();
const coursesClient = new CoursesClient();

export default function CourseGroupsPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [actionError, setActionError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<CourseGroupList | null>(null);

  const { data, loading, error, reload } = useResource(
    async () => {
      const [groups, members, course] = await Promise.all([
        groupsClient.listCourseGroupsCourseGroupsGet({ courseId, limit: 500 }),
        // Member counts drive whether a group can be deleted (the FK is RESTRICT).
        membersClient.listCourseMembersCourseMembersGet({ courseId, limit: 2000 }),
        coursesClient.getCoursesCoursesIdGet({ id: courseId }).catch(() => null),
      ]);
      return { groups, members, course };
    },
    [courseId],
    { enabled: canManage },
  );

  const groups = data?.groups ?? [];
  const course = data?.course ?? null;
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

  const courseLabel = course?.title || course?.path || 'Course';

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: courseLabel, href: `/courses/${courseId}` },
            { label: 'Course Groups' },
          ]}
          title="Course Groups"
          subtitle="Groups (lab sections, tutorial cohorts) students are assigned to. Every student must belong to a group."
          actions={
            <Link
              href={`/courses/${courseId}/management/groups/create`}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
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
                    <tr key={g.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <Link
                          href={`/courses/${courseId}/management/groups/${g.id}/edit`}
                          className="font-medium text-gray-900 text-sm hover:text-blue-600"
                        >
                          {g.title || g.id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{count}</td>
                      <td className="px-4 py-3 text-right space-x-4">
                        <Link
                          href={`/courses/${courseId}/management/groups/${g.id}/edit`}
                          className="text-sm text-blue-600 hover:underline"
                        >
                          Edit
                        </Link>
                        {count === 0 ? (
                          <button
                            onClick={() => setToDelete(g)}
                            className="text-sm text-red-600 hover:underline"
                          >
                            Delete
                          </button>
                        ) : (
                          <span
                            className="text-sm text-gray-300 cursor-not-allowed"
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
                    <td colSpan={3} className="px-4 py-8 text-center text-sm text-gray-500">
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
          message={`Delete the group "${toDelete.title || toDelete.id}"? This cannot be undone.`}
          confirmWord={toDelete.title || toDelete.id}
          onConfirm={() => deleteGroup(toDelete)}
          onClose={() => setToDelete(null)}
        />
      )}
    </AuthenticatedLayout>
  );
}
