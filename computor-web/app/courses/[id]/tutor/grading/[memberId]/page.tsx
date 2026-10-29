'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Panel from '@/src/components/ui/Panel';
import Score from '@/src/components/ui/Score';
import Badge from '@/src/components/Badge';
import GradingStatusBadge from '@/src/components/student/gradingStatus';
import GradingPanel from '@/src/components/student/GradingPanel';
import TestResultTree, { type TestRunResult } from '@/src/components/student/TestResultTree';
import TutorGradeForm from '@/src/components/tutor/TutorGradeForm';
import { memberName, tutorsClient } from '@/src/components/tutor/tutorData';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { localizedText } from '@/src/utils/localizedText';
import type { CourseContentStudentList, TutorGradeCreate } from 'types/generated';

const COPY = {
  de: {
    tutor: 'Tutor',
    grading: 'Bewertung',
    student: 'Studierende/r',
    assignments: 'Aufgaben',
    noAssignments: 'Keine Aufgaben.',
    toReview: 'zu prüfen',
    submissions: (n: number) => `${n} ${n === 1 ? 'Abgabe' : 'Abgaben'}`,
    runs: (n: number) => `${n} ${n === 1 ? 'Testlauf' : 'Testläufe'}`,
    testRuns: (n: number) => `${n} ${n === 1 ? 'Testlauf' : 'Testläufe'}`,
    choose: 'Wähle links eine Aufgabe aus.',
    latestResult: 'Letztes Testergebnis:',
    gradeLatest: 'Letzte Abgabe bewerten',
    nothingSubmitted: 'Noch nichts eingereicht.',
    needsSubmission: 'Für die Bewertung ist eine offizielle Abgabe nötig.',
    gradesFeedback: 'Bewertungen und Feedback',
    latestTests: 'Details zum letzten Test',
  },
  en: {
    tutor: 'Tutor',
    grading: 'Grading',
    student: 'Student',
    assignments: 'Assignments',
    noAssignments: 'No assignments.',
    toReview: 'to review',
    submissions: (n: number) => `${n} submission${n === 1 ? '' : 's'}`,
    runs: (n: number) => `${n} runs`,
    testRuns: (n: number) => `${n} test runs`,
    choose: 'Choose an assignment on the left.',
    latestResult: 'Latest test result:',
    gradeLatest: 'Grade the latest submission',
    nothingSubmitted: 'Nothing submitted yet.',
    needsSubmission: 'Grading needs an official submission.',
    gradesFeedback: 'Grades and feedback',
    latestTests: 'Latest test details',
  },
};

/** Read `?content=` once on the client; avoids a Suspense boundary for useSearchParams. */
function initialContent(): string | null {
  if (typeof window === 'undefined') return null;
  return new URLSearchParams(window.location.search).get('content');
}

function isAssignment(c: CourseContentStudentList): boolean {
  return c.course_content_kind_id !== 'unit';
}

/**
 * One student's assignments for a tutor: the latest test result, earlier
 * grades and feedback, and the form to grade the latest submission.
 */
