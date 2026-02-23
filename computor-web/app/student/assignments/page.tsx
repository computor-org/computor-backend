'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';

interface CourseContent {
  id: string;
  title: string;
  description?: string;
  due_date?: string;
  course_id?: string;
  course_name?: string;
  submitted?: boolean;
  grade?: number;
}

export default function StudentAssignmentsPage() {
  const [assignments, setAssignments] = useState<CourseContent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'submitted'>('all');

  useEffect(() => {
    async function fetchAssignments() {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/students/course-contents`, {
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error('Failed to fetch assignments');
        }

        const data = await response.json();
        setAssignments(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchAssignments();
  }, []);

  const filteredAssignments = assignments.filter((assignment) => {
    if (filter === 'pending') return !assignment.submitted;
    if (filter === 'submitted') return assignment.submitted;
    return true;
  });

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Assignments</h1>
            <p className="mt-2 text-gray-600">View and submit your course assignments</p>
          </div>
          <Link
            href="/student"
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            ← Back to Dashboard
          </Link>
        </div>

        {/* Filter Tabs */}
        <div className="flex space-x-2 border-b border-gray-200">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === 'all'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            All ({assignments.length})
          </button>
          <button
            onClick={() => setFilter('pending')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === 'pending'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Pending ({assignments.filter((a) => !a.submitted).length})
          </button>
          <button
            onClick={() => setFilter('submitted')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === 'submitted'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Submitted ({assignments.filter((a) => a.submitted).length})
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Assignments List */}
        {!loading && !error && filteredAssignments.length === 0 && (
          <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">No assignments found</h3>
            <p className="mt-2 text-sm text-gray-500">
              {filter === 'pending' && 'You have no pending assignments.'}
              {filter === 'submitted' && 'You have not submitted any assignments yet.'}
              {filter === 'all' && 'There are no assignments available.'}
            </p>
          </div>
        )}

        {!loading && !error && filteredAssignments.length > 0 && (
          <div className="space-y-4">
            {filteredAssignments.map((assignment) => (
              <AssignmentCard key={assignment.id} assignment={assignment} />
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}

function AssignmentCard({ assignment }: { assignment: CourseContent }) {
  const dueDate = assignment.due_date ? new Date(assignment.due_date) : null;
  const isOverdue = dueDate && dueDate < new Date() && !assignment.submitted;

  return (
    <div className={`bg-white rounded-lg border p-6 hover:shadow-md transition-shadow ${isOverdue ? 'border-red-300 bg-red-50' : 'border-gray-200'}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-gray-900">{assignment.title}</h3>
            {assignment.submitted && (
              <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded">
                Submitted
              </span>
            )}
            {isOverdue && (
              <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded">
                Overdue
              </span>
            )}
          </div>

          {assignment.course_name && (
            <p className="text-sm text-gray-500 mb-2">{assignment.course_name}</p>
          )}

          {assignment.description && (
            <p className="text-sm text-gray-600 mb-4">{assignment.description}</p>
          )}

          <div className="flex items-center space-x-4 text-sm text-gray-500">
            {dueDate && (
              <div className="flex items-center">
                <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Due: {dueDate.toLocaleDateString()}
              </div>
            )}
            {assignment.grade !== undefined && (
              <div className="flex items-center">
                <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Grade: {assignment.grade}%
              </div>
            )}
          </div>
        </div>

        <Link
          href={`/student/assignments/${assignment.id}`}
          className="ml-4 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          {assignment.submitted ? 'View' : 'Submit'}
        </Link>
      </div>
    </div>
  );
}
