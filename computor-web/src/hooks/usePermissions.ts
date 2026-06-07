'use client';

import { useAuth } from '../contexts/AuthContext';

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

export function usePermissions() {
  const { user, views, scopes } = useAuth();
  const systemRoles = user?.systemRoles ?? [];

  const isAdmin =
    Boolean(scopes?.is_admin) || systemRoles.includes('_admin') || user?.role === 'admin';
  const isOrganizationManager = systemRoles.includes('_organization_manager');
  const isUserManager = isAdmin || systemRoles.includes('_user_manager');
  // Coder/workspace access is controlled by the _workspace_user system role
  // (admins bypass). Gates the Workspaces sidebar section.
  const isWorkspaceUser = isAdmin || systemRoles.includes('_workspace_user');

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

  return {
    isAdmin,
    isOrganizationManager,
    isUserManager,
    isWorkspaceUser,
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
  };
}
