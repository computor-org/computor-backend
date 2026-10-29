'use client';

import { useParams } from 'next/navigation';
import { usePermissions } from '@/src/hooks/usePermissions';
import CourseWorkspaceLaunchButtons from '@/src/components/workspaces/CourseWorkspaceLaunchButtons';
import ReactMarkdown from 'react-markdown';
import { mathMarkdownPlugins } from '@/src/components/markdownMath';
import { formatUsage } from '@/src/utils/limits';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import DetailPanel from '@/src/components/DetailPanel';
import SectionCard from '@/src/components/SectionCard';
import DescriptionList from '@/src/components/DescriptionList';
import EmptyState from '@/src/components/EmptyState';
import Badge from '@/src/components/Badge';
import Panel from '@/src/components/ui/Panel';
import Score, { formatScore, scoreTone } from '@/src/components/ui/Score';
import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import { ButtonLink } from '@/src/components/ui/Button';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import TestResultTree, { testResultLabel } from '@/src/components/student/TestResultTree';
import type { TestRunResult } from '@/src/components/student/TestResultTree';
import GradingPanel from '@/src/components/student/GradingPanel';
import GradingStatusBadge from '@/src/components/student/gradingStatus';
import TestRunHistory from '@/src/components/student/TestRunHistory';
import PublicLunaPanel from '@/src/components/student/PublicLunaPanel';
import { displayName } from '@/src/utils/displayName';
import {
  descriptionHeading,
  descriptionInLanguage,
  fetchStudentDescription,
  localizedUnitTitle,
  plainHeading,
  withoutLeadingHeading,
} from '@/src/components/student/studentDescription';
import { UserClient } from '@/src/generated/clients/UserClient';
import { StudentsClient } from '@/src/generated/clients/StudentsClient';
import { ResultsClient } from '@/src/generated/clients/ResultsClient';
import { SubmissionsClient } from '@/src/generated/clients/SubmissionsClient';

const studentsClient = new StudentsClient();
const resultsClient = new ResultsClient();
const submissionsClient = new SubmissionsClient();
const userClient = new UserClient();

const COPY = {
  de: {
    assignment: 'Aufgabe',
    assignments: 'Aufgaben',
    notFound: 'Aufgabe nicht gefunden',
    submitted: 'Eingereicht',
    notSubmitted: 'Nicht eingereicht',
    unreadTitle: 'Ungelesenes Feedback zu dieser Aufgabe',
    newCount: (n: number) => `${n} neu`,
    invisible: 'Für Studierende unsichtbar',
    invisibleTitle: 'Studierende können diese Aufgabe derzeit nicht sehen.',
    grade: 'Bewertung',
    latestTestResult: 'Letztes Testergebnis',
    testRuns: 'Testläufe',
    submissions: 'Abgaben',
    grading: 'Bewertung',
    description: 'Beschreibung',
    noDescription: 'Keine Beschreibung.',
    noTestRun: 'Noch kein Testlauf.',
    noTestRunHint: 'Führe die Tests aus, um hier Ergebnisse zu sehen.',
    summary: (passed: number, failed: number) => `${passed} bestanden · ${failed} nicht bestanden`,
    skipped: (n: number) => ` · ${n} übersprungen`,
    total: (n: number) => `${n} gesamt`,
    history: 'Testlauf-Verlauf',
    yourSubmission: 'Deine Abgabe',
    openRepository: 'Repository öffnen',
    repository: 'Repository',
    groupSize: 'Gruppengröße',
    teamMembers: 'Teammitglieder',
    notStarted: 'Du hast diese Aufgabe noch nicht begonnen.',
  },
  en: {
    assignment: 'Assignment',
    assignments: 'Assignments',
    notFound: 'Assignment not found',
    submitted: 'Submitted',
    notSubmitted: 'Not submitted',
    unreadTitle: 'Unread feedback on this assignment',
    newCount: (n: number) => `${n} new`,
    invisible: 'Invisible to students',
    invisibleTitle: 'Students cannot currently see this assignment.',
    grade: 'Grade',
    latestTestResult: 'Latest test result',
    testRuns: 'Test runs',
    submissions: 'Submissions',
    grading: 'Grading',
    description: 'Description',
    noDescription: 'No description.',
    noTestRun: 'No test run yet.',
    noTestRunHint: 'Run the tests to see results here.',
    summary: (passed: number, failed: number) => `${passed} passed · ${failed} failed`,
    skipped: (n: number) => ` · ${n} skipped`,
    total: (n: number) => `${n} total`,
    history: 'Test run history',
    yourSubmission: 'Your submission',
    openRepository: 'Open repository',
    repository: 'Repository',
    groupSize: 'Group size',
    teamMembers: 'Team members',
    notStarted: 'You have not started this assignment yet.',
  },
};

