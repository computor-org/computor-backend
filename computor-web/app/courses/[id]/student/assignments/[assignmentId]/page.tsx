'use client';

import { useParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { formatUsage } from '@/src/utils/limits';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import DetailPanel from '@/src/components/DetailPanel';
import SectionCard from '@/src/components/SectionCard';
import EmptyState from '@/src/components/EmptyState';
import Badge from '@/src/components/Badge';
import Panel from '@/src/components/ui/Panel';
import Score from '@/src/components/ui/Score';
import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import TestResultTree from '@/src/components/student/TestResultTree';
import type { TestRunResult } from '@/src/components/student/TestResultTree';
import { displayName } from '@/src/utils/displayName';
import type { CourseContentStudentGet } from 'types/generated';

export default function AssignmentDetailPage() {
  const params = useParams();
  const courseId = params.id as string;
  const assignmentId = params.assignmentId as string;

  const { data: assignment, loading, error } = useResource(async () => {
    const response = await apiFetch(`${API_BASE_URL}/students/course-contents/${assignmentId}`);
    if (!response.ok) throw new Error('Failed to fetch assignment');
    return (await response.json()) as CourseContentStudentGet;
  }, [assignmentId]);

  const name = displayName(assignment, 'Assignment');
  const crumbs = useCourseCrumbs(
    courseId,
    { label: 'Assignments', href: `/courses/${courseId}/student/assignments` },
    name,
  );

  const resultData = assignment?.result?.result_json as TestRunResult | undefined;

  return (
    <AuthenticatedLayout>
      <DetailPanel
        breadcrumbs={crumbs}
        title={name}
        loading={loading}
        error={error || (!loading && !assignment ? 'Assignment not found' : null)}
        subtitle={
          assignment && (
            <Badge tone={assignment.submitted ? 'success' : 'warning'}>
              {assignment.submitted ? 'Submitted' : 'Not submitted'}
            </Badge>
          )
        }
      >
        {assignment && (
          <>
            <StatGrid columns={3}>
              <StatCard label="Max group size" value={assignment.max_group_size || 1} />
              <StatCard
                label="Test runs"
                value={formatUsage(assignment.result_count, assignment.max_test_runs)}
              />
              <StatCard
                label="Submissions"
                value={formatUsage(assignment.submission_count, assignment.max_submissions)}
              />
            </StatGrid>

            {assignment.description && (
              <SectionCard title="Description">
                <div className="prose prose-slate max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{assignment.description}</ReactMarkdown>
                </div>
              </SectionCard>
            )}

            <SectionCard
              title="Latest test result"
              action={resultData && <Score value={resultData.result_value ?? 0} decimals={1} />}
            >
              {resultData ? (
                <>
                  <Panel padding="compact" className="bg-gray-50">
                    <div className="flex flex-wrap items-center gap-4 text-sm">
                      <Badge tone={resultData.result === 'PASSED' ? 'success' : 'error'}>
                        {resultData.result ?? 'UNKNOWN'}
                      </Badge>
                      <span className="text-gray-600">
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
          </>
        )}
      </DetailPanel>
    </AuthenticatedLayout>
  );
}
