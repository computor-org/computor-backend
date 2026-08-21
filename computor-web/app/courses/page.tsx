'use client';

import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import CourseCard, { CourseCardSkeleton, ViewCourseLink } from '@/src/components/courses/CourseCard';
import { ButtonLink } from '@/src/components/ui/Button';

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
          subtitle={
            loading
              ? 'Browse and access all courses where you have permissions'
              : `${courses.length} ${courses.length === 1 ? 'course' : 'courses'} where you have permissions`
          }
          actions={
            <>
              <ButtonLink href="/courses/catalog" variant="secondary">
                Browse catalog
              </ButtonLink>
              {canCreateCourse() && <ButtonLink href="/courses/create">New course</ButtonLink>}
            </>
          }
        />

        {/* Error State */}
        <ErrorBanner>{error}</ErrorBanner>

        {/* Loading State */}
        {loading && (
          <ScrollArea spacing="none" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 content-start">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <CourseCardSkeleton key={i} />
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
            action={<ButtonLink href="/courses/catalog">Browse the catalog</ButtonLink>}
          />
        )}

        {/* Courses Grid */}
        {!loading && !error && courses.length > 0 && (
          <ScrollArea spacing="none" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 content-start">
            {courses.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                role={courseRole(course.id)}
                href={`/courses/${course.id}`}
                footer={<ViewCourseLink courseId={course.id} />}
              />
            ))}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
