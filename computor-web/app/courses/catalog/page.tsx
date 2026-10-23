'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { UserClient } from '@/src/generated/clients/UserClient';
import { useResource } from '@/src/hooks/useResource';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
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

const COPY = {
  de: {
    thisCourse: 'diesen Kurs',
    enrolled: (title: string) => `Du bist jetzt Mitglied in ${title}.`,
    enrollFailed: 'Der Beitritt zum Kurs war nicht möglich.',
    courses: 'Kurse',
    catalog: 'Katalog',
    title: 'Kurskatalog',
    subtitle: 'Kurse, denen du selbst beitreten kannst. Du trittst als Studierende(r) bei.',
    emptyTitle: 'Keine Kurse offen für die Selbstanmeldung',
    emptyDescription: 'Ein Kurs erscheint hier, sobald seine Lehrenden ihn freigeben. Frage dort nach oder schau später wieder vorbei.',
    backToCourses: 'Zurück zu deinen Kursen',
    enrolledBadge: 'Angemeldet',
    openCourse: 'Kurs öffnen',
    full: 'Voll',
    seatsLeft: (n: number) => (n === 1 ? '1 Platz frei' : `${n} Plätze frei`),
    join: 'Kurs beitreten',
    confirmTitle: 'Diesem Kurs beitreten?',
    confirmMessage: (title: string) =>
      `Du trittst ${title} als Studierende(r) bei. Auf der Kursseite kannst du den Kurs jederzeit wieder verlassen.`,
    joining: 'Beitritt läuft …',
  },
  en: {
    thisCourse: 'this course',
    enrolled: (title: string) => `You are now enrolled in ${title}.`,
    enrollFailed: 'Could not enrol you in this course.',
    courses: 'Courses',
    catalog: 'Catalog',
    title: 'Course catalog',
    subtitle: 'Courses you can join yourself. Enrolling adds you as a student.',
    emptyTitle: 'No courses are open for self-registration',
    emptyDescription: 'A course appears here once its staff opens it up. Ask them, or check back later.',
    backToCourses: 'Back to your courses',
    enrolledBadge: 'Enrolled',
    openCourse: 'Open course',
    full: 'Full',
    seatsLeft: (n: number) => (n === 1 ? '1 seat left' : `${n} seats left`),
    join: 'Join course',
    confirmTitle: 'Join this course?',
    confirmMessage: (title: string) =>
      `You will be enrolled in ${title} as a student. ` +
      'You can leave the course again at any time from its course page.',
    joining: 'Joining…',
  },
};

export default function CourseCatalogPage() {
  const router = useRouter();
  const notify = useNotify();
  const { refreshPermissions } = useAuth();
  const t = COPY[useUiLanguage()];
  const { data, loading, error, reload } = useResource(
    () => coursesClient.listPublicCoursesCoursesPublicGet({}),
    [],
  );
  const courses = data ?? [];

  // The course awaiting confirmation. Joining is worth one dialog, which also
  // says how to leave again (POST /user/courses/{id}/leave, issues#458).
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
      notify(t.enrolled(displayName(course, t.thisCourse)), 'success');
      setPending(null);
      router.push(`/courses/${course.id}`);
    } catch (err) {
      notify(err instanceof Error ? err.message : t.enrollFailed, 'error');
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
          breadcrumbs={[{ label: t.courses, href: '/courses' }, { label: t.catalog }]}
          title={t.title}
          subtitle={t.subtitle}
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
            title={t.emptyTitle}
            description={t.emptyDescription}
            action={<ButtonLink href="/courses" variant="secondary">{t.backToCourses}</ButtonLink>}
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
                    <Badge color="green" className="shrink-0">{t.enrolledBadge}</Badge>
                  ) : course.organization_title ? (
                    <Badge color="gray" className="max-w-full whitespace-normal wrap-anywhere">{course.organization_title}</Badge>
                  ) : undefined
                }
                footer={
                  course.enrolled ? (
                    <ButtonLink href={`/courses/${course.id}`} size="sm">
                      {t.openCourse}
                    </ButtonLink>
                  ) : (
                    <div className="flex items-center gap-3">
                      {course.full ? (
                        <span className="text-xs text-muted">{t.full}</span>
                      ) : course.seats_left != null ? (
                        <span className="text-xs text-muted">
                          {t.seatsLeft(course.seats_left)}
                        </span>
                      ) : null}
                      <Button
                        size="sm"
                        disabled={course.full === true}
                        onClick={() => setPending(course)}
                      >
                        {t.join}
                      </Button>
                    </div>
                  )
                }
              />
            ))}
          </ScrollArea>
        )}

        <ConfirmDialog
          open={pending !== null}
          title={t.confirmTitle}
          message={t.confirmMessage(displayName(pending, t.thisCourse))}
          confirmLabel={joining ? t.joining : t.join}
          onCancel={() => setPending(null)}
          onConfirm={() => pending && join(pending)}
        />
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
