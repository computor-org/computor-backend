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
// The catalog sits here rather than behind a permission: it is how a user with
// no memberships at all finds their first course (issue #213).
//
// Dashboard leads because it is where signing in already lands you — it just had
// no entry here, so the only ways back to it were the top-bar logo and the
// sidebar's user name, neither of which looks like navigation.
export const coursesNavigation: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: '/dashboard',
    icon: 'dashboard',
    ownPage: true,
  },
  {
    id: 'courses',
    label: 'Courses',
    path: '/courses',
    icon: 'courses',
    ownPage: true,
    subItems: [
      { id: 'courses-mine', label: 'My courses', path: '/courses' },
      { id: 'courses-catalog', label: 'Catalog', path: '/courses/catalog' },
    ],
  },
];

// Workspaces — gated by workspace access (_workspace_user / admin). Choosing a
// type and creating a workspace happens on /workspaces itself, so the
// Administration sub-item (deploying templates, fleet, volumes) only appears
// for maintainers; plain workspace users get a single flat entry.
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
      { id: 'mgmt-families', label: 'Course families', path: '/course-families' },
      { id: 'mgmt-examples', label: 'Examples', path: '/examples' },
      { id: 'mgmt-example-repos', label: 'Example repositories', path: '/example-repositories' },
      { id: 'mgmt-gitservers', label: 'Git servers', path: '/admin/git-servers' },
    ],
  },
];

// Service accounts — admin or _service_manager. Its own group rather than a
// System sub-item, because the System group is gated on isAdmin alone and
// _service_manager exists precisely so this can be delegated without admin.
export const servicesNavigation: NavItem[] = [
  {
    id: 'services',
    label: 'Services',
    path: '/admin/services',
    icon: 'services',
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
      { id: 'sys-status', label: 'Status', path: '/admin/status' },
      { id: 'sys-maintenance', label: 'Maintenance', path: '/admin/maintenance' },
      { id: 'sys-limits', label: 'Instance limits', path: '/admin/limits' },
      { id: 'sys-updates', label: 'Updates', path: '/admin/updates' },
      { id: 'sys-consent', label: 'Privacy notices', path: '/admin/consent' },
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
      { id: 'um-invites', label: 'Invite links', path: '/admin/users/invites' },
      { id: 'um-roles', label: 'Roles & claims', path: '/admin/users/roles' },
    ],
  },
];

/**
 * The tutor view is not built yet.
 *
 * The backend hands out the `tutor` view to `_tutor` *and every role above it*
 * (see COURSE_ROLE_VIEW_MAP in business_logic/users.py), so leaving the entry in
 * meant every lecturer, maintainer and owner had a nav item that dead-ended on a
 * "Coming Soon" page wearing the 404 illustration. Hidden here rather than
 * deleted so switching it back on is this one line; the routes still exist and
 * answer honestly if someone has the URL.
 */
const TUTOR_VIEW_ENABLED = false;

// Navigation structure for view-based navigation (when in course context).
//
// The lecturer sub-items are ordered by workflow, not by role seniority:
// authoring (Assignments, Templates) is what a lecturer opens a course to do at
// the start of a semester, and it used to sit below three roster-management
// pages with Grading — the analytics view — as the section's landing page.
export const getViewNavigation = (courseId: string): NavItem[] =>
  [
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
      // Filtered out below until the view exists. Its sub-pages (submissions,
      // grading) are stubs too, which is why it has none listed here.
    },
    {
      id: 'lecturer-view',
      view: 'lecturer',
      label: 'Lecturer',
      path: `/courses/${courseId}/lecturer`,
      icon: 'lecturer',
      // No ownPage: /courses/[id]/lecturer only redirects to the first sub-item,
      // so the sidebar link hops there directly.
      subItems: [
        { id: 'lecturer-assignments', label: 'Assignments', path: `/courses/${courseId}/lecturer/assignments` },
        { id: 'lecturer-templates', label: 'Templates', path: `/courses/${courseId}/lecturer/templates` },
        { id: 'lecturer-grading', label: 'Grading', path: `/courses/${courseId}/lecturer/grading` },
        { id: 'lecturer-members', label: 'Course members', path: `/courses/${courseId}/lecturer/members` },
        { id: 'lecturer-groups', label: 'Course groups', path: `/courses/${courseId}/lecturer/groups` },
        { id: 'lecturer-workspaces', label: 'Workspaces', path: `/courses/${courseId}/lecturer/workspaces` },
      ],
    },
  ].filter((item) => TUTOR_VIEW_ENABLED || item.view !== 'tutor');

/** Is `pathname` on this item's own path or anywhere beneath it? */
export function pathMatches(itemPath: string, pathname: string): boolean {
  return pathname === itemPath || pathname.startsWith(itemPath + '/');
}
