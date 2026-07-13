'use client';

import { useAuth } from '@/src/contexts/AuthContext';

/**
 * Central role/permission helpers for gating UI consistently.
 *
 * Sources (all from the backend, fetched in AuthContext):
 *  - `scopes` (`GET /user/scopes`): `is_admin` + per-scope role maps
 *    (organization / course_family / course → role labels held).
 *  - `views` (`GET /user/views`): `lecturer` | `student` | `tutor` | `user_manager`.
 *  - `user.systemRoles`: global role ids (e.g. `_admin`, `_organization_manager`,
 *    `_user_manager`).
 *
 * The `lecturer` view is the org → course-family → course *creation pipeline*, so
 * it is the right gate for showing the Management section. The actual create
 * *actions* are gated finer (org creation needs admin/`_organization_manager`,
 * family/course creation needs a manage role on the parent scope). The backend
 * still enforces every action; these helpers just decide what to show.
 */

// organization / course_family scope role hierarchy (owner > manager > developer).
const SCOPE_RANK: Record<string, number> = { _owner: 3, _manager: 2, _developer: 1 };

// course role hierarchy + friendly labels for per-course badges.
const COURSE_ROLE_RANK: Record<string, number> = {
  _owner: 5,
  _maintainer: 4,
  _lecturer: 3,
  _tutor: 2,
  _student: 1,
};
const COURSE_ROLE_LABEL: Record<string, string> = {
  _owner: 'Owner',
  _maintainer: 'Maintainer',
  _lecturer: 'Lecturer',
  _tutor: 'Tutor',
  _student: 'Student',
};

export function usePermissions() {
  const { user, views, scopes } = useAuth();
  const systemRoles = user?.systemRoles ?? [];

  const isAdmin =
    Boolean(scopes?.is_admin) || systemRoles.includes('_admin') || user?.role === 'admin';
  const isOrganizationManager = systemRoles.includes('_organization_manager');
  const isUserManager = isAdmin || systemRoles.includes('_user_manager');
  // The cohort allowed to manage the org → family → course → git
  // registry surfaces (the manage/edit/delete actions on those pages).
  const canManageHierarchy = isAdmin || isOrganizationManager;
  // Example library authoring (upload / create / edit / delete of examples and
  // example repositories) is reserved to the _example_manager system role
  // (admins bypass). Mirrors the backend, where these claims moved off
  // _organization_manager onto _example_manager.
  const isExampleManager = isAdmin || systemRoles.includes('_example_manager');
  // Who may AUTHOR examples/repositories.
  const canManageExamples = isExampleManager;
  // Who may BROWSE the example library (read-only): the management cohort keeps
  // read access, plus example managers. Admins bypass via both flags.
  const canViewExamples = canManageHierarchy || isExampleManager;
  // Coder/workspace access is controlled by the _workspace_user system role
  // (admins bypass). Gates the Workspaces sidebar section.
  const isWorkspaceUser = isAdmin || systemRoles.includes('_workspace_user');
  // Provisioning, templates and workspace administration are reserved to
  // _workspace_maintainer (admins bypass) — mirrors the backend claims
  // (workspace:provision / workspace:templates / workspace:manage).
  const isWorkspaceMaintainer = isAdmin || systemRoles.includes('_workspace_maintainer');

  const hasView = (view: string) => views.includes(view);

  const orgRoles = scopes?.organization ?? {};
  const familyRoles = scopes?.course_family ?? {};
  const courseRoles = scopes?.course ?? {};

  const scopeHasAtLeast = (
    map: Record<string, string[]>,
    id: string,
    minRole: string,
  ): boolean => {
    const want = SCOPE_RANK[minRole] ?? 1;
    return (map[id] ?? []).some((r) => (SCOPE_RANK[r] ?? 0) >= want);
  };

  // Show the Management (org → family → course) section to the lecturer-pipeline
  // cohort: admins, organization managers, anyone holding an org/family scope
  // role, or anyone the backend granted the `lecturer` view.
  const showManagement =
    isAdmin ||
    isOrganizationManager ||
    hasView('lecturer') ||
    Object.keys(orgRoles).length > 0 ||
    Object.keys(familyRoles).length > 0;

  // Create-action gates (mirror backend authority; the backend still enforces).
  const canCreateOrganization = isAdmin || isOrganizationManager;

  const canCreateCourseFamily = (orgId?: string): boolean =>
    isAdmin ||
    isOrganizationManager ||
    (orgId
      ? scopeHasAtLeast(orgRoles, orgId, '_manager')
      : Object.keys(orgRoles).length > 0);

  const canCreateCourse = (orgId?: string, familyId?: string): boolean =>
    isAdmin ||
    isOrganizationManager ||
    (orgId ? scopeHasAtLeast(orgRoles, orgId, '_manager') : false) ||
    (familyId
      ? scopeHasAtLeast(familyRoles, familyId, '_manager')
      : Object.keys(familyRoles).length > 0);

  // True when the user holds at least `minRole` on the course (admins bypass).
  // Mirrors the backend course-role hierarchy so course surfaces gate the same
  // way the API enforces them.
  const courseHasAtLeast = (courseId: string, minRole: string): boolean => {
    if (isAdmin) return true;
    const want = COURSE_ROLE_RANK[minRole] ?? COURSE_ROLE_RANK._owner;
    return (courseRoles[courseId] ?? []).some(
      (r) => (COURSE_ROLE_RANK[r] ?? 0) >= want,
    );
  };

  // The user's highest role on a course → friendly label for a badge, or null.
  const courseRole = (courseId: string): string | null => {
    const roles = courseRoles[courseId] ?? [];
    if (roles.length === 0) return null;
    const top = roles.reduce((best, r) =>
      (COURSE_ROLE_RANK[r] ?? 0) > (COURSE_ROLE_RANK[best] ?? 0) ? r : best,
    );
    return COURSE_ROLE_LABEL[top] ?? top.replace(/^_/, '');
  };

  return {
    isAdmin,
    isOrganizationManager,
    isUserManager,
    canManageHierarchy,
    isExampleManager,
    canManageExamples,
    canViewExamples,
    isWorkspaceUser,
    isWorkspaceMaintainer,
    hasView,
    views,
    scopes,
    orgRoles,
    familyRoles,
    courseRoles,
    showManagement,
    canCreateOrganization,
    canCreateCourseFamily,
    canCreateCourse,
    courseRole,
    courseHasAtLeast,
  };
}
