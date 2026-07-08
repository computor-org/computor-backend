'use client';

import Link from 'next/link';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Badge from '@/src/components/Badge';
import type { CourseList } from 'types/generated';

const coursesClient = new CoursesClient();

export default function CoursesPage() {
  const { courseRole, canCreateCourse } = usePermissions();
  const { data, loading, error } = useResource(() => coursesClient.listCoursesCoursesGet({}), []);
  const courses = data ?? [];

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Courses' }]}
          title="Courses"
          subtitle="Browse and access all courses where you have permissions"
          actions={
            <>
              {!loading && (
                <span className="text-sm text-gray-500">
                  {courses.length} {courses.length === 1 ? 'course' : 'courses'}
                </span>
              )}
              {canCreateCourse() && (
                <Link href="/courses/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                  New Course
                </Link>
              )}
            </>
          }
        />

        {/* Error State */}
        <ErrorBanner>{error}</ErrorBanner>

        {/* Loading State */}
        {loading && (
          <ScrollArea className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 content-start">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
            ))}
          </ScrollArea>
        )}

        {/* Empty State */}
        {!loading && !error && courses.length === 0 && (
          <EmptyState
            icon={
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            }
            title="No courses found"
            description="You do not have access to any courses yet."
          />
        )}

        {/* Courses Grid */}
        {!loading && !error && courses.length > 0 && (
          <ScrollArea className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 content-start">
            {courses.map((course) => (
              <CourseCard key={course.id} course={course} role={courseRole(course.id)} />
            ))}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

function CourseCard({ course, role }: { course: CourseList; role: string | null }) {
  return (
    <Link href={`/courses/${course.id}`}>
      <div className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg transition-all cursor-pointer h-full flex flex-col">
        <div className="flex items-start justify-between mb-4 gap-2">
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
            {course.title || 'Untitled Course'}
          </h3>
          {role && (
            <Badge color="blue" className="shrink-0">
              {role}
            </Badge>
          )}
        </div>

        <div className="space-y-2 mb-4 flex-grow">
          <div className="flex items-center text-sm text-gray-600">
            <svg className="h-4 w-4 mr-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <span className="font-mono text-xs">{course.path}</span>
          </div>
          {course.language_code && (
            <div className="flex items-center text-sm text-gray-600">
              <svg className="h-4 w-4 mr-2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
              </svg>
              <span className="uppercase">{course.language_code}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end pt-4 border-t border-gray-200 mt-auto">
          <span className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center">
            View Course
            <svg className="ml-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </Link>
  );
}
