'use client';

import { Fragment, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import EmptyState from '@/src/components/EmptyState';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import Notice from '@/src/components/ui/Notice';
import Toolbar from '@/src/components/ui/Toolbar';
import TreeRow, { TreeRows } from '@/src/components/ui/TreeRow';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import type { CourseGroupList } from 'types/generated';
import { buildRoster, fetchCourseRoster } from '@/src/components/course-members/roster';
import { courseRoleLabel, localizedRoleLabel } from '@/src/utils/courseRoles';
import { memberName } from '@/src/utils/userName';

const groupsClient = new CourseGroupsClient();
const membersClient = new CourseMembersClient();

const COPY = {
  de: {
    courseGroups: 'Kursgruppen',
    deleteFailed: 'Gruppe konnte nicht gelöscht werden',
    forbidden: 'Zum Verwalten der Gruppen brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    backToCourse: 'Zurück zum Kurs',
    subtitle: 'Gruppen (Übungsgruppen, Tutorien), denen Studierende zugeordnet werden. Jede studierende Person muss einer Gruppe angehören.',
    newGroup: 'Neue Gruppe',
    loading: 'Gruppen werden geladen …',
    emptyTitle: 'Noch keine Gruppen',
    emptyDescription: 'Lege eine an, damit Studierende ihr zugeordnet werden können.',
    emptyNotice: 'Noch keine Gruppen – lege eine an, damit Studierende ihr zugeordnet werden können.',
    collapseAll: 'Alle einklappen',
    expandAll: 'Alle ausklappen',
    member: 'Mitglied',
    members: 'Mitglieder',
    edit: 'Bearbeiten',
    delete: 'Löschen',
    reassign: 'Weise die Mitglieder dieser Gruppe neu zu, bevor du sie löschst.',
    deleteTitle: 'Gruppe löschen',
    untitled: 'Gruppe ohne Titel',
    deleteMessage: (title: string) => `Die Gruppe „${title}“ löschen? Das kann nicht rückgängig gemacht werden.`,
  },
  en: {
    courseGroups: 'Course groups',
    deleteFailed: 'Failed to delete group',
    forbidden: 'You need lecturer access (or higher) on this course to manage its groups.',
    backToCourse: 'Back to course',
    subtitle: 'Groups (lab sections, tutorial cohorts) students are assigned to. Every student must belong to a group.',
    newGroup: 'New group',
    loading: 'Loading groups…',
    emptyTitle: 'No groups yet',
    emptyDescription: 'Create one so students can be assigned to it.',
    emptyNotice: 'No groups yet — create one so students can be assigned to it.',
    collapseAll: 'Collapse all',
    expandAll: 'Expand all',
    member: 'member',
    members: 'members',
    edit: 'Edit',
    delete: 'Delete',
    reassign: "Reassign this group's members before deleting it.",
    deleteTitle: 'Delete group',
    untitled: 'Untitled group',
    deleteMessage: (title: string) => `Delete the group "${title}"? This cannot be undone.`,
  },
};

export default function CourseGroupsPage() {
  const courseId = useParams().id as string;
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, t.courseGroups);
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [actionError, setActionError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<CourseGroupList | null>(null);
  // Collapsed is the default the issue asks for, so this holds what is OPEN.
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, loading, error, reload } = useResource(
    async () => {
      const [groups, members] = await Promise.all([
        groupsClient.listCourseGroupsCourseGroupsGet({ courseId, limit: 500 }),
        // The roster is both the membership shown under each group and the count
        // that decides whether a group can be deleted (the FK is RESTRICT).
        fetchCourseRoster(membersClient, courseId),
      ]);
      return { groups, members };
    },
    [courseId],
    { enabled: canManage },
  );

  const roster = useMemo(
    () => buildRoster(data?.groups ?? [], data?.members ?? [], language),
    [data?.groups, data?.members, language],
  );

  function toggle(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (!next.delete(key)) next.add(key);
      return next;
    });
  }

  async function deleteGroup(group: CourseGroupList) {
    setActionError(null);
    try {
      await groupsClient.deleteCourseGroupsCourseGroupsIdDelete({ id: group.id });
      setToDelete(null);
      await reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : t.deleteFailed);
      setToDelete(null);
    }
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
          title={t.courseGroups}
          subtitle={t.subtitle}
          actions={
            <ButtonLink href={`/courses/${courseId}/lecturer/groups/create`}>{t.newGroup}</ButtonLink>
          }
        />

        <ErrorBanner>{error || actionError}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : (
          <ScrollArea spacing="rows">
            {roster.length === 0 ? (
              <EmptyState
                title={t.emptyTitle}
                description={t.emptyDescription}
              />
            ) : (
              <>
                {(data?.groups ?? []).length === 0 && (
                  <Notice tone="info">
                    {t.emptyNotice}
                  </Notice>
                )}

                <Toolbar>
                  <Button variant="ghost" size="sm" onClick={() => setExpanded(new Set())}>
                    {t.collapseAll}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setExpanded(
                        new Set(roster.filter((r) => r.members.length > 0).map((r) => r.key)),
                      )
                    }
                  >
                    {t.expandAll}
                  </Button>
                </Toolbar>

                <TreeRows>
                  {roster.map(({ group, key, title, members }) => {
                    const open = expanded.has(key);
                    return (
                      <Fragment key={key}>
                        <TreeRow
                          depth={0}
                          expandable={members.length > 0}
                          expanded={open}
                          onToggle={() => toggle(key)}
                          label={title}
                        >
                          <Badge tone="muted" className="shrink-0">
                            {members.length} {members.length === 1 ? t.member : t.members}
                          </Badge>
                          {/* The unassigned bucket is a view, not a row anyone
                              can edit or delete — it has no group behind it. */}
                          {group && (
                            <ButtonLink
                              href={`/courses/${courseId}/lecturer/groups/${group.id}/edit`}
                              variant="ghost"
                              size="xs"
                              className="shrink-0"
                            >
                              {t.edit}
                            </ButtonLink>
                          )}
                          {group && (
                            <Button
                              variant="dangerGhost"
                              size="xs"
                              className="shrink-0"
                              disabled={members.length > 0}
                              title={
                                members.length > 0
                                  ? t.reassign
                                  : undefined
                              }
                              onClick={() => setToDelete(group)}
                            >
                              {t.delete}
                            </Button>
                          )}
                        </TreeRow>

                        {open &&
                          members.map((m) => (
                            <TreeRow
                              key={m.id}
                              depth={1}
                              label={
                                <>
                                  {memberName(m)}
                                  {m.user?.email && (
                                    <span className="ml-2 text-xs font-normal text-muted">
                                      {m.user.email}
                                    </span>
                                  )}
                                </>
                              }
                            >
                              <Badge tone="muted" className="shrink-0">
                                {localizedRoleLabel(courseRoleLabel(m.course_role_id), language)}
                              </Badge>
                            </TreeRow>
                          ))}
                      </Fragment>
                    );
                  })}
                </TreeRows>
              </>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>

      {toDelete && (
        <ConfirmDeleteDialog
          title={t.deleteTitle}
          message={t.deleteMessage(toDelete.title || t.untitled)}
          confirmWord={toDelete.title || t.untitled}
          onConfirm={() => deleteGroup(toDelete)}
          onClose={() => setToDelete(null)}
        />
      )}
    </AuthenticatedLayout>
  );
}
