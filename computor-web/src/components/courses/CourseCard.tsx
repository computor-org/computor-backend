'use client';

import Link from 'next/link';
import { ReactNode } from 'react';
import Badge from '@/src/components/Badge';
import CourseWorkspaceLaunchButtons from '@/src/components/workspaces/CourseWorkspaceLaunchButtons';
import { displayName } from '@/src/utils/displayName';

/**
 * One course tile, shared by the course list and the public catalog.
 *
 * The two surfaces differ only in the footer — "View Course" for a course you
 * are in, a Register control for one you are not — so that is the slot, and
 * everything above it stays identical between them. Extracted out of
 * app/courses/page.tsx: palette utilities are only legal under
 * src/components/**, so a card used from app/** has to live here anyway.
 */
export default function CourseCard({
  course,
  role,
  href,
  badge,
  footer,
}: {
  course: { id: string; title?: string | null; path?: string | null; language_code?: string | null; description?: string | null };
  /** Course role, when the viewer has one. Also gates the workspace launchers. */
  role?: string | null;
  /** Where the title links. Omit to render the title as plain text (catalog). */
  href?: string;
  /** Overrides the default role badge. */
  badge?: ReactNode;
  footer?: ReactNode;
}) {
  const body = (
    <>
      <div className="flex items-start justify-between mb-4 gap-2">
        <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
          {displayName(course, 'Untitled Course')}
        </h3>
        {badge ?? (role && <Badge color="blue" className="shrink-0">{role}</Badge>)}
      </div>

      <div className="space-y-2 mb-4 flex-grow">
        {course.description && (
          <p className="text-sm leading-6 text-gray-600 line-clamp-3">{course.description}</p>
        )}
        {course.language_code && (
          <div className="flex items-center text-sm text-gray-600">
            <svg className="h-4 w-4 mr-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
            </svg>
            <span className="uppercase">{course.language_code}</span>
          </div>
        )}
      </div>
    </>
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg transition-all h-full flex flex-col">
      {href ? (
        // The launch buttons live OUTSIDE the Link: nesting them in the anchor
        // would both be invalid HTML and still navigate the card on an icon click.
        <Link href={href} className="flex flex-col flex-grow cursor-pointer">
          {body}
        </Link>
      ) : (
        <div className="flex flex-col flex-grow">{body}</div>
      )}

      {/* Template icon launchers; hides itself when the course offers no
          workspaces. Members only — the fetch would 403 without a role. */}
      {role && <CourseWorkspaceLaunchButtons courseId={course.id} compact className="mb-4" />}

      {footer && (
        <div className="flex items-center justify-end pt-4 border-t border-gray-200 mt-auto gap-3">
          {footer}
        </div>
      )}
    </div>
  );
}

/** The "View Course →" footer used by the course list. */
export function ViewCourseLink({ courseId }: { courseId: string }) {
  return (
    <Link
      href={`/courses/${courseId}`}
      className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center"
    >
      View Course
      <svg className="ml-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </Link>
  );
}

/** Skeleton tile shown while a grid of cards is loading. */
export function CourseCardSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
      <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
      <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
      <div className="h-4 bg-gray-200 rounded w-2/3"></div>
    </div>
  );
}
