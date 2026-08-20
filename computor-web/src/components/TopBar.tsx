'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { useCourse } from '@/src/contexts/CourseContext';
import { MessagesClient } from '@/src/generated/clients/MessagesClient';
import Avatar from './Avatar';

const messagesClient = new MessagesClient();

export default function TopBar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { courseId: currentCourseId, course } = useCourse();
  const courseTitle = course ? course.title || 'Untitled Course' : null;
  const [avatar, setAvatar] = useState<{ color: number | null; image: string | null }>({ color: null, image: null });
  const [unreadCount, setUnreadCount] = useState(0);

  // Unread global announcements drive the bell badge. Re-fetched on navigation,
  // so the count clears after /notifications opens (which marks them read).
  //
  // /messages/counts returns the number; the previous version fetched up to 50
  // message rows and measured the array, so a 51st unread announcement did not
  // move the badge and every navigation pulled a page of message bodies to
  // render a single integer.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const counts = await messagesClient.getMessageCountsMessagesCountsGet({});
        if (!cancelled) {
          const global = (counts.counts ?? []).find((c) => c.scope === 'global');
          setUnreadCount(global?.unread ?? 0);
        }
      } catch {
        /* leave the count as-is */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, pathname]);

  // Pull the profile's avatar (color / image) once so the badge matches /profile.
  // Falls back silently to colored initials if it can't be fetched.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`${API_BASE_URL}/user`);
        if (!cancelled && res.ok) {
          const data = await res.json();
          setAvatar({ color: data?.profile?.avatar_color ?? null, image: data?.profile?.avatar_image ?? null });
        }
      } catch {
        /* keep initials fallback */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };

  return (
    // No `sticky` — the header is a flex sibling of the scroll container, not
    // inside it, so it never scrolled in the first place and had nothing to
    // stick to. `z-40` stays: it applies to a flex item even when statically
    // positioned, and the profile dropdown below relies on it to paint over the
    // sticky <thead> in list tables.
    <header className="h-16 bg-surface border-b border-rule flex items-center justify-between px-6 z-40 print:hidden">
      {/*
        Where the app's logo and wordmark used to sit. Both are in the sidebar
        footer, and the user's name was here as well as in the sidebar header —
        three restatements of identity above a page header that then repeats the
        course name in its breadcrumb. What belongs here is the one thing the
        sidebar cannot show: which course you are currently inside.
      */}
      <div className="min-w-0">
        {currentCourseId && courseTitle && (
          <Link
            href={`/courses/${currentCourseId}`}
            className="text-lg font-medium text-body hover:text-fg transition-colors truncate block"
          >
            {courseTitle}
          </Link>
        )}
      </div>

      {/* Right Side - Notifications & User Menu */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Notifications — global announcements */}
        <button
          onClick={() => router.push('/notifications')}
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
          className="p-2 text-muted hover:text-body hover:bg-sunken rounded-lg transition-colors relative"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[1.1rem] h-[1.1rem] px-1 flex items-center justify-center text-[0.65rem] font-semibold text-on-accent bg-red-500 rounded-full">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </button>

        {/* User Menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label="User menu"
            className="flex items-center gap-1.5 p-2 rounded-lg hover:bg-sunken transition-colors"
          >
            {/* Avatar */}
            <Avatar
              size="sm"
              name={`${user?.givenName ?? ''} ${user?.familyName ?? ''}`}
              fallback={user?.username}
              avatarColor={avatar.color}
              avatarImage={avatar.image}
            />
            {/* Chevron */}
            <svg
              className={`h-4 w-4 text-muted transition-transform ${menuOpen ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Dropdown Menu */}
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-surface rounded-lg shadow-lg border border-rule py-2">
              {/* User Info Section */}
              <div className="px-4 py-3 border-b border-rule">
                <p className="text-sm font-medium text-fg">
                  {user?.givenName} {user?.familyName}
                </p>
                <p className="text-xs text-muted mt-1">{user?.email}</p>
              </div>

              {/* Menu Items */}
              <div className="py-1">
                <button
                  onClick={() => {
                    setMenuOpen(false);
                    router.push('/profile');
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-body hover:bg-sunken flex items-center space-x-2"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span>My Profile</span>
                </button>

                <button
                  onClick={() => {
                    setMenuOpen(false);
                    router.push('/settings');
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-body hover:bg-sunken flex items-center space-x-2"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>Settings</span>
                </button>
              </div>

              {/* Logout */}
              <div className="border-t border-rule pt-1">
                <button
                  onClick={handleLogout}
                  className="w-full px-4 py-2 text-left text-sm text-danger-text hover:bg-danger-wash flex items-center space-x-2"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
