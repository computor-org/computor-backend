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
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import type { CourseMemberList, CourseGroupList } from 'types/generated';
import { Table, Thead, Tbody, Th } from '@/src/components/ui/Table';
import {
  assignableRoles,
  canManageMemberRole,
  courseRoleLabel,
  highestCourseRole,
  maxAssignableRole,
} from '@/src/utils/courseRoles';

const PAGE_SIZE = 25;
const membersClient = new CourseMembersClient();
const groupsClient = new CourseGroupsClient();
const coursesClient = new CoursesClient();

function memberName(m: CourseMemberList): string {
  const name = `${m.user?.given_name ?? ''} ${m.user?.family_name ?? ''}`.trim();
  return name || m.user?.email || m.user_id;
}

export default function CourseMembersPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const { isAdmin, isOrganizationManager, courseRoles, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');
  const ceiling = isAdmin || isOrganizationManager ? '_owner' : highestCourseRole(courseRoles[courseId]);
  // Roles this user may grant (lecturers capped at _student); `ceiling` itself
  // still governs which existing members they may edit/remove below.
  const roleOptions = assignableRoles(maxAssignableRole(ceiling));

  const [page, setPage] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [toRemove, setToRemove] = useState<CourseMemberList | null>(null);

  const { data, loading, error, reload } = useResource(
    async () => {
      const [members, groups, course] = await Promise.all([
        membersClient.listCourseMembersCourseMembersGet({
          courseId,
          skip: page * PAGE_SIZE,
          limit: PAGE_SIZE,
        }),
        groupsClient
          .listCourseGroupsCourseGroupsGet({ courseId, limit: 200 })
          .catch(() => [] as CourseGroupList[]),
        coursesClient.getCoursesCoursesIdGet({ id: courseId }).catch(() => null),
      ]);
      return { members, groups, course };
    },
    [courseId, page],
    { enabled: canManage },
  );

  const members = data?.members ?? [];
  const course = data?.course ?? null;
  const groups = data?.groups ?? [];
  const groupName = useMemo(() => {
    const map = new Map<string, string>();
    for (const g of data?.groups ?? []) map.set(g.id, g.title || g.id);
    return map;
  }, [data?.groups]);

  const hasNext = members.length === PAGE_SIZE;

  async function changeRole(member: CourseMemberList, role: string) {
    if (role === member.course_role_id) return;
    setSavingId(member.id);
    setActionError(null);
    try {
      await membersClient.updateCourseMembersCourseMembersIdPatch({
        id: member.id,
        body: { course_role_id: role },
      });
      await reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to change role');
    } finally {
      setSavingId(null);
    }
  }

  async function changeGroup(member: CourseMemberList, groupId: string) {
    const next = groupId || null;
    if (next === (member.course_group_id ?? null)) return;
    // A student must keep a group (DB check constraint); block clearing it with a
    // clear message rather than surfacing the raw constraint error.
    if (!next && member.course_role_id === '_student') {
      setActionError('Students must be assigned to a group.');
      return;
    }
    setSavingId(member.id);
    setActionError(null);
    try {
      await membersClient.updateCourseMembersCourseMembersIdPatch({
        id: member.id,
        body: { course_group_id: next },
      });
      await reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Failed to change group');
    } finally {
      setSavingId(null);
    }
  }

  async function removeMember(member: CourseMemberList) {
    await membersClient.deleteCourseMembersCourseMembersIdDelete({ id: member.id });
    setToRemove(null);
    await reload();
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden
        message="You need lecturer access (or higher) on this course to manage its members."
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
            { label: 'Course Members' },
          ]}
          title="Course Members"
          subtitle="Manage who belongs to this course and their roles."
          actions={
            <Link
              href={`/courses/${courseId}/lecturer/members/add`}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Add members
            </Link>
          }
        />

        <ErrorBanner>{error || actionError}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading members…</ListLoading>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <tr>
                  <Th>Member</Th>
                  <Th>Role</Th>
                  <Th>Group</Th>
                  <th className="px-4 py-3" />
                </tr>
              </Thead>
              <Tbody>
                {members.map((m) => {
                  const isSelf = user?.id === m.user_id;
                  const manageable = !isSelf && canManageMemberRole(ceiling, m.course_role_id);
                  // The current role may rank above the assigner's options; include
                  // it so the select shows the real value rather than blanking out.
                  const options = roleOptions.includes(m.course_role_id as never)
                    ? roleOptions
                    : [...roleOptions, m.course_role_id];
                  return (
                    <tr key={m.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900 text-sm">
                          {memberName(m)}
                          {isSelf && <span className="ml-2 text-xs text-gray-400">(you)</span>}
                        </div>
                        <div className="text-xs text-gray-500">{m.user?.email ?? '—'}</div>
                      </td>
                      <td className="px-4 py-3">
                        {manageable ? (
                          <select
                            value={m.course_role_id}
                            disabled={savingId === m.id}
                            onChange={(e) => changeRole(m, e.target.value)}
                            className="px-2 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                          >
                            {options.map((r) => (
                              <option key={r} value={r}>
                                {courseRoleLabel(r)}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <Badge color="gray">{courseRoleLabel(m.course_role_id)}</Badge>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {manageable ? (
                          <select
                            value={m.course_group_id ?? ''}
                            disabled={savingId === m.id}
                            onChange={(e) => changeGroup(m, e.target.value)}
                            className="px-2 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                          >
                            <option value="">— no group —</option>
                            {groups.map((g) => (
                              <option key={g.id} value={g.id}>
                                {g.title || g.id}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-sm text-gray-600">
                            {m.course_group_id ? groupName.get(m.course_group_id) ?? '—' : '—'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {manageable && (
                          <button
                            onClick={() => setToRemove(m)}
                            className="text-sm text-red-600 hover:underline"
                          >
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {members.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                      No members on this page.
                    </td>
                  </tr>
                )}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}

        {/* Pager — pinned below the scrolling list. Total count isn't exposed
            via the client, so Next is enabled whenever a full page came back. */}
        <div className="shrink-0 flex items-center justify-between">
          <span className="text-sm text-gray-500">Page {page + 1}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext || loading}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </ListPageLayout>

      {toRemove && (
        <ConfirmDeleteDialog
          title="Remove member"
          message={`Remove ${memberName(toRemove)} from this course? This deletes their membership; their account is not affected.`}
          confirmWord={toRemove.user?.email || memberName(toRemove)}
          onConfirm={() => removeMember(toRemove)}
          onClose={() => setToRemove(null)}
        />
      )}
    </AuthenticatedLayout>
  );
}
