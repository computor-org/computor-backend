'use client';

import Link from 'next/link';
import { useEffect, useRef } from 'react';
import type { CourseWorkspaceLauncher } from '@/src/components/workspaces/CourseWorkspaceLaunchButtons';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Panel from '@/src/components/ui/Panel';
import Badge from '@/src/components/Badge';
import { ButtonLink } from '@/src/components/ui/Button';
import CourseCard, { ViewCourseLink } from '@/src/components/courses/CourseCard';
import NeedsAttention, {
  DEFAULT_REASONS,
  selectNeedsAttention,
} from '@/src/components/dashboard/NeedsAttention';
import InviteFriendCard from '@/src/components/dashboard/InviteFriendCard';
import DashboardWorkspaces from '@/src/components/dashboard/DashboardWorkspaces';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useResource } from '@/src/hooks/useResource';
import { displayName } from '@/src/utils/displayName';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { StudentsClient } from '@/src/generated/clients/StudentsClient';
import { MessagesClient } from '@/src/generated/clients/MessagesClient';
import { CourseWorkspacesClient } from '@/src/clients/CourseWorkspacesClient';
import { CoderClient } from '@/src/clients/CoderClient';

const coursesClient = new CoursesClient();
const studentsClient = new StudentsClient();
const messagesClient = new MessagesClient();
const coderClient = new CoderClient();
const courseWorkspacesClient = new CourseWorkspacesClient();

const COPY = {
  de: {
    dashboard: 'Übersicht',
    viewAll: 'Alle anzeigen',
    untitledCourse: 'Kurs ohne Titel',
    course: 'Kurs',
    welcome: (name?: string) => `Willkommen, ${name}`,
    welcomeBack: (name?: string) => `Willkommen zurück, ${name}`,
    sentBack: (n: number) =>
      n === 1 ? '1 Aufgabe wurde von Tutoren zurückgegeben.' : `${n} Aufgaben wurden von Tutoren zurückgegeben.`,
    notEnrolled: 'Du bist noch in keinem Kurs.',
    nothingSentBack: 'Dir wurde keine Aufgabe zur Korrektur zurückgegeben.',
    announcements: 'Ankündigungen',
    new: 'Neu',
    announcement: 'Ankündigung',
    yourCourses: 'Deine Kurse',
    noCourses: 'Noch keine Kurse',
    noAccess: 'Im Katalog findest du Kurse, denen du beitreten kannst.',
    browse: 'Katalog durchsuchen',
    sentBackHeading: 'Zur Korrektur zurückgegeben',
    workspaces: 'Deine Arbeitsumgebungen',
  },
  en: {
    dashboard: 'Dashboard',
    viewAll: 'View all',
    untitledCourse: 'Untitled Course',
    course: 'Course',
    welcome: (name?: string) => `Welcome, ${name}`,
    welcomeBack: (name?: string) => `Welcome back, ${name}`,
    sentBack: (n: number) => `${n} ${n === 1 ? 'assignment' : 'assignments'} sent back by a tutor.`,
    notEnrolled: "You're not enrolled in any courses yet.",
    nothingSentBack: 'No assignment has been sent back to you for correction.',
    announcements: 'Announcements',
    new: 'New',
    announcement: 'Announcement',
    yourCourses: 'Your courses',
    noCourses: 'No courses yet',
    noAccess: 'The catalog lists the courses you can join.',
    browse: 'Browse the catalog',
    sentBackHeading: 'Sent back for correction',
    workspaces: 'Your workspaces',
  },
};

/** Section heading with an optional "see all" link. */
function SectionHeading({ title, href, linkLabel }: { title: string; href?: string; linkLabel?: string }) {
  const t = COPY[useUiLanguage()];
  return (
    <div className="flex items-baseline justify-between gap-3 mb-3">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      {href && (
        <Link href={href} className="text-sm text-accent-text hover:underline shrink-0">
          {linkLabel ?? t.viewAll}
        </Link>
      )}
    </div>
  );
}

/**
 * The signed-in landing page.
 *
 * It used to be a second, smaller copy of /courses, which made it hard to argue
 * it should exist at all — and it had no sidebar entry, so the only ways in were
 * the top-bar logo and the post-login redirect. What earns it a place is the
 * cross-course view no other page offers: /students/course-contents without a
 * course filter answers "what do I still have to do" for every course at once.
 *
 * Each section hides itself when it has nothing, so a lecturer with no student
 * enrolments and no workspaces sees their courses and nothing misleading.
 */
