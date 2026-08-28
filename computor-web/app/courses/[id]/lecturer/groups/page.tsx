'use client';

import { Fragment, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
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
import { courseRoleLabel } from '@/src/utils/courseRoles';
import { memberName } from '@/src/utils/userName';

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
    () => buildRoster(data?.groups ?? [], data?.members ?? []),
    [data?.groups, data?.members],
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
            <ButtonLink href={`/courses/${courseId}/lecturer/groups/create`}>New group</ButtonLink>
          }
        />

        <ErrorBanner>{error || actionError}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading groups…</ListLoading>
        ) : (
          <ScrollArea spacing="rows">
            {roster.length === 0 ? (
              <EmptyState
                title="No groups yet"
                description="Create one so students can be assigned to it."
              />
            ) : (
              <>
                {(data?.groups ?? []).length === 0 && (
                  <Notice tone="info">
                    No groups yet — create one so students can be assigned to it.
                  </Notice>
                )}

                <Toolbar>
                  <Button variant="ghost" size="sm" onClick={() => setExpanded(new Set())}>
                    Collapse all
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
                    Expand all
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
                            {members.length} {members.length === 1 ? 'member' : 'members'}
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
                              Edit
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
                                  ? "Reassign this group's members before deleting it."
                                  : undefined
                              }
                              onClick={() => setToDelete(group)}
                            >
                              Delete
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
                                {courseRoleLabel(m.course_role_id)}
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
