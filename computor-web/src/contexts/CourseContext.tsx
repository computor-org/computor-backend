'use client';

import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { useResource } from '@/src/hooks/useResource';
import { displayName } from '@/src/utils/displayName';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import type { CourseGet } from 'types/generated';

const coursesClient = new CoursesClient();

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Only treat the segment as a course id when it is UUID-shaped: static routes
 * like `/courses/create` and `/courses/catalog` must not be fetched as a bogus
 * course, which the backend answers with a 400 (VAL_001) on the UUID cast.
 * Same guard as useCourseViews and TopBar, which is part of why this exists.
 */
function courseIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/courses\/([^/]+)/);
  return match && UUID_RE.test(match[1]) ? match[1] : null;
}

interface CourseContextValue {
  /** The course in the current route, or null outside a course. */
  courseId: string | null;
  course: CourseGet | null;
  loading: boolean;
  /** The resolved name, falling back while the fetch is in flight. */
  courseName: string;
  /** Re-fetch — for a page that just edited the course. */
  reload: () => void;
}

const CourseContext = createContext<CourseContextValue>({
  courseId: null,
  course: null,
  loading: false,
  courseName: 'Course',
  reload: () => {},
});

/**
 * The course the current route is about, fetched once.
 *
 * Eight places were fetching the same course purely to put its title in a
 * breadcrumb or a header — six pages, the grading view and the top bar — which
 * meant up to two identical requests per navigation and four different fallback
 * strings when one of them failed. One of those fallbacks was the literal word
 * "Course", rendered in a breadcrumb where the course's name belonged.
 *
 * Mounted inside AuthenticatedLayout rather than a route layout so it covers the
 * top bar too, and derived from the pathname rather than route params so a
 * single mount point serves every page. Outside a course route it holds nulls
 * and issues no request.
 */
export function CourseProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const courseId = courseIdFromPath(pathname);

  const { data, loading, reload } = useResource(
    () => coursesClient.getCoursesCoursesIdGet({ id: courseId as string }),
    [courseId],
    { enabled: courseId != null },
  );

  // A stale course from the previously-visited course must never leak into the
  // next one's header, so gate the value on the id the route currently names.
  const course = courseId && data?.id === courseId ? data : null;

  const value = useMemo<CourseContextValue>(
    () => ({
      courseId,
      course,
      loading: courseId != null && loading,
      courseName: displayName(course, 'Course'),
      reload,
    }),
    [courseId, course, loading, reload],
  );

  return <CourseContext.Provider value={value}>{children}</CourseContext.Provider>;
}

/** The current route's course. Safe outside a course route — everything is null. */
export function useCourse(): CourseContextValue {
  return useContext(CourseContext);
}

/**
 * The course's name for a header or breadcrumb.
 *
 * Takes the id the caller already has so a page cannot accidentally render the
 * previous course's name during a transition; returns the fallback until the
 * context is holding that exact course.
 */
export function useCourseName(courseId?: string, fallback = 'Course'): string {
  const { course } = useCourse();
  const match = courseId == null || course?.id === courseId;
  return match ? displayName(course, fallback) : fallback;
}

/** Stable no-op-safe reload, for a page that mutates the course. */
export function useReloadCourse(): () => void {
  const { reload } = useCourse();
  return useCallback(() => reload(), [reload]);
}
