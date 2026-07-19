'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import ErrorBanner from '@/src/components/ErrorBanner';
import type { CourseContentStudentGet } from 'types/generated';

/** Shape of the tester's result_json payload (not covered by generated types). */
interface TestSummary {
  passed: number;
  failed: number;
  skipped: number;
  total: number;
}

interface SubtestResult {
  name?: string;
  result?: string;
  resultMessage?: string;
}

interface TestResult {
  name?: string;
  type?: string;
  result?: string;
  summary: TestSummary;
  tests?: SubtestResult[];
}

interface TestRunResult {
  result?: string;
  result_value?: number;
  summary: TestSummary;
  tests?: TestResult[];
}

export default function AssignmentDetailPage() {
  const params = useParams();
  const courseId = params.id as string;
  const assignmentId = params.assignmentId as string;

  const { data: assignment, loading, error } = useResource(async () => {
    const response = await apiFetch(`${API_BASE_URL}/students/course-contents/${assignmentId}`);
    if (!response.ok) throw new Error('Failed to fetch assignment');
    return (await response.json()) as CourseContentStudentGet;
  }, [assignmentId]);

  if (loading) {
    return (
      <AuthenticatedLayout>
        <ListLoading />
      </AuthenticatedLayout>
    );
  }

  if (error || !assignment) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <ErrorBanner>{error || 'Assignment not found'}</ErrorBanner>
        </div>
      </AuthenticatedLayout>
    );
  }

  const resultData = assignment.result?.result_json as TestRunResult | undefined;

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <Link
                href={`/courses/${courseId}/student/assignments`}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                ← Back to Assignments
              </Link>
            </div>
            <div className="flex items-center space-x-3">
              <span
                className="w-6 h-6 rounded-sm flex-shrink-0"
                style={{ backgroundColor: assignment.color || '#3B82F6' }}
              ></span>
              <h1 className="text-3xl font-bold text-gray-900">{assignment.title}</h1>
            </div>
            <p className="mt-2 text-gray-600 font-mono text-sm">{assignment.path}</p>
          </div>

          {/* Submission Status Badge */}
          {assignment.submitted ? (
            <span className="px-4 py-2 text-sm font-medium bg-green-100 text-green-700 rounded-lg">
              ✓ Submitted
            </span>
          ) : (
            <span className="px-4 py-2 text-sm font-medium bg-yellow-100 text-yellow-700 rounded-lg">
              Not Submitted
            </span>
          )}
        </div>

        <ScrollArea className="space-y-6">
        {/* Description */}
        {assignment.description && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Description</h2>
            <div className="prose prose-slate prose-lg max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {assignment.description}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Assignment Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <dt className="text-sm font-medium text-gray-500">Max Group Size</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">{assignment.max_group_size || 1}</dd>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <dt className="text-sm font-medium text-gray-500">Results</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">{assignment.result_count}</dd>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <dt className="text-sm font-medium text-gray-500">Submissions</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">{assignment.submission_count}</dd>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <dt className="text-sm font-medium text-gray-500">Max Test Runs</dt>
            <dd className="mt-1 text-2xl font-semibold text-gray-900">
              {assignment.max_test_runs || 'Unlimited'}
            </dd>
          </div>
        </div>

        {/* Latest Test Result */}
        {assignment.result && resultData && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Latest Test Result</h2>

            {/* Summary */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl font-bold">
                  {resultData.result === 'PASSED' ? '✓' : '✗'} {resultData.result}
                </span>
                <span className="text-3xl font-bold" style={{
                  color: (resultData.result_value ?? 0) >= 50 ? '#10B981' : '#EF4444'
                }}>
                  {(resultData.result_value || 0).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center space-x-6 text-sm">
                <span className="text-green-600">✓ {resultData.summary.passed} passed</span>
                <span className="text-red-600">✗ {resultData.summary.failed} failed</span>
                {resultData.summary.skipped > 0 && (
                  <span className="text-yellow-600">⊘ {resultData.summary.skipped} skipped</span>
                )}
                <span className="text-gray-600">Total: {resultData.summary.total}</span>
              </div>
            </div>

            {/* Test Details */}
            <div className="space-y-4">
              {resultData.tests?.map((test, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg">
                  <div className="p-4 bg-gray-50 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <span className="text-xl">
                          {test.result === 'PASSED' ? '✓' : '✗'}
                        </span>
                        <div>
                          <h3 className="font-medium text-gray-900">{test.name}</h3>
                          <p className="text-xs text-gray-500">{test.type}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`text-sm font-medium ${
                          test.result === 'PASSED' ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {test.result}
                        </span>
                        <p className="text-xs text-gray-500">
                          {test.summary.passed}/{test.summary.total} passed
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Sub-tests */}
                  {test.tests && test.tests.length > 0 && (
                    <div className="p-4 space-y-2">
                      {test.tests.map((subtest, subIdx) => (
                        <div
                          key={subIdx}
                          className="flex items-start justify-between py-2 border-b last:border-b-0 border-gray-100"
                        >
                          <div className="flex items-start space-x-2">
                            <span className="text-sm mt-0.5">
                              {subtest.result === 'PASSED' ? '✓' : '✗'}
                            </span>
                            <div>
                              <p className="text-sm font-medium text-gray-900">{subtest.name}</p>
                              {subtest.resultMessage && subtest.result !== 'PASSED' && (
                                <p className="text-xs text-red-600 mt-1">{subtest.resultMessage}</p>
                              )}
                            </div>
                          </div>
                          <span className={`text-xs font-medium ${
                            subtest.result === 'PASSED' ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {subtest.result}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
