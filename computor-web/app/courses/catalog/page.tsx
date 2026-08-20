'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { UserClient } from '@/src/generated/clients/UserClient';
import { useResource } from '@/src/hooks/useResource';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Badge from '@/src/components/Badge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import CourseCard, { CourseCardSkeleton } from '@/src/components/courses/CourseCard';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import { displayName } from '@/src/utils/displayName';
import type { CoursePublicList } from 'types/generated';

const coursesClient = new CoursesClient();
const userClient = new UserClient();

export default function CourseCatalogPage() {
  const router = useRouter();
  const notify = useNotify();
  const { refreshPermissions } = useAuth();
  const { data, loading, error, reload } = useResource(
    () => coursesClient.listPublicCoursesCoursesPublicGet({}),
    [],
  );
  const courses = data ?? [];

  // The course awaiting confirmation. Enrolling is a one-way door — there is
  // no self-unenrol endpoint by design — so it is worth one dialog.
  const [pending, setPending] = useState<CoursePublicList | null>(null);
  const [joining, setJoining] = useState(false);

  async function join(course: CoursePublicList) {
    setJoining(true);
    try {
      await userClient.enrollInPublicCourseUserCoursesCourseIdEnrollPost({ courseId: course.id });
      // The backend has already dropped this user's cached principal, so
      // re-pulling scopes now returns the new _student role. Without it the
      // sidebar and role badges would lag the redirect.
      await refreshPermissions();
      notify(`You are now enrolled in ${displayName(course, 'this course')}.`, 'success');
      setPending(null);
      router.push(`/courses/${course.id}`);
    } catch (err) {
      notify(err instanceof Error ? err.message : 'Could not enrol you in this course.', 'error');
      setPending(null);
      reload();
    } finally {
      setJoining(false);
    }
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Courses', href: '/courses' }, { label: 'Catalog' }]}
          title="Course catalog"
          subtitle="Courses you can join yourself. Enrolling adds you as a student."
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading && (
          <ScrollArea spacing="none" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 content-start">
            {[1, 2, 3].map((i) => (
              <CourseCardSkeleton key={i} />
            ))}
          </ScrollArea>
        )}

        {!loading && !error && courses.length === 0 && (
          <EmptyState
            icon={
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            }
            title="No courses are open for self-registration"
            description="A course appears here once its staff opens it up. Ask them, or check back later."
            action={<ButtonLink href="/courses" variant="secondary">Back to your courses</ButtonLink>}
          />
        )}

        {!loading && !error && courses.length > 0 && (
          <ScrollArea spacing="none" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 content-start">
            {courses.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                badge={
                  course.enrolled ? (
                    <Badge color="green" className="shrink-0">Enrolled</Badge>
                  ) : course.organization_title ? (
                    <Badge color="gray" className="shrink-0">{course.organization_title}</Badge>
                  ) : undefined
                }
                footer={
                  course.enrolled ? (
                    <ButtonLink href={`/courses/${course.id}`} size="sm">
                      Open course
                    </ButtonLink>
                  ) : (
                    <Button size="sm" onClick={() => setPending(course)}>
                      Join course
                    </Button>
                  )
                }
              />
            ))}
          </ScrollArea>
        )}

        <ConfirmDialog
          open={pending !== null}
          title="Join this course?"
          message={
            `You will be enrolled in ${displayName(pending, 'this course')} as a student. ` +
            'You cannot remove yourself again — ask the course staff if you change your mind.'
          }
          confirmLabel={joining ? 'Joining…' : 'Join course'}
          onCancel={() => setPending(null)}
          onConfirm={() => pending && join(pending)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