/**
 * One assignment, as the student sees it.
 *
 * This page used to answer a single question — did my tests pass? — while the
 * grade, the verdict, the grader and their feedback all arrived in the same
 * response and were dropped on the floor. Grading now leads; the automated test
 * result is one section among several, as it is in the VS Code extension.
 */
export default function AssignmentDetailPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const params = useParams();
  const courseId = params.id as string;
  const assignmentId = params.assignmentId as string;
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();
  const isOrdinaryLearner = !isAdmin && !isOrganizationManager &&
    courseHasAtLeast(courseId, '_student') && !courseHasAtLeast(courseId, '_tutor');

  const { data, loading, error } = useResource(async () => {
    const [assignment, selfEnrollment] = await Promise.all([
      studentsClient.studentGetCourseContentEndpointStudentsCourseContentsCourseContentIdGet(
        { courseContentId: assignmentId, localize: language },
      ),
      // A course joined through the catalog has no tutors (issues#458), so the
      // grading panel must not promise that one will look at the submission.
      isOrdinaryLearner
        ? userClient.getOwnSelfEnrollmentUserCoursesCourseIdSelfEnrollmentGet({ courseId }).catch(() => null)
        : Promise.resolve(null),
    ]);
    const submissionGroupId = assignment.submission_group?.id;
    // Nothing has been attempted yet — there is no group to hang runs off.
    if (!submissionGroupId) return { assignment, selfEnrollment, results: [], artifacts: [] };

    // The artifacts are only here to say which runs were official submissions;
    // a Result carries the artifact id but not its `submit` flag.
    const [results, artifacts] = await Promise.all([
      resultsClient.listResultsResultsGet({
        courseContentId: assignmentId,
        submissionGroupId,
        limit: 20,
      }),
      submissionsClient.listSubmissionArtifactsSubmissionsArtifactsGet({ submissionGroupId }),
    ]);
    return { assignment, selfEnrollment, results, artifacts };
  }, [assignmentId, courseId, isOrdinaryLearner, language]);
  // The released README in the reading language, the same language as the
  // interface (computor-org/issues#552); the stored title and the example's
  // meta description are only the fallback.
  const { data: readme, loading: readmeLoading } = useResource(
    () => fetchStudentDescription(assignmentId, language).catch(() => null),
    [assignmentId, language],
  );

  const assignment = data?.assignment ?? null;
  const group = assignment?.submission_group ?? null;
  const readmeHeading = descriptionHeading(readme?.markdown);
  const name = readmeHeading ? plainHeading(readmeHeading) : localizedUnitTitle(displayName(assignment, t.assignment), language);
  const crumbs = useCourseCrumbs(
    courseId,
    { label: t.assignments, href: `/courses/${courseId}/student/assignments` },
    name,
  );

  const resultData = assignment?.result?.result_json as TestRunResult | undefined;
  // The typed field is the same number the list page shows; result_json is the
  // fallback for a run whose row predates it. They used to disagree.
  const testScore = assignment?.result?.result ?? resultData?.result_value ?? null;
  // Assignments carry no description of their own — the text belongs to the
  // example version that was deployed onto them.
  // The page title already shows the README heading, so it is not repeated.
  // A unit's own text may hold one section per language (welcome unit).
  const description = readme
    ? (readmeHeading ? withoutLeadingHeading(readme.markdown) : readme.markdown)
    : descriptionInLanguage(assignment?.description, language) || assignment?.deployment?.example_version?.description;
  // What VS Code can open: a released assignment, or a unit with authored text.
  const openable = assignment?.course_id === courseId && assignment.visible_effective !== false && (
    assignment.course_content_kind_id === 'unit'
      ? Boolean(assignment.description?.trim() || assignment.has_deployment || assignment.deployment)
      : Boolean(assignment.has_deployment || assignment.deployment));
  const repository = group?.repository ?? null;
  const members = group?.members ?? [];

  return (
    <AuthenticatedLayout>
      <DetailPanel
        breadcrumbs={crumbs}
        title={name}
        loading={loading || readmeLoading}
        error={error || (!loading && !assignment ? t.notFound : null)}
        // The task stays on this page, as on main; one button opens it in VS Code.
        actions={isOrdinaryLearner && openable ? (
          <CourseWorkspaceLaunchButtons courseId={courseId} courseContentId={assignmentId} compact single />
        ) : undefined}
        subtitle={
          assignment && (
            <div className="flex flex-wrap items-center gap-2">
              <GradingStatusBadge status={assignment.status} />
              <Badge tone={assignment.submitted ? 'success' : 'warning'}>
                {assignment.submitted ? t.submitted : t.notSubmitted}
              </Badge>
              {(assignment.unread_message_count ?? 0) > 0 && (
                <Badge tone="info" title={t.unreadTitle}>
                  {t.newCount(assignment.unread_message_count ?? 0)}
                </Badge>
              )}
              {assignment.visible_effective === false && (
                <Badge tone="muted" title={t.invisibleTitle}>
                  {t.invisible}
                </Badge>
              )}
            </div>
          )
        }
      >
        {assignment && (
          <>
            <StatGrid columns={4}>
              <StatCard
                label={t.grade}
                value={formatScore(group?.grading, 1, language)}
                tone={scoreTone(group?.grading)}
              />
              <StatCard
                label={t.latestTestResult}
                value={formatScore(testScore, 1, language)}
                tone={scoreTone(testScore)}
              />
              <StatCard
                label={t.testRuns}
                value={formatUsage(assignment.result_count, assignment.max_test_runs)}
              />
              <StatCard
                label={t.submissions}
                value={formatUsage(assignment.submission_count, assignment.max_submissions)}
              />
            </StatGrid>

            <SectionCard title={t.grading}>
              <GradingPanel
                group={group}
                submitted={assignment.submitted}
                hasTutors={!data?.selfEnrollment?.self_registered}
              />
            </SectionCard>

            <SectionCard title={t.description}>
              {description ? (
                <div className="prose markdown max-w-none">
                  <ReactMarkdown
                    {...mathMarkdownPlugins}
                    skipHtml
                    components={{
                      img: ({ src, alt }) => {
                        const image = typeof src === 'string' ? readme?.images[src.replace(/^\.\//, '')] : undefined;
                        if (!image) return <span>{alt ?? ''}</span>;
                        // Inline data URL from the released archive; no dimensions are known.
                        // eslint-disable-next-line @next/next/no-img-element
                        return <img src={image} alt={alt ?? ''} className="max-w-full h-auto rounded-md" />;
                      },
                    }}
                  >
                    {description}
                  </ReactMarkdown>
                </div>
              ) : (
                <EmptyState compact title={t.noDescription} />
              )}
            </SectionCard>

            <PublicLunaPanel key={assignmentId} assignmentId={assignmentId} language={language} />

            <SectionCard
              title={t.latestTestResult}
              action={resultData && <Score value={testScore} decimals={1} />}
            >
              {resultData ? (
                <>
                  <Panel padding="compact" className="bg-canvas">
                    <div className="flex flex-wrap items-center gap-4 text-sm">
                      <Badge tone={resultData.result === 'PASSED' ? 'success' : 'error'}>
                        {testResultLabel(resultData.result, language)}
                      </Badge>
                      <span className="text-muted">
                        {t.summary(resultData.summary.passed, resultData.summary.failed)}
                        {resultData.summary.skipped > 0 && t.skipped(resultData.summary.skipped)}
                        {' · '}
                        {t.total(resultData.summary.total)}
                      </span>
                    </div>
                  </Panel>

                  <TestResultTree tests={resultData.tests ?? []} />
                </>
              ) : (
                <EmptyState compact title={t.noTestRun} description={t.noTestRunHint} />
              )}
            </SectionCard>

            <SectionCard title={t.history}>
              <TestRunHistory results={data?.results ?? []} artifacts={data?.artifacts ?? []} />
            </SectionCard>

            <SectionCard
              title={t.yourSubmission}
              action={
                repository?.web_url && (
                  <ButtonLink href={repository.web_url} variant="secondary" size="sm">
                    {t.openRepository}
                  </ButtonLink>
                )
              }
            >
              {group ? (
                <>
                  <DescriptionList
                    items={[
                      { term: t.repository, value: repository?.full_path ?? '—', mono: true },
                      {
                        term: t.groupSize,
                        value: `${group.current_group_size ?? members.length} / ${assignment.max_group_size || 1}`,
                      },
                    ]}
                  />
                  {members.length > 1 && (
                    <div className="space-y-1">
                      <h3 className="text-sm font-semibold text-fg">{t.teamMembers}</h3>
                      <ul className="text-sm text-body">
                        {members.map((m) => (
                          <li key={m.id}>{m.full_name || m.username}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <EmptyState compact title={t.notStarted} />
              )}
            </SectionCard>
          </>
        )}
      </DetailPanel>
    </AuthenticatedLayout>
  );
}