export default function DashboardPage() {
  const { user, isAuthenticated } = useAuth();
  const { courseRole, isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();
  const courseLaunchers = useRef(new Map<string, CourseWorkspaceLauncher>());
  const openAssignment = (courseId: string, contentId: string) => {
    if (isAdmin || isOrganizationManager || !courseHasAtLeast(courseId, '_student') || courseHasAtLeast(courseId, '_tutor')) return false;
    const launcher = courseLaunchers.current.get(courseId);
    if (launcher) launcher.launch(contentId);
    else window.location.assign(`/courses/${courseId}/student/assignments/${contentId}`);
    return true;
  };
  const t = COPY[useUiLanguage()];

  const { data, loading, error } = useResource(async () => {
    const courses = await coursesClient.listCoursesCoursesGet({});

    // Each of these is optional decoration on the page: a student with no
    // workspace access, or a deployment with messaging disabled, should still
    // get their courses rather than an error banner.
    const [contents, announcements] = await Promise.all([
      // No course_id: the backend treats it as "every course this user is in"
      // (student_view.list_course_contents), which is the whole point of this
      // page. Server-side the response is cached per user for 5 minutes and —
      // since _course_content_view_tags — tagged with every course the user is
      // enrolled in, so a tutor grading in any of them evicts it immediately.
      // Without those tags the entry carried no course tag at all and kept
      // serving the pre-grade answer for the rest of its TTL.
      //
      // `status` narrows that to the handful of rows this page can actually
      // render. Unfiltered it fetched every course content the student can see
      // — 172 rows and 455KB on a real account — to draw a list of two, reading
      // about a tenth of the fields. The filter runs in SQL, so the rows are
      // never built; DEFAULT_REASONS is passed rather than hardcoded so the
      // server and `selectNeedsAttention` cannot drift apart. The client-side
      // filter below stays as the source of truth for ordering and for
      // excluding units (whose status is aggregated from these very rows).
      //
      // Two more consequences worth knowing: on a cache MISS this also
      // provisions any missing submission groups across those courses
      // (idempotent, and the per-course page does the same on first visit), and
      // it returns no hidden content even for staff, because _may_see_hidden
      // cannot scope its staff check without a course. Both are safe here.
      studentsClient
        .studentListCourseContentsEndpointStudentsCourseContentsGet({
          limit: 500,
          status: DEFAULT_REASONS.join(','),
        })
        .catch(() => []),
      messagesClient
        .listMessagesMessagesGet({ scope: 'global', kind: 'announcement', unread: true, limit: 5 })
        .catch(() => []),
    ]);

    const courseWorkspaceTemplates = await Promise.all(courses.map(async (course) => {
      const settings = await courseWorkspacesClient.getSettings({ courseId: course.id }).catch(() => null);
      return { courseId: course.id, templates: (settings?.templates ?? []).filter((t) => t.enabled).map((t) => t.template_name) };
    }));

    return {
      courseWorkspaceTemplates,
      courses,
      contents,
      announcements,
    };
  }, []);

  // The launch/editor runs in another tab, so its lifecycle changes must not
  // leave the mounted dashboard showing the pre-launch snapshot. Only poll
  // workspace state; courses, progress and announcements remain one-shot.
  const { data: workspaceData, refresh: refreshWorkspaces } = useResource(
    async () => (await coderClient.listWorkspaces()).workspaces,
    [],
    { refetchInterval: 3000 },
  );
  useEffect(() => {
    if (!isAuthenticated) return;
    const onFocus = () => { void refreshWorkspaces(); };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [isAuthenticated, refreshWorkspaces]);

  const courses = data?.courses ?? [];
  const courseTitles = new Map(courses.map((c) => [c.id, displayName(c, t.untitledCourse)]));
  const attention = selectNeedsAttention(Array.isArray(data?.contents) ? data.contents : [], courseTitles, DEFAULT_REASONS, t.course);
  const workspaces = workspaceData ?? [];
  const announcements = data?.announcements ?? [];
  // Every state, not just running: a workspace stops after an hour without
  // use, so the one a returning learner comes back for is usually stopped.
  // Only a workspace being deleted is left out.
  const ownWorkspaces = workspaces.filter((ws) => ws.latest_build_transition !== 'delete');

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.dashboard }]}
          title={(courses.length > 0 || ownWorkspaces.length > 0 ? t.welcomeBack : t.welcome)(user?.givenName || user?.username)}
          subtitle={
            loading
              ? undefined
              : attention.length > 0
                ? t.sentBack(attention.length)
                : courses.length === 0
                  ? t.notEnrolled
                  : t.nothingSentBack
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            {announcements.length > 0 && (
              <section>
                <SectionHeading title={t.announcements} href="/notifications" />
                <Panel padding="none">
                  <div className="divide-y divide-rule-soft">
                    {announcements.map((m) => (
                      <Link
                        key={m.id}
                        href="/notifications"
                        className="flex items-start gap-3 px-4 py-3 hover:bg-canvas transition-colors"
                      >
                        <Badge tone="info" className="shrink-0 mt-0.5">
                          {t.new}
                        </Badge>
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-fg truncate">
                            {m.title || t.announcement}
                          </div>
                          <div className="text-xs text-muted line-clamp-2">{m.content}</div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </Panel>
              </section>
            )}

            {ownWorkspaces.length > 0 && (
              <section>
                <SectionHeading title={t.workspaces} href="/workspaces" />
                <DashboardWorkspaces workspaces={ownWorkspaces} courseTitles={courseTitles} courseTemplates={data?.courseWorkspaceTemplates ?? []} />
              </section>
            )}

            <section>
              <SectionHeading title={t.yourCourses} href="/courses" />
              {courses.length === 0 ? (
                <EmptyState
                  title={t.noCourses}
                  description={t.noAccess}
                  action={<ButtonLink href="/courses/catalog">{t.browse}</ButtonLink>}
                />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {courses.slice(0, 6).map((course) => (
                    <CourseCard
                      key={course.id}
                      course={course}
                      workspaceLauncherRef={(launcher) => {
                        if (launcher) courseLaunchers.current.set(course.id, launcher);
                        else courseLaunchers.current.delete(course.id);
                      }}
                      role={courseRole(course.id)}
                      href={`/courses/${course.id}`}
                      footer={<ViewCourseLink courseId={course.id} />}
                    />
                  ))}
                </div>
              )}
            </section>

            {attention.length > 0 && (
              <section>
                <SectionHeading title={t.sentBackHeading} />
                <NeedsAttention items={attention} onOpenAssignment={openAssignment} />
              </section>
            )}

            <InviteFriendCard />
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
