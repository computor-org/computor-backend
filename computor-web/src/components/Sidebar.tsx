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
  getViewNavigation,
  pathMatches,
} from '@/src/config/navigation';

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { isAdmin, isOrganizationManager, isUserManager, isWorkspaceUser, isWorkspaceMaintainer, isExampleManager, showManagement } = usePermissions();
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
                  ? 'bg-blue-50 text-blue-600'
                  : isChildActive
                  ? 'bg-blue-50/50 text-blue-600'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
              title={collapsed ? navItem.label : undefined}
            >
              <span className={isExactActive || isChildActive ? 'text-blue-600' : 'text-gray-500'}>
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
                className="p-2 hover:bg-gray-100 rounded transition-colors"
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
                        ? 'bg-blue-50 text-blue-600 font-medium'
                        : 'text-gray-600 hover:bg-gray-100'
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
      <aside
        className={`${
          collapsed ? 'w-16' : 'w-64'
        } bg-white border-r border-gray-200 transition-all duration-300 flex flex-col print:hidden`}
      >
        {/* Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
          {!collapsed && (
            <Link href="/dashboard" className="flex-1 min-w-0 hover:bg-gray-50 rounded px-2 py-1 -mx-2 -my-1 transition-colors cursor-pointer">
              <p className="text-sm font-semibold text-gray-900 truncate">
                {user?.givenName} {user?.familyName}
              </p>
            </Link>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg
              className={`h-5 w-5 text-gray-600 transition-transform ${collapsed ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        </div>

        {/* Navigation - View-based */}
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {/* Back to Courses Link */}
          <Link
            href="/courses"
            className="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors mb-4"
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
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
            title={collapsed ? 'Overview' : undefined}
          >
            <span className={pathname === `/courses/${currentCourseId}` ? 'text-blue-600' : 'text-gray-500'}>
              {icons.overview}
            </span>
            {!collapsed && <span className="text-sm font-medium">Overview</span>}
          </Link>

          {renderNavItems(availableViews)}
        </nav>

        {/* Footer - Logo & Version */}
        <div className="p-4 border-t border-gray-200">
          {!collapsed ? (
            <div className="space-y-2">
              <div className="flex items-center justify-center space-x-2">
                <Image src="/computor_logo.png" alt="Computor" width={24} height={24} className="h-6 w-6" />
                <span className="text-sm font-semibold text-gray-700">Computor</span>
              </div>
              <p className="text-xs text-gray-500 text-center" title="Running version (git commit)">{APP_VERSION}</p>
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

  // Default navigation
  return (
    <aside
      className={`${
        collapsed ? 'w-16' : 'w-64'
      } bg-white border-r border-gray-200 transition-all duration-300 flex flex-col print:hidden`}
    >
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-200">
        {!collapsed && (
          <Link href="/dashboard" className="flex-1 min-w-0 hover:bg-gray-50 rounded px-2 py-1 -mx-2 -my-1 transition-colors cursor-pointer">
            <p className="text-sm font-semibold text-gray-900 truncate">
              {user?.givenName} {user?.familyName}
            </p>
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            className={`h-5 w-5 text-gray-600 transition-transform ${collapsed ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* Navigation - Main Items */}
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
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
        {isAdmin && renderNavItems(adminNavigation)}
      </nav>

      {/* Footer - Logo & Version */}
      <div className="p-4 border-t border-gray-200">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center justify-center space-x-2">
              <Image src="/computor_logo.png" alt="Computor" width={24} height={24} className="h-6 w-6" />
              <span className="text-sm font-semibold text-gray-700">Computor</span>
            </div>
            <p className="text-xs text-gray-500 text-center" title="Running version (git commit)">{APP_VERSION}</p>
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
