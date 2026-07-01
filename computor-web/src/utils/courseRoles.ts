/**
 * Course-role hierarchy mirrored from the backend (`permissions/roles.py` +
 * `principal.py`). Kept in one place so the member-management UI ranks, labels
 * and gates roles exactly the way the API enforces them. The backend remains the
 * source of truth — these helpers only decide what to show/enable.
 */

// Highest privilege last.
export const COURSE_ROLES = [
  '_student',
  '_tutor',
  '_lecturer',
  '_maintainer',
  '_owner',
] as const;

export type CourseRoleId = (typeof COURSE_ROLES)[number];

export const COURSE_ROLE_RANK: Record<string, number> = {
  _student: 1,
  _tutor: 2,
  _lecturer: 3,
  _maintainer: 4,
  _owner: 5,
};

export const COURSE_ROLE_LABEL: Record<string, string> = {
  _student: 'Student',
  _tutor: 'Tutor',
  _lecturer: 'Lecturer',
  _maintainer: 'Maintainer',
  _owner: 'Owner',
};

export function courseRoleLabel(roleId?: string | null): string {
  if (!roleId) return '—';
  return COURSE_ROLE_LABEL[roleId] ?? roleId.replace(/^_/, '');
}

export function roleRank(roleId?: string | null): number {
  return roleId ? (COURSE_ROLE_RANK[roleId] ?? 0) : 0;
}

/** The highest-privilege role id in a list, or null when the list is empty. */
export function highestCourseRole(roleIds: string[] | undefined | null): string | null {
  let best: string | null = null;
  for (const r of roleIds ?? []) {
    if (roleRank(r) > roleRank(best)) best = r;
  }
  return best;
}

/**
 * The highest role a principal with authority `ceiling` may *grant*. Lecturers
 * (and below) are capped at `_student`; only `_maintainer` and above — including
 * admins / organization managers, who are passed in as `_owner` — may grant a
 * role above `_student`. Mirrors the backend
 * `Principal.get_course_assignment_ceiling`.
 */
export function maxAssignableRole(ceiling?: string | null): CourseRoleId | null {
  if (!ceiling) return null;
  if (roleRank(ceiling) >= roleRank('_maintainer')) return ceiling as CourseRoleId;
  return '_student';
}

/**
 * Roles a principal whose assignment ceiling is `ceiling` may grant — every
 * role at or below the ceiling's rank (low → high). Mirrors the backend's
 * `CourseRoleHierarchy.can_assign_role` (level(assigner) >= level(target)).
 * Pass a value from {@link maxAssignableRole} to apply the lecturer cap.
 */
export function assignableRoles(ceiling?: string | null): CourseRoleId[] {
  const max = roleRank(ceiling);
  if (max <= 0) return [];
  return COURSE_ROLES.filter((r) => COURSE_ROLE_RANK[r] <= max);
}

/** Can a principal with `ceiling` modify/remove a member currently holding `targetRole`? */
export function canManageMemberRole(ceiling: string | null, targetRole?: string | null): boolean {
  const max = roleRank(ceiling);
  if (max <= 0) return false;
  // Mirror the backend guard: only members strictly below your ceiling.
  return roleRank(targetRole) < max;
}
