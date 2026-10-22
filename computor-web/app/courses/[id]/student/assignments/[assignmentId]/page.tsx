'use client';

import { useParams } from 'next/navigation';
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
import TestResultTree from '@/src/components/student/TestResultTree';
import type { TestRunResult } from '@/src/components/student/TestResultTree';
import GradingPanel from '@/src/components/student/GradingPanel';
import GradingStatusBadge from '@/src/components/student/gradingStatus';
import TestRunHistory from '@/src/components/student/TestRunHistory';
import PublicLunaPanel from '@/src/components/student/PublicLunaPanel';
import { displayName } from '@/src/utils/displayName';
import {
  descriptionHeading,
  fetchStudentDescription,
  localizedUnitTitle,
  plainHeading,
  resolveContentLanguage,
  withoutLeadingHeading,
} from '@/src/components/student/studentDescription';
import { UserClient } from '@/src/generated/clients/UserClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { StudentsClient } from '@/src/generated/clients/StudentsClient';
import { ResultsClient } from '@/src/generated/clients/ResultsClient';
import { SubmissionsClient } from '@/src/generated/clients/SubmissionsClient';

const studentsClient = new StudentsClient();
const resultsClient = new ResultsClient();
const submissionsClient = new SubmissionsClient();
const userClient = new UserClient();
const coursesClient = new CoursesClient();

/** Profile language if the learner chose one, else the course's, else English. */
async function contentLanguage(courseId: string): Promise<string> {
  const user = await userClient.getCurrentUserEndpointUserGet({}).catch(() => null);
  if (user?.profile?.language_code) return resolveContentLanguage(user.profile.language_code);
  const course = await coursesClient.getCoursesCoursesIdGet({ id: courseId }).catch(() => null);
  return resolveContentLanguage(null, course?.language_code);
}

/**
 * One assignment, as the student sees it.
 *
 * This page used to answer a single question — did my tests pass? — while the
 * grade, the verdict, the grader and their feedback all arrived in the same
 * response and were dropped on the floor. Grading now leads; the automated test
 * result is one section among several, as it is in the VS Code extension.
 */
