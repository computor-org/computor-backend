'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiFetch } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseContentStudentGet } from 'types/generated';

export default function AssignmentDetailPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const params = useParams();
  const courseId = params.id as string;
  const assignmentId = params.assignmentId as string;
  const [assignment, setAssignment] = useState<CourseContentStudentGet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Don't fetch until authentication is confirmed
    if (authLoading || !isAuthenticated) {
      return;
    }

    async function fetchAssignment() {
      try {
        const response = await apiFetch(
          `${process.env.NEXT_PUBLIC_API_URL}/students/course-contents/${assignmentId}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch assignment');
        }

        const data = await response.json();
        setAssignment(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchAssignment();
  }, [assignmentId, authLoading, isAuthenticated]);

  if (loading) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  if (error || !assignment) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">{error || 'Assignment not found'}</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const resultData = assignment.result?.result_json as any;

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <Link
                href={`/courses/${courseId}/student/course-contents`}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                ← Back to Course Contents
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

        {/* Repository */}
        {assignment.submission_group?.repository && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Repository</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Full Path:</span>
                <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">
                  {assignment.submission_group.repository.full_path}
                </code>
              </div>
              <div className="flex items-center space-x-3">
                <a
                  href={assignment.submission_group.repository.web_url || undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                >
                  Open in GitLab
                </a>
                <button
                  onClick={() => navigator.clipboard.writeText(assignment.submission_group!.repository!.clone_url!)}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm"
                >
                  Copy Clone URL
                </button>
              </div>
            </div>
          </div>
        )}

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
                  color: resultData.result_value >= 50 ? '#10B981' : '#EF4444'
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
              {resultData.tests?.map((test: any, idx: number) => (
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
                      {test.tests.map((subtest: any, subIdx: number) => (
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

        {/* Deployment Info */}
        {assignment.deployment && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Deployment</h2>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Example Identifier</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono">
                  {assignment.deployment.example_identifier}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Version Tag</dt>
                <dd className="mt-1 text-sm text-gray-900">{assignment.deployment.version_tag}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1">
                  <span className={`px-2 py-1 text-xs font-medium rounded ${
                    assignment.deployment.deployment_status === 'deployed'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {assignment.deployment.deployment_status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Deployed At</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {assignment.deployment.deployed_at
                    ? new Date(assignment.deployment.deployed_at).toLocaleString()
                    : 'N/A'}
                </dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