export default function TutorStudentGradingPage() {
  const params = useParams();
  const language = useUiLanguage();
  const t = COPY[language];
  const courseId = params.id as string;
  const memberId = params.memberId as string;
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    // Deep link from the submissions queue (?content=<id>).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(initialContent());
  }, []);

  const member = useResource(
    () => tutorsClient.tutorGetCourseMembersEndpointTutorsCourseMembersCourseMemberIdGet({ courseMemberId: memberId }),
    [memberId],
  );
  const contents = useResource(
    () => tutorsClient.tutorListCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsGet({ courseMemberId: memberId }),
    [memberId],
  );
  const detail = useResource(
    () =>
      selected
        ? tutorsClient.tutorGetCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdGet({
            courseMemberId: memberId,
            courseContentId: selected,
          })
        : Promise.resolve(null),
    [memberId, selected],
  );

  const name = member.data ? memberName(member.data, language) : t.student;
  const crumbs = useCourseCrumbs(
    courseId,
    { label: t.tutor, href: `/courses/${courseId}/tutor` },
    { label: t.grading, href: `/courses/${courseId}/tutor/grading` },
    name,
  );

  const assignments = (contents.data ?? []).filter(isAssignment).sort((a, b) => a.path.localeCompare(b.path));
  const item = detail.data;
  const group = item?.submission_group ?? null;
  const resultJson = item?.result?.result_json as TestRunResult | undefined;

  function select(id: string) {
    setSelected(id);
    const url = new URL(window.location.href);
    url.searchParams.set('content', id);
    window.history.replaceState(null, '', url.toString());
  }

  async function grade(body: TutorGradeCreate) {
    if (!selected) return;
    await tutorsClient.tutorUpdateCourseContentsEndpointTutorsCourseMembersCourseMemberIdCourseContentsCourseContentIdPatch({
      courseMemberId: memberId,
      courseContentId: selected,
      body,
    });
    await Promise.all([detail.refresh(), contents.refresh()]);
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader breadcrumbs={crumbs} title={name} subtitle={member.data?.user?.email ?? undefined} />
        <ScrollArea>
          <ErrorBanner>{member.error || contents.error}</ErrorBanner>
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 items-start">
            <Panel padding="none">
              <div className="px-4 py-3 border-b border-rule">
                <h3 className="text-sm font-semibold text-fg">{t.assignments}</h3>
              </div>
              {contents.loading ? (
                <div className="h-40 bg-sunken animate-pulse" />
              ) : assignments.length === 0 ? (
                <div className="p-4"><EmptyState compact title={t.noAssignments} /></div>
              ) : (
                <ul className="divide-y divide-rule-soft">
                  {assignments.map((c) => (
                    <li key={c.id}>
                      <button
                        type="button"
                        onClick={() => select(c.id)}
                        className={`w-full text-left px-4 py-2.5 hover:bg-accent-wash/50 ${selected === c.id ? 'bg-accent-wash' : ''}`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium text-fg truncate">{localizedText(c.title_i18n, language, c.title) || c.path}</span>
                          {(c.unreviewed_count ?? 0) > 0 && <Badge tone="warning">{t.toReview}</Badge>}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <Score value={c.result?.result ?? null} />
                          <span className="text-xs text-subtle">
                            {t.submissions(c.submission_count)} · {t.runs(c.result_count)}
                          </span>
                          <GradingStatusBadge status={c.status ?? null} />
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <div className="space-y-4">
              {!selected ? (
                <EmptyState compact title={t.choose} />
              ) : detail.loading ? (
                <div className="h-64 bg-sunken rounded-lg animate-pulse" />
              ) : detail.error ? (
                <ErrorBanner>{detail.error}</ErrorBanner>
              ) : item ? (
                <>
                  <Panel className="space-y-2">
                    <h3 className="text-sm font-semibold text-fg">{localizedText(item.title_i18n, language, item.title) || item.path}</h3>
                    <p className="text-sm text-muted">
                      {t.latestResult} <Score value={item.result?.result ?? null} decimals={1} /> ·{' '}
                      {t.submissions(item.submission_count)} ·{' '}
                      {t.testRuns(item.result_count)}
                    </p>
                  </Panel>

                  <Panel className="space-y-3">
                    <h3 className="text-sm font-semibold text-fg">{t.gradeLatest}</h3>
                    {group?.latest_submitted_artifact_id ? (
                      <TutorGradeForm
                        key={`${selected}-${group.latest_submitted_artifact_id}`}
                        artifactId={group.latest_submitted_artifact_id}
                        initialPercent={item.result?.result ?? null}
                        onSubmit={grade}
                      />
                    ) : (
                      <EmptyState compact title={t.nothingSubmitted} description={t.needsSubmission} />
                    )}
                  </Panel>

                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-fg">{t.gradesFeedback}</h3>
                    <GradingPanel group={group} submitted={item.submitted} audience="staff" />
                  </div>

                  {resultJson?.tests && resultJson.tests.length > 0 && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold text-fg">{t.latestTests}</h3>
                      <TestResultTree tests={resultJson.tests} />
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
