'use client';

import Image from 'next/image';
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCourseViews } from '@/src/hooks/useCourseViews';
import { icons } from './icons';

// Baked at build time by computor.sh (docker/web/Dockerfile GIT_COMMIT arg);
// unset in `next dev`, where the generic fallback is shown instead.
const APP_VERSION = process.env.NEXT_PUBLIC_GIT_COMMIT
  ? process.env.NEXT_PUBLIC_GIT_COMMIT.slice(0, 7)
  : 'dev';
import {
  NavItem,
  coursesNavigation,
  getWorkspacesNavigation,
  managementNavigation,
  adminNavigation,
  userMgmtNavigation,
  servicesNavigation,
  getViewNavigation,
  pathMatches,
} from '@/src/config/navigation';

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { isAdmin, isOrganizationManager, isUserManager, isWorkspaceUser, isWorkspaceMaintainer, isExampleManager, isServiceManager, showManagement } = usePermissions();
  const [collapsed, setCollapsed] = useState(false);

  // Sub-sections the user has explicitly toggled open. The section containing
  // the active route is always rendered expanded (see renderNavItems), so this
  // only needs to track manual expand/collapse.
  const [expandedViews, setExpandedViews] = useState<Record<string, boolean>>({});

  // Course context + the per-course views the user holds (UUID guard + fetch
  // live in the hook).
  const { currentCourseId, courseViews } = useCourseViews();

  const toggleView = (viewId: string) => {
    setExpandedViews(prev => ({
      ...prev,
      [viewId]: !prev[viewId]
    }));
  };

  /** Render a list of nav items with expand/collapse sub-items */
  const renderNavItems = (items: NavItem[]) =>
    items.map((navItem) => {
      const hasSubItems = !!navItem.subItems && navItem.subItems.length > 0;
      // A section is "active" when the current route is one of its sub-items
      // (paths may be unrelated to the parent's own path).
      const sectionActive = hasSubItems
        ? navItem.subItems!.some((s) => pathMatches(s.path, pathname))
        : false;
      // Only the MOST specific matching sub-item is active. Several sub-item
      // paths can prefix-match the route at once (a group's self-referential
      // first item like "/workspaces" is a prefix of "/workspaces/templates"),
      // so pick the longest match instead of lighting up every prefix.
      const activeSubPath = hasSubItems
        ? navItem.subItems!
            .filter((s) => pathMatches(s.path, pathname))
            .reduce<string | null>((best, s) => (s.path.length > (best?.length ?? -1) ? s.path : best), null)
        : null;
      // While a child is the active page the section stays expanded — it can't
      // be collapsed out from under the selected item.
      const isExpanded = expandedViews[navItem.id] || sectionActive;
      const isExactActive = pathname === navItem.path;
      // A parent with sub-items is "active" only when one of ITS OWN sub-items
      // matches — never just because the route sits under its path prefix (e.g.
      // /admin/git-servers is under System's /admin but belongs to Management).
      const isChildActive = hasSubItems ? sectionActive : pathname.startsWith(navItem.path + '/');
      // A parent with sub-items but no dedicated page of its own hops to its
      // first sub-item (e.g. System has no /admin page → go to Maintenance).
      const linkHref = hasSubItems && !navItem.ownPage ? navItem.subItems![0].path : navItem.path;

      return (
        <div key={navItem.id} className="space-y-1">
          <div className="flex items-center">
            <Link
              href={linkHref}
              className={`flex-1 flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                isExactActive
                  ? 'bg-accent-wash text-accent-text'
                  : isChildActive
                  ? 'bg-accent-wash/50 text-accent-text'
                  : 'text-body hover:bg-sunken'
              }`}
              title={collapsed ? navItem.label : undefined}
            >
              <span className={isExactActive || isChildActive ? 'text-accent-text' : 'text-muted'}>
                {icons[navItem.icon]}
              </span>
              {!collapsed && (
                <span className="text-sm font-medium">{navItem.label}</span>
              )}
            </Link>

            {!collapsed && hasSubItems && !sectionActive && (
              <button
                onClick={() => toggleView(navItem.id)}
                aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${navItem.label} section`}
                aria-expanded={isExpanded}
                className="p-2 hover:bg-sunken rounded transition-colors"
              >
                <span aria-hidden="true" className={`transition-transform inline-block ${isExpanded ? 'rotate-180' : ''}`}>
                  {icons.chevronDown}
                </span>
              </button>
            )}
          </div>

          {!collapsed && isExpanded && navItem.subItems && (
            <div className="ml-8 space-y-1">
              {navItem.subItems.map((subItem) => {
                const isSubActive = subItem.path === activeSubPath;

                return (
                  <Link
                    key={subItem.id}
                    href={subItem.path}
                    className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                      isSubActive
                        ? 'bg-accent-wash text-accent-text font-medium'
                        : 'text-muted hover:bg-sunken'
                    }`}
                  >
                    {subItem.label}
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      );
    });

  // If we're in a course context, show view-based navigation
  if (currentCourseId) {
    const viewNavigation = getViewNavigation(currentCourseId);
    // Only the course's actual views — never fall back to global views, which
    // would surface role views the user doesn't hold for this course.
    const activeViews = courseViews;
    // Admins/org managers without a course role only get the `management`
    // view from the backend; member administration now lives under Lecturer,
    // so that view keeps the Lecturer section visible for them.
    const availableViews = viewNavigation.filter(
      (item) =>
        activeViews.includes(item.view!) ||
        (item.view === 'lecturer' && activeViews.includes('management'))
    );

    return (
      <SidebarShell collapsed={collapsed} setCollapsed={setCollapsed} user={user}>
        {/* Back to Courses Link */}
        <Link
          href="/courses"
          className="flex items-center space-x-3 px-3 py-2 rounded-lg text-body hover:bg-sunken transition-colors mb-4"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          {!collapsed && <span className="text-sm">Back to Courses</span>}
        </Link>

        {/* Course overview (this course's landing page) — always reachable,
            even after switching into a role view. Active only on the exact
            path so it doesn't stay highlighted inside the role sub-routes. */}
        <Link
          href={`/courses/${currentCourseId}`}
          className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors mb-1 ${
            pathname === `/courses/${currentCourseId}`
              ? 'bg-accent-wash text-accent-text'
              : 'text-body hover:bg-sunken'
          }`}
          title={collapsed ? 'Overview' : undefined}
        >
          <span className={pathname === `/courses/${currentCourseId}` ? 'text-accent-text' : 'text-muted'}>
            {icons.overview}
          </span>
          {!collapsed && <span className="text-sm font-medium">Overview</span>}
        </Link>

        {renderNavItems(availableViews)}
      </SidebarShell>
    );
  }

  // Default navigation
  return (
    <SidebarShell collapsed={collapsed} setCollapsed={setCollapsed} user={user}>
      {renderNavItems(coursesNavigation)}
      {(showManagement || isExampleManager) &&
        renderNavItems(
          isAdmin || isOrganizationManager
            ? managementNavigation
            : managementNavigation.map((n) => ({
                ...n,
                subItems: n.subItems?.filter((s) => {
                  // Git Servers is admin / org-manager only.
                  if (s.id === 'mgmt-gitservers') return false;
                  // A user who reaches this section only via _example_manager
                  // (no org/family/lecturer access) sees just the example links.
                  if (!showManagement) return s.id === 'mgmt-examples' || s.id === 'mgmt-example-repos';
                  return true;
                }),
              })),
        )}
      {isUserManager && renderNavItems(userMgmtNavigation)}
      {isWorkspaceUser && renderNavItems(getWorkspacesNavigation(isWorkspaceMaintainer))}
      {isServiceManager && renderNavItems(servicesNavigation)}
      {isAdmin && renderNavItems(adminNavigation)}
    </SidebarShell>
  );
}

/**
 * The sidebar's fixed chrome — collapse header, scrolling nav, logo footer.
 *
 * Both navigation modes (course context and the default app nav) render the
 * exact same frame and differ only in what goes inside <nav>, so the frame
 * lives here once and each mode passes its items as children.
 */
function SidebarShell({
  collapsed,
  setCollapsed,
  user,
  children,
}: {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
  user: { givenName?: string; familyName?: string } | null | undefined;
  children: React.ReactNode;
}) {
  return (
    <aside
      className={`${
        collapsed ? 'w-16' : 'w-64'
      } bg-surface border-r border-rule transition-all duration-300 flex flex-col print:hidden`}
    >
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-rule">
        {!collapsed && (
          <Link href="/dashboard" className="flex-1 min-w-0 hover:bg-canvas rounded px-2 py-1 -mx-2 -my-1 transition-colors cursor-pointer">
            <p className="text-sm font-semibold text-fg truncate">
              {user?.givenName} {user?.familyName}
            </p>
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded-lg hover:bg-sunken transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            className={`h-5 w-5 text-muted transition-transform ${collapsed ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <nav className="flex-1 p-2 space-y-1 overflow-y-auto scroll-slim">{children}</nav>

      {/* Footer - Logo & Version */}
      <div className="p-4 border-t border-rule">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center justify-center space-x-2">
              <Image src="/computor_logo.png" alt="Computor" width={24} height={24} className="h-6 w-6" />
              <span className="text-sm font-semibold text-body">Computor</span>
            </div>
            <p className="text-xs text-muted text-center" title="Running version (git commit)">{APP_VERSION}</p>
          </div>
        ) : (
          <div className="flex justify-center">
            <Image src="/computor_logo.png" alt="Computor" width={32} height={32} className="h-8 w-8" />
          </div>
        )}
      </div>
    </aside>
  );
}
