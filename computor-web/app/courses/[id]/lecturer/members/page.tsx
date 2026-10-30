'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import type { CourseMemberList, CourseGroupList } from 'types/generated';
import { Table, Thead, Tbody, Th } from '@/src/components/ui/Table';
import {
  assignableRoles,
  canManageMemberRole,
  courseRoleLabel,
  localizedRoleLabel,
  highestCourseRole,
  maxAssignableRole,
} from '@/src/utils/courseRoles';
import { memberName } from '@/src/utils/userName';

const PAGE_SIZE = 25;
const membersClient = new CourseMembersClient();
const groupsClient = new CourseGroupsClient();

const COPY = {
  de: {
    courseMembers: 'Kursmitglieder',
    roleFailed: 'Rolle konnte nicht geändert werden',
    groupFailed: 'Gruppe konnte nicht geändert werden',
    studentNeedsGroup: 'Studierende müssen einer Gruppe zugeordnet sein.',
    forbidden: 'Zum Verwalten der Mitglieder brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    backToCourse: 'Zurück zum Kurs',
    subtitle: 'Verwalte, wer zu diesem Kurs gehört, und welche Rollen die Mitglieder haben.',
    addMembers: 'Mitglieder hinzufügen',
    loading: 'Mitglieder werden geladen …',
    member: 'Mitglied',
    role: 'Rolle',
    group: 'Gruppe',
    you: '(du)',
    noGroup: '— keine Gruppe —',
    untitled: 'Gruppe ohne Titel',
    remove: 'Entfernen',
    empty: 'Keine Mitglieder auf dieser Seite.',
    page: (n: number) => `Seite ${n}`,
    previous: 'Zurück',
    next: 'Weiter',
    removeTitle: 'Mitglied entfernen',
    removeMessage: (name: string) => `${name} aus diesem Kurs entfernen? Dadurch wird die Mitgliedschaft gelöscht, das Konto bleibt unberührt.`,
  },
  en: {
    courseMembers: 'Course members',
    roleFailed: 'Failed to change role',
    groupFailed: 'Failed to change group',
    studentNeedsGroup: 'Students must be assigned to a group.',
    forbidden: 'You need lecturer access (or higher) on this course to manage its members.',
    backToCourse: 'Back to course',
    subtitle: 'Manage who belongs to this course and their roles.',
    addMembers: 'Add members',
    loading: 'Loading members…',
    member: 'Member',
    role: 'Role',
    group: 'Group',
    you: '(you)',
    noGroup: '— no group —',
    untitled: 'Untitled group',
    remove: 'Remove',
    empty: 'No members on this page.',
    page: (n: number) => `Page ${n}`,
    previous: 'Previous',
    next: 'Next',
    removeTitle: 'Remove member',
    removeMessage: (name: string) => `Remove ${name} from this course? This deletes their membership; their account is not affected.`,
  },
};

export default function CourseMembersPage() {
  const courseId = useParams().id as string;
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, t.courseMembers);
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
      const [members, groups] = await Promise.all([
        membersClient.listCourseMembersCourseMembersGet({
          courseId,
          skip: page * PAGE_SIZE,
          limit: PAGE_SIZE,
        }),
        groupsClient
          .listCourseGroupsCourseGroupsGet({ courseId, limit: 200 })
          .catch(() => [] as CourseGroupList[]),
      ]);
      return { members, groups };
    },
    [courseId, page],
    { enabled: canManage },
  );

  const members = data?.members ?? [];
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
      setActionError(e instanceof Error ? e.message : t.roleFailed);
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
      setActionError(t.studentNeedsGroup);
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
      setActionError(e instanceof Error ? e.message : t.groupFailed);
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
        message={t.forbidden}
        backLink={`/courses/${courseId}`}
        backText={t.backToCourse}
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={t.courseMembers}
          subtitle={t.subtitle}
          actions={
            <Link
              href={`/courses/${courseId}/lecturer/members/add`}
              className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover"
            >
              {t.addMembers}
            </Link>
          }
        />

        <ErrorBanner>{error || actionError}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <tr>
                  <Th>{t.member}</Th>
                  <Th>{t.role}</Th>
                  <Th>{t.group}</Th>
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
                    <tr key={m.id} className="hover:bg-canvas">
                      <td className="px-4 py-3">
                        <div className="font-medium text-fg text-sm">
                          {memberName(m)}
                          {isSelf && <>{' '}<span className="ml-1 text-xs text-subtle">{t.you}</span></>}
                        </div>
                        <div className="text-xs text-muted">{m.user?.email ?? '—'}</div>
                      </td>
                      <td className="px-4 py-3">
                        {manageable ? (
                          <select
                            value={m.course_role_id}
                            disabled={savingId === m.id}
                            onChange={(e) => changeRole(m, e.target.value)}
                            className="px-2 py-1 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent disabled:opacity-50"
                          >
                            {options.map((r) => (
                              <option key={r} value={r}>
                                {localizedRoleLabel(courseRoleLabel(r), language)}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <Badge color="gray">{localizedRoleLabel(courseRoleLabel(m.course_role_id), language)}</Badge>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {manageable ? (
                          <select
                            value={m.course_group_id ?? ''}
                            disabled={savingId === m.id}
                            onChange={(e) => changeGroup(m, e.target.value)}
                            className="px-2 py-1 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent disabled:opacity-50"
                          >
                            <option value="">{t.noGroup}</option>
                            {groups.map((g) => (
                              <option key={g.id} value={g.id}>
                                {g.title || t.untitled}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-sm text-muted">
                            {m.course_group_id ? groupName.get(m.course_group_id) ?? '—' : '—'}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {manageable && (
                          <button
                            onClick={() => setToRemove(m)}
                            className="text-sm text-danger-text hover:underline"
                          >
                            {t.remove}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {members.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted">
                      {t.empty}
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
          <span className="text-sm text-muted">{t.page(page + 1)}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="px-3 py-1.5 text-sm border border-rule-strong rounded-lg hover:bg-canvas disabled:opacity-50"
            >
              {t.previous}
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext || loading}
              className="px-3 py-1.5 text-sm border border-rule-strong rounded-lg hover:bg-canvas disabled:opacity-50"
            >
              {t.next}
            </button>
          </div>
        </div>
      </ListPageLayout>

      {toRemove && (
        <ConfirmDeleteDialog
          title={t.removeTitle}
          message={t.removeMessage(memberName(toRemove))}
          confirmWord={toRemove.user?.email || memberName(toRemove)}
          onConfirm={() => removeMember(toRemove)}
          onClose={() => setToRemove(null)}
        />
      )}
    </AuthenticatedLayout>
  );
}