export default function AssignmentDetailPage() {
  const params = useParams();
  const courseId = params.id as string;
  const assignmentId = params.assignmentId as string;

  const { data, loading, error } = useResource(async () => {
    const assignment = await studentsClient.studentGetCourseContentEndpointStudentsCourseContentsCourseContentIdGet(
      { courseContentId: assignmentId },
    );
    // The released README in the reading language; the stored title and the
    // example's meta description are only the fallback.
    const language = await contentLanguage(courseId);
    const readme = await fetchStudentDescription(assignmentId, language).catch(() => null);
    const submissionGroupId = assignment.submission_group?.id;
    // Nothing has been attempted yet — there is no group to hang runs off.
    if (!submissionGroupId) return { assignment, language, readme, results: [], artifacts: [] };

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
    return { assignment, language, readme, results, artifacts };
  }, [assignmentId, courseId]);

  const assignment = data?.assignment ?? null;
  const group = assignment?.submission_group ?? null;
  const readme = data?.readme ?? null;
  const readmeHeading = descriptionHeading(readme?.markdown);
  const name = readmeHeading ? plainHeading(readmeHeading) : localizedUnitTitle(displayName(assignment, 'Assignment'), data?.language ?? 'en');
  const crumbs = useCourseCrumbs(
    courseId,
    { label: 'Assignments', href: `/courses/${courseId}/student/assignments` },
    name,
  );

  const resultData = assignment?.result?.result_json as TestRunResult | undefined;
  // The typed field is the same number the list page shows; result_json is the
  // fallback for a run whose row predates it. They used to disagree.
  const testScore = assignment?.result?.result ?? resultData?.result_value ?? null;
  // Assignments carry no description of their own — the text belongs to the
  // example version that was deployed onto them.
  // The page title already shows the README heading, so it is not repeated.
  const description = readme
    ? (readmeHeading ? withoutLeadingHeading(readme.markdown) : readme.markdown)
    : assignment?.description || assignment?.deployment?.example_version?.description;
  const repository = group?.repository ?? null;
  const members = group?.members ?? [];

  return (
    <AuthenticatedLayout>
      <DetailPanel
        breadcrumbs={crumbs}
        title={name}
        loading={loading}
        error={error || (!loading && !assignment ? 'Assignment not found' : null)}
        subtitle={
          assignment && (
            <div className="flex flex-wrap items-center gap-2">
              <GradingStatusBadge status={assignment.status} />
              <Badge tone={assignment.submitted ? 'success' : 'warning'}>
                {assignment.submitted ? 'Submitted' : 'Not submitted'}
              </Badge>
              {(assignment.unread_message_count ?? 0) > 0 && (
                <Badge tone="info" title="Unread feedback on this assignment">
                  {assignment.unread_message_count} new
                </Badge>
              )}
              {assignment.visible_effective === false && (
                <Badge tone="muted" title="Students cannot currently see this assignment.">
                  Invisible to students
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
                label="Grade"
                value={formatScore(group?.grading, 1)}
                tone={scoreTone(group?.grading)}
              />
              <StatCard
                label="Latest test result"
                value={formatScore(testScore, 1)}
                tone={scoreTone(testScore)}
              />
              <StatCard
                label="Test runs"
                value={formatUsage(assignment.result_count, assignment.max_test_runs)}
              />
              <StatCard
                label="Submissions"
                value={formatUsage(assignment.submission_count, assignment.max_submissions)}
              />
            </StatGrid>

            <SectionCard title="Grading">
              <GradingPanel group={group} submitted={assignment.submitted} />
            </SectionCard>

            <SectionCard title="Description">
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
                <EmptyState compact title="No description." />
              )}
            </SectionCard>

            <PublicLunaPanel key={assignmentId} assignmentId={assignmentId} />

            <SectionCard
              title="Latest test result"
              action={resultData && <Score value={testScore} decimals={1} />}
            >
              {resultData ? (
                <>
                  <Panel padding="compact" className="bg-canvas">
                    <div className="flex flex-wrap items-center gap-4 text-sm">
                      <Badge tone={resultData.result === 'PASSED' ? 'success' : 'error'}>
                        {resultData.result ?? 'UNKNOWN'}
                      </Badge>
                      <span className="text-muted">
                        {resultData.summary.passed} passed · {resultData.summary.failed} failed
                        {resultData.summary.skipped > 0 && ` · ${resultData.summary.skipped} skipped`}
                        {' · '}
                        {resultData.summary.total} total
                      </span>
                    </div>
                  </Panel>

                  <TestResultTree tests={resultData.tests ?? []} />
                </>
              ) : (
                <EmptyState compact title="No test run yet." description="Run the tests to see results here." />
              )}
            </SectionCard>

            <SectionCard title="Test run history">
              <TestRunHistory results={data?.results ?? []} artifacts={data?.artifacts ?? []} />
            </SectionCard>

            <SectionCard
              title="Your submission"
              action={
                repository?.web_url && (
                  <ButtonLink href={repository.web_url} variant="secondary" size="sm">
                    Open repository
                  </ButtonLink>
                )
              }
            >
              {group ? (
                <>
                  <DescriptionList
                    items={[
                      { term: 'Repository', value: repository?.full_path ?? '—', mono: true },
                      {
                        term: 'Group size',
                        value: `${group.current_group_size ?? members.length} / ${assignment.max_group_size || 1}`,
                      },
                    ]}
                  />
                  {members.length > 1 && (
                    <div className="space-y-1">
                      <h3 className="text-sm font-semibold text-fg">Team members</h3>
                      <ul className="text-sm text-body">
                        {members.map((m) => (
                          <li key={m.id}>{m.full_name || m.username}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <EmptyState compact title="You have not started this assignment yet." />
              )}
            </SectionCard>
          </>
        )}
      </DetailPanel>
    </AuthenticatedLayout>
  );
}
