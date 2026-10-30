'use client';

import { useState } from 'react';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Badge from '@/src/components/Badge';
import CourseCard, { CourseCardSkeleton, ViewCourseLink } from '@/src/components/courses/CourseCard';
import { ButtonLink } from '@/src/components/ui/Button';
import Toggle from '@/src/components/ui/Toggle';
import { localizedRoleLabel } from '@/src/utils/courseRoles';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const coursesClient = new CoursesClient();

const COPY = {
  de: {
    courses: 'Kurse',
    loadingSubtitle: 'Alle Kurse, auf die du Zugriff hast',
    subtitle: (n: number) => (n === 1 ? '1 Kurs, auf den du Zugriff hast' : `${n} Kurse, auf die du Zugriff hast`),
    showArchived: 'Archivierte anzeigen',
    showArchivedLabel: 'Archivierte Kurse anzeigen',
    browseCatalog: 'Katalog durchsuchen',
    newCourse: 'Neuer Kurs',
    noCourses: 'Keine Kurse gefunden',
    noAccess: 'Im Katalog findest du Kurse, denen du beitreten kannst.',
    browse: 'Katalog durchsuchen',
    archived: 'Archiviert',
  },
  en: {
    courses: 'Courses',
    loadingSubtitle: 'All courses you have access to',
    subtitle: (n: number) => `${n} ${n === 1 ? 'course' : 'courses'} you have access to`,
    showArchived: 'Show archived',
    showArchivedLabel: 'Show archived courses',
    browseCatalog: 'Browse catalog',
    newCourse: 'New course',
    noCourses: 'No courses found',
    noAccess: 'The catalog lists the courses you can join.',
    browse: 'Browse the catalog',
    archived: 'Archived',
  },
};

export default function CoursesPage() {
  const { courseRole, canCreateCourse, hasView, isAdmin } = usePermissions();
  const language = useUiLanguage();
  const t = COPY[language];
  const { data, loading, error } = useResource(() => coursesClient.listCoursesCoursesGet({}), []);
  // The server includes archived courses for staff (students never get them),
  // so staff can still reach one to unarchive or delete it. They are folded
  // away by default: an archived course is over, and the list is for the ones
  // that are not.
  const [showArchived, setShowArchived] = useState(false);
  const isStaff = isAdmin || hasView('lecturer');
  const all = data ?? [];
  const courses = showArchived ? all : all.filter((c) => !c.archived_at);
  const archivedCount = all.length - all.filter((c) => !c.archived_at).length;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.courses }]}
          title={t.courses}
          subtitle={
            loading
              ? t.loadingSubtitle
              : t.subtitle(courses.length)
          }
          actions={
            <>
              {isStaff && (
                <label className="flex items-center gap-2 text-sm text-muted mr-2">
                  <span>{t.showArchived}{archivedCount > 0 ? ` (${archivedCount})` : ''}</span>
                  <Toggle checked={showArchived} onChange={setShowArchived} label={t.showArchivedLabel} />
                </label>
              )}
              <ButtonLink href="/courses/catalog" variant="secondary">
                {t.browseCatalog}
              </ButtonLink>
              {canCreateCourse() && <ButtonLink href="/courses/create">{t.newCourse}</ButtonLink>}
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
            title={t.noCourses}
            description={t.noAccess}
            action={<ButtonLink href="/courses/catalog">{t.browse}</ButtonLink>}
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
                badge={
                  course.archived_at ? (
                    <span className="flex items-center gap-1 shrink-0">
                      <Badge tone="muted">{t.archived}</Badge>
                      {courseRole(course.id) && <Badge tone="info">{localizedRoleLabel(courseRole(course.id)!, language)}</Badge>}
                    </span>
                  ) : undefined
                }
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
