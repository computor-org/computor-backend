'use client';

import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Panel from '@/src/components/ui/Panel';
import Badge from '@/src/components/Badge';
import { ButtonLink } from '@/src/components/ui/Button';
import CourseCard, { ViewCourseLink } from '@/src/components/courses/CourseCard';
import WorkspaceStatusBadge, { categorizeStatus } from '@/src/components/workspaces/WorkspaceStatusBadge';
import NeedsAttention, { selectNeedsAttention } from '@/src/components/dashboard/NeedsAttention';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { displayName } from '@/src/utils/displayName';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { StudentsClient } from '@/src/generated/clients/StudentsClient';
import { MessagesClient } from '@/src/generated/clients/MessagesClient';
import { CoderClient } from '@/src/clients/CoderClient';

const coursesClient = new CoursesClient();
const studentsClient = new StudentsClient();
const messagesClient = new MessagesClient();
const coderClient = new CoderClient();

/** Section heading with an optional "see all" link. */
function SectionHeading({ title, href, linkLabel }: { title: string; href?: string; linkLabel?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 mb-3">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      {href && (
        <Link href={href} className="text-sm text-accent-text hover:underline shrink-0">
          {linkLabel ?? 'View all'}
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
  const { user } = useAuth();
  const { courseRole } = usePermissions();

  const { data, loading, error } = useResource(async () => {
    const courses = await coursesClient.listCoursesCoursesGet({});
    const courseTitles = new Map(courses.map((c) => [c.id, displayName(c, 'Untitled Course')]));

    // Each of these is optional decoration on the page: a student with no
    // workspace access, or a deployment with messaging disabled, should still
    // get their courses rather than an error banner.
    const [contents, workspaces, announcements] = await Promise.all([
      // No course_id: the backend treats it as "every course this user is in"
      // (student_view.list_course_contents), which is the whole point of this
      // page. Two consequences worth knowing: it also provisions any missing
      // submission groups across all of those courses — idempotent, and the
      // per-course page does the same thing on first visit — and it returns no
      // hidden content even for staff, because _may_see_hidden cannot scope its
      // staff check without a course. Both are the safe directions here.
      studentsClient
        .studentListCourseContentsEndpointStudentsCourseContentsGet({ limit: 500 })
        .catch(() => []),
      coderClient
        .listWorkspaces()
        .then((r) => r.workspaces)
        .catch(() => []),
      messagesClient
        .listMessagesMessagesGet({ scope: 'global', kind: 'announcement', unread: true, limit: 5 })
        .catch(() => []),
    ]);

    return {
      courses,
      attention: selectNeedsAttention(contents, courseTitles),
      workspaces,
      announcements,
    };
  }, []);

  const courses = data?.courses ?? [];
  const attention = data?.attention ?? [];
  const workspaces = data?.workspaces ?? [];
  const announcements = data?.announcements ?? [];
  const runningWorkspaces = workspaces.filter(
    (ws) => categorizeStatus(ws.latest_build_status, ws.latest_build_transition) === 'running',
  );

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Dashboard' }]}
          title={`Welcome back, ${user?.givenName || user?.username}`}
          subtitle={
            loading
              ? undefined
              : attention.length > 0
                ? `${attention.length} ${attention.length === 1 ? 'assignment needs' : 'assignments need'} your attention.`
                : courses.length === 0
                  ? "You're not enrolled in any courses yet."
                  : 'Nothing needs your attention right now.'
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            {announcements.length > 0 && (
              <section>
                <SectionHeading title="Announcements" href="/notifications" />
                <Panel padding="none">
                  <div className="divide-y divide-rule-soft">
                    {announcements.map((m) => (
                      <Link
                        key={m.id}
                        href="/notifications"
                        className="flex items-start gap-3 px-4 py-3 hover:bg-canvas transition-colors"
                      >
                        <Badge tone="info" className="shrink-0 mt-0.5">
                          New
                        </Badge>
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-fg truncate">
                            {m.title || 'Announcement'}
                          </div>
                          <div className="text-xs text-muted line-clamp-2">{m.content}</div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </Panel>
              </section>
            )}

            {attention.length > 0 && (
              <section>
                <SectionHeading title="Needs your attention" />
                <NeedsAttention items={attention} />
              </section>
            )}

            <section>
              <SectionHeading title="Your courses" href="/courses" />
              {courses.length === 0 ? (
                <EmptyState
                  title="No courses yet"
                  description="You do not have access to any courses yet."
                  action={<ButtonLink href="/courses/catalog">Browse the catalog</ButtonLink>}
                />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {courses.slice(0, 6).map((course) => (
                    <CourseCard
                      key={course.id}
                      course={course}
                      role={courseRole(course.id)}
                      href={`/courses/${course.id}`}
                      footer={<ViewCourseLink courseId={course.id} />}
                    />
                  ))}
                </div>
              )}
            </section>

            {runningWorkspaces.length > 0 && (
              <section>
                <SectionHeading title="Your workspaces" href="/workspaces" />
                <Panel padding="none">
                  <div className="divide-y divide-rule-soft">
                    {runningWorkspaces.map((ws) => (
                      <div key={ws.id} className="flex items-center gap-3 px-4 py-3">
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium text-fg truncate">{ws.name}</div>
                          <div className="text-xs text-muted truncate">{ws.template_name}</div>
                        </div>
                        <WorkspaceStatusBadge
                          status={ws.latest_build_status}
                          transition={ws.latest_build_transition}
                        />
                      </div>
                    ))}
                  </div>
                </Panel>
              </section>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
