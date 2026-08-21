'use client';

import { useMemo } from 'react';
import { useCourse } from '@/src/contexts/CourseContext';
import type { Crumb } from '@/src/components/Breadcrumbs';

/**
 * The breadcrumb trail for any page inside a course.
 *
 * There were four shapes in use within a single course, and the trail told you
 * something different about the app's structure on each page:
 *
 *   Courses / <Course> / Lecturer View / Assignments   (assignments, templates)
 *   Courses / <Course> / Course Members                (members, groups)
 *   Courses / Assignments / <Content>                  (assignment edit)
 *   Courses / Assignments                              (student assignments)
 *
 * plus one that rendered the literal word "Course" where the course's name
 * belonged, and two detail pages with no trail at all.
 *
 * One shape now: `Courses / <Course> / <Section> [/ <Item>]`.
 *
 * "Lecturer View" is deliberately gone. It linked to `/courses/{id}/lecturer`,
 * which is a bare redirect to the section's first sub-page — so clicking the
 * parent crumb from Assignments landed you on Grading, a sibling. A crumb has to
 * be an ancestor; the course is the real one.
 */
export function useCourseCrumbs(courseId: string, ...tail: (Crumb | string | null | undefined)[]): Crumb[] {
  const { course, courseName } = useCourse();
  // Named so the dependency is the resolved string, not the object identity —
  // the course object is replaced on every reload even when the name is the same.
  const name = course?.id === courseId ? courseName : 'Course';

  return useMemo(
    () => [
      { label: 'Courses', href: '/courses' },
      { label: name, href: `/courses/${courseId}` },
      ...tail
        .filter((c): c is Crumb | string => c != null)
        .map((c) => (typeof c === 'string' ? { label: c } : c)),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [courseId, name, JSON.stringify(tail)],
  );
}

export default useCourseCrumbs;
