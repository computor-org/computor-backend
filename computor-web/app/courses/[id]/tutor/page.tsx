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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { listCourseStudents } from '@/src/components/tutor/tutorData';

const COPY = {
  de: {
    title: 'Tutor',
    subtitle: 'Abgaben deiner Studierenden prüfen und bewerten',
    students: 'Studierende',
    withUngraded: 'Studierende mit unbewerteten Abgaben',
    ungraded: 'Unbewertete Abgaben',
    unread: 'Ungelesene Nachrichten',
    reviewTitle: 'Abgaben zur Prüfung',
    reviewText: 'Alle Abgaben, die noch nicht bewertet sind, filterbar nach Aufgabe.',
    gradingTitle: 'Bewertung nach Studierenden',
    gradingText: 'Wähle eine Person aus, sieh dir ihre Aufgaben, Testergebnisse und frühere Rückmeldungen an und bewerte.',
  },
  en: {
    title: 'Tutor',
    subtitle: "Review and grade your students' submissions",
    students: 'Students',
    withUngraded: 'Students with ungraded work',
    ungraded: 'Ungraded submissions',
    unread: 'Unread messages',
    reviewTitle: 'Submissions to review',
    reviewText: 'Every submission that has not been graded yet, filterable by assignment.',
    gradingTitle: 'Grading by student',
    gradingText: 'Pick a student, see their assignments, test results and earlier feedback, and grade.',
  },
};

/** Tutor landing page: what is waiting, and the two places to act on it. */
export default function TutorViewPage() {
  const courseId = useParams().id as string;
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, t.title);
  const { data, loading, error } = useResource(() => listCourseStudents(courseId), [courseId]);

  const students = data ?? [];
  const waiting = students.filter((s) => (s.ungraded_submissions_count ?? 0) > 0);
  const ungraded = waiting.reduce((n, s) => n + (s.ungraded_submissions_count ?? 0), 0);
  const unread = students.reduce((n, s) => n + (s.unread_message_count ?? 0), 0);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader breadcrumbs={crumbs} title={t.title} subtitle={t.subtitle} />
        <ScrollArea>
          <ErrorBanner>{error}</ErrorBanner>
          {loading ? (
            <div className="h-20 bg-sunken rounded-lg animate-pulse" />
          ) : (
            <StatGrid columns={4}>
              <StatCard label={t.students} value={students.length} />
              <StatCard label={t.withUngraded} value={waiting.length} tone={waiting.length ? 'warning' : 'muted'} />
              <StatCard label={t.ungraded} value={ungraded} tone={ungraded ? 'warning' : 'muted'} />
              <StatCard label={t.unread} value={unread} tone={unread ? 'info' : 'muted'} />
            </StatGrid>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link href={`/courses/${courseId}/tutor/submissions`} className="block">
              <Panel className="hover:border-accent-line transition-colors h-full">
                <h3 className="text-sm font-semibold text-fg">{t.reviewTitle}</h3>
                <p className="text-sm text-muted mt-1">
                  {t.reviewText}
                </p>
              </Panel>
            </Link>
            <Link href={`/courses/${courseId}/tutor/grading`} className="block">
              <Panel className="hover:border-accent-line transition-colors h-full">
                <h3 className="text-sm font-semibold text-fg">{t.gradingTitle}</h3>
                <p className="text-sm text-muted mt-1">
                  {t.gradingText}
                </p>
              </Panel>
            </Link>
          </div>
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
