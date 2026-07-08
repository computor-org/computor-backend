'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import AddFromUserList from '@/src/components/course-members/AddFromUserList';
import AddByEmail from '@/src/components/course-members/AddByEmail';
import ImportFromFile from '@/src/components/course-members/ImportFromFile';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import type { CourseGroupList } from 'types/generated';
import { assignableRoles, highestCourseRole, maxAssignableRole } from '@/src/utils/courseRoles';

const groupsClient = new CourseGroupsClient();
const coursesClient = new CoursesClient();

type AddTab = 'list' | 'email' | 'file';

export default function AddCourseMembersPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseRoles, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');
  const ceiling = isAdmin || isOrganizationManager ? '_owner' : highestCourseRole(courseRoles[courseId]);
  // Roles this user may grant when adding/importing members. Lecturers (and
  // below) are capped at _student; only maintainers/owners/org-managers may
  // grant a higher role. Mirrors the backend assignment ceiling.
  const roleOptions = assignableRoles(maxAssignableRole(ceiling));
  const defaultRole = roleOptions[0] ?? '_student';

  const [tab, setTab] = useState<AddTab>('list');

  const { data: courseData } = useResource(
    () => coursesClient.getCoursesCoursesIdGet({ id: courseId }).catch(() => null),
    [courseId],
    { enabled: canManage },
  );
  const courseLabel = courseData?.title || courseData?.path || 'Course';

  // Course groups — a student must be assigned to one (DB constraint), so the
  // user-list tab needs a group picker. Also feeds a sensible default below.
  const { data: groupData } = useResource(
    () =>
      groupsClient
        .listCourseGroupsCourseGroupsGet({ courseId, limit: 500 })
        .catch(() => [] as CourseGroupList[]),
    [courseId],
    { enabled: canManage },
  );
  const groups = groupData ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden
        message="You need lecturer access (or higher) on this course to add members."
        backLink={`/courses/${courseId}`}
        backText="Back to course"
      />
    );
  }

  const tabClass = (active: boolean) =>
    `py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
      active ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
    }`;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: courseLabel, href: `/courses/${courseId}` },
            { label: 'Course Members', href: `/courses/${courseId}/management/members` },
            { label: 'Add' },
          ]}
          title="Add members"
          subtitle="Add existing users from the list, or invite someone new by email."
        />

        {/* Tabs: the two add flows are mutually exclusive, so show one at a time. */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-6">
            <button type="button" onClick={() => setTab('list')} className={tabClass(tab === 'list')}>
              From user list
            </button>
            <button type="button" onClick={() => setTab('email')} className={tabClass(tab === 'email')}>
              By email
            </button>
            <button type="button" onClick={() => setTab('file')} className={tabClass(tab === 'file')}>
              Import file
            </button>
          </nav>
        </div>

        <ScrollArea>
          {tab === 'list' && (
            <AddFromUserList
              courseId={courseId}
              roleOptions={roleOptions}
              defaultRole={defaultRole}
              groups={groups}
              canManage={canManage}
            />
          )}
          {tab === 'email' && (
            <AddByEmail courseId={courseId} roleOptions={roleOptions} defaultRole={defaultRole} />
          )}
          {tab === 'file' && (
            <ImportFromFile courseId={courseId} roleOptions={roleOptions} defaultRole={defaultRole} />
          )}
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
