'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '../utils/apiClient';
import { useAuth } from '../contexts/AuthContext';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * When the current route is a course context (`/courses/{uuid}/...`), fetch the
 * per-course views the user holds (student/tutor/lecturer/management).
 *
 * The segment is only treated as a course id when it is UUID-shaped — static
 * routes like `/courses/create` must not be mistaken for a course (otherwise
 * we'd call `/user/views/create` and 500 on the UUID cast). Course views are
 * left empty on failure; they never fall back to global views, so a non-member
 * isn't shown course-role views they don't hold.
 */
export function useCourseViews(): { currentCourseId: string | null; courseViews: string[] } {
  const pathname = usePathname();
  const { user } = useAuth();
  const [courseViews, setCourseViews] = useState<string[]>([]);

  const courseMatch = pathname.match(/^\/courses\/([^/]+)/);
  const currentCourseId = courseMatch && UUID_RE.test(courseMatch[1]) ? courseMatch[1] : null;

  useEffect(() => {
    if (!user || !currentCourseId) {
      return;
    }
    async function fetchCourseViews() {
      try {
        const response = await apiFetch(`${API_BASE_URL}/user/views/${currentCourseId}`);
        if (response.ok) {
          setCourseViews(await response.json());
        }
      } catch (error) {
        console.error('Failed to fetch course views:', error);
        setCourseViews([]);
      }
    }
    fetchCourseViews();
  }, [currentCourseId, user]);

  return { currentCourseId, courseViews };
}
