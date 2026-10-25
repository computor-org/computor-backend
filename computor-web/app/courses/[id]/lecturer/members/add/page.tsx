'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import AddFromUserList from '@/src/components/course-members/AddFromUserList';
import AddByEmail from '@/src/components/course-members/AddByEmail';
import ImportFromFile from '@/src/components/course-members/ImportFromFile';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import type { CourseGroupList } from 'types/generated';
import { assignableRoles, highestCourseRole, maxAssignableRole } from '@/src/utils/courseRoles';

const groupsClient = new CourseGroupsClient();

const COPY = {
  de: {
    courseMembers: 'Kursmitglieder',
    add: 'Hinzufügen',
    forbidden: 'Zum Hinzufügen von Mitgliedern brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    backToCourse: 'Zurück zum Kurs',
    title: 'Mitglieder hinzufügen',
    subtitle: 'Füge bestehende Nutzer aus der Liste hinzu oder lade neue Personen per E-Mail ein.',
    tabList: 'Aus Nutzerliste',
    tabEmail: 'Per E-Mail',
    tabFile: 'Datei importieren',
  },
  en: {
    courseMembers: 'Course members',
    add: 'Add',
    forbidden: 'You need lecturer access (or higher) on this course to add members.',
    backToCourse: 'Back to course',
    title: 'Add members',
    subtitle: 'Add existing users from the list, or invite someone new by email.',
    tabList: 'From user list',
    tabEmail: 'By email',
    tabFile: 'Import file',
  },
};

type AddTab = 'list' | 'email' | 'file';

export default function AddCourseMembersPage() {
  const courseId = useParams().id as string;
  const t = COPY[useUiLanguage()];
  const crumbs = useCourseCrumbs(courseId, { label: t.courseMembers, href: `/courses/${courseId}/lecturer/members` }, t.add);
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
        message={t.forbidden}
        backLink={`/courses/${courseId}`}
        backText={t.backToCourse}
      />
    );
  }

  const tabClass = (active: boolean) =>
    `py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
      active ? 'border-accent text-accent-text' : 'border-transparent text-muted hover:text-body'
    }`;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={t.title}
          subtitle={t.subtitle}
        />

        {/* Tabs: the two add flows are mutually exclusive, so show one at a time. */}
        <div className="border-b border-rule">
          <nav className="flex gap-6">
            <button type="button" onClick={() => setTab('list')} className={tabClass(tab === 'list')}>
              {t.tabList}
            </button>
            <button type="button" onClick={() => setTab('email')} className={tabClass(tab === 'email')}>
              {t.tabEmail}
            </button>
            <button type="button" onClick={() => setTab('file')} className={tabClass(tab === 'file')}>
              {t.tabFile}
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
