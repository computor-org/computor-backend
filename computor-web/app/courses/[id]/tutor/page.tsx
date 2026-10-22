'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Panel from '@/src/components/ui/Panel';
import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { listCourseStudents } from '@/src/components/tutor/tutorData';

/** Tutor landing page: what is waiting, and the two places to act on it. */
export default function TutorViewPage() {
  const courseId = useParams().id as string;
  const crumbs = useCourseCrumbs(courseId, 'Tutor');
  const { data, loading, error } = useResource(() => listCourseStudents(courseId), [courseId]);

  const students = data ?? [];
  const waiting = students.filter((s) => (s.ungraded_submissions_count ?? 0) > 0);
  const ungraded = waiting.reduce((n, s) => n + (s.ungraded_submissions_count ?? 0), 0);
  const unread = students.reduce((n, s) => n + (s.unread_message_count ?? 0), 0);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader breadcrumbs={crumbs} title="Tutor" subtitle="Review and grade your students' submissions" />
        <ScrollArea>
          <ErrorBanner>{error}</ErrorBanner>
          {loading ? (
            <div className="h-20 bg-sunken rounded-lg animate-pulse" />
          ) : (
            <StatGrid columns={4}>
              <StatCard label="Students" value={students.length} />
              <StatCard label="Students with ungraded work" value={waiting.length} tone={waiting.length ? 'warning' : 'muted'} />
              <StatCard label="Ungraded submissions" value={ungraded} tone={ungraded ? 'warning' : 'muted'} />
              <StatCard label="Unread messages" value={unread} tone={unread ? 'info' : 'muted'} />
            </StatGrid>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link href={`/courses/${courseId}/tutor/submissions`} className="block">
              <Panel className="hover:border-accent-line transition-colors h-full">
                <h3 className="text-sm font-semibold text-fg">Submissions to review</h3>
                <p className="text-sm text-muted mt-1">
                  Every submission that has not been graded yet, filterable by assignment.
                </p>
              </Panel>
            </Link>
            <Link href={`/courses/${courseId}/tutor/grading`} className="block">
              <Panel className="hover:border-accent-line transition-colors h-full">
                <h3 className="text-sm font-semibold text-fg">Grading by student</h3>
                <p className="text-sm text-muted mt-1">
                  Pick a student, see their assignments, test results and earlier feedback, and grade.
                </p>
              </Panel>
            </Link>
          </div>
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
