// Sidebar navigation configuration: static nav trees + the course-view tree.
// Kept out of Sidebar.tsx so the component is just state + rendering.

export interface SubItem {
  id: string;
  label: string;
  path: string;
}

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: string;
  subItems?: SubItem[];
  /** Only used for course view navigation — matched against user's available views */
  view?: string;
  /**
   * Set when the parent has its own landing page at `path`. Default (unset) for a
   * parent WITH sub-items means "no dedicated page" — clicking it hops to the
   * first sub-item instead (e.g. System → Maintenance).
   */
  ownPage?: boolean;
}

// Always-visible navigation (every authenticated user sees their courses).
export const coursesNavigation: NavItem[] = [
  {
    id: 'courses',
    label: 'Courses',
    path: '/courses',
    icon: 'courses',
  },
];

// Workspaces — gated by workspace access (_workspace_user / admin). Template
// browsing/provisioning lives on /workspaces/create (maintainer-only), so the
// Administration sub-item only appears for maintainers; plain workspace users
// get a single flat entry.
export const getWorkspacesNavigation = (includeAdmin: boolean): NavItem[] => [
  {
    id: 'workspaces',
    label: 'Workspaces',
    path: '/workspaces',
    icon: 'workspaces',
    ownPage: true,
    subItems: includeAdmin
      ? [
          { id: 'ws-list', label: 'Workspaces', path: '/workspaces' },
          { id: 'ws-admin', label: 'Administration', path: '/workspaces/admin' },
        ]
      : undefined,
  },
];

// Management — the org → course-family → course pipeline. Shown to the
// lecturer-view cohort (admins, organization managers, org/family role holders);
// the actual create actions on each page are gated finer.
export const managementNavigation: NavItem[] = [
  {
    id: 'management',
    label: 'Organizations',
    path: '/organizations',
    icon: 'lecturer',
    ownPage: true,
    subItems: [
      { id: 'mgmt-orgs', label: 'Organizations', path: '/organizations' },
      { id: 'mgmt-families', label: 'Course Families', path: '/course-families' },
      { id: 'mgmt-examples', label: 'Examples', path: '/examples' },
      { id: 'mgmt-example-repos', label: 'Example Repositories', path: '/example-repositories' },
      { id: 'mgmt-gitservers', label: 'Git Servers', path: '/admin/git-servers' },
    ],
  },
];

// Admin-only navigation items
export const adminNavigation: NavItem[] = [
  {
    id: 'system',
    label: 'System',
    path: '/admin',
    icon: 'admin',
    subItems: [
      { id: 'sys-maintenance', label: 'Maintenance', path: '/admin/maintenance' },
      { id: 'sys-updates', label: 'Updates', path: '/admin/updates' },
      { id: 'sys-consent', label: 'Privacy Notices', path: '/admin/consent' },
    ],
  },
];

// User management navigation (admin or _user_manager)
export const userMgmtNavigation: NavItem[] = [
  {
    id: 'user-management',
    label: 'Users',
    path: '/admin/users',
    icon: 'users',
    ownPage: true,
    subItems: [
      { id: 'um-users', label: 'Users', path: '/admin/users' },
      { id: 'um-invites', label: 'Invite Links', path: '/admin/users/invites' },
      { id: 'um-roles', label: 'Roles & Claims', path: '/admin/users/roles' },
    ],
  },
];

// Navigation structure for view-based navigation (when in course context)
export const getViewNavigation = (courseId: string): NavItem[] => [
  {
    id: 'student-view',
    view: 'student',
    label: 'Student',
    path: `/courses/${courseId}/student`,
    icon: 'student',
    ownPage: true,
    subItems: [
      { id: 'student-assignments', label: 'Assignments', path: `/courses/${courseId}/student/assignments` },
    ],
  },
  {
    id: 'tutor-view',
    view: 'tutor',
    label: 'Tutor',
    path: `/courses/${courseId}/tutor`,
    icon: 'tutor',
    ownPage: true,
    // The Tutor landing IS the student progress overview; no sub-pages yet
    // (submissions/grading are still stubs).
  },
  {
    id: 'lecturer-view',
    view: 'lecturer',
    label: 'Lecturer',
    path: `/courses/${courseId}/lecturer`,
    icon: 'lecturer',
    ownPage: true,
    subItems: [
      { id: 'lecturer-assignments', label: 'Assignments', path: `/courses/${courseId}/lecturer/assignments` },
      { id: 'lecturer-students', label: 'Students', path: `/courses/${courseId}/lecturer/students` },
      { id: 'lecturer-templates', label: 'Templates', path: `/courses/${courseId}/lecturer/templates` },
      { id: 'lecturer-workspaces', label: 'Workspaces', path: `/courses/${courseId}/lecturer/workspaces` },
      // Grading Overview isn't implemented yet — re-add the link once
      // /courses/[id]/lecturer/grading has a real page.
    ],
  },
  {
    id: 'management-view',
    view: 'management',
    label: 'Management',
    path: `/courses/${courseId}/management`,
    icon: 'admin',
    subItems: [
      { id: 'management-members', label: 'Course Members', path: `/courses/${courseId}/management/members` },
      { id: 'management-groups', label: 'Course Groups', path: `/courses/${courseId}/management/groups` },
    ],
  },
];

/** Is `pathname` on this item's own path or anywhere beneath it? */
export function pathMatches(itemPath: string, pathname: string): boolean {
  return pathname === itemPath || pathname.startsWith(itemPath + '/');
}
