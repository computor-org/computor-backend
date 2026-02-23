'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { apiFetch } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseGet } from 'types/generated';

export default function CoursePage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const params = useParams();
  const courseId = params.id as string;
  const [course, setCourse] = useState<CourseGet | null>(null);
  const [courseViews, setCourseViews] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Don't fetch until authentication is confirmed
    if (authLoading || !isAuthenticated) {
      return;
    }

    async function fetchCourseData() {
      try {
        // Fetch course details
        const courseResponse = await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/courses/${courseId}`);

        if (!courseResponse.ok) {
          throw new Error('Failed to fetch course');
        }

        const courseData = await courseResponse.json();
        setCourse(courseData);

        // Fetch course-specific views
        const viewsResponse = await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/user/views/${courseId}`);

        if (viewsResponse.ok) {
          const viewsData = await viewsResponse.json();
          setCourseViews(viewsData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchCourseData();
  }, [courseId, authLoading, isAuthenticated]);

  if (loading) {
    return (
      <AuthenticatedLayout>
        <div className="p-6 space-y-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  if (error || !course) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-800">{error || 'Course not found'}</p>
            </div>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{course.title || 'Untitled Course'}</h1>
            <p className="mt-2 text-gray-600">
              <span className="font-mono text-sm">{course.path}</span>
              {course.language_code && (
                <span className="ml-4 px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded uppercase">
                  {course.language_code}
                </span>
              )}
            </p>
          </div>
          <Link
            href="/courses"
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            ← Back to Courses
          </Link>
        </div>

        {/* Course Description */}
        {course.description && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Description</h2>
            <p className="text-gray-700">{course.description}</p>
          </div>
        )}

        {/* Course Info */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Course Information</h2>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">Course ID</dt>
              <dd className="mt-1 text-sm text-gray-900 font-mono">{course.id}</dd>
            </div>
            {course.organization_id && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Organization ID</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono">{course.organization_id}</dd>
              </div>
            )}
            {course.course_family_id && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Course Family ID</dt>
                <dd className="mt-1 text-sm text-gray-900 font-mono">{course.course_family_id}</dd>
              </div>
            )}
            {course.team_mode && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Team Mode</dt>
                <dd className="mt-1 text-sm text-gray-900">{course.team_mode}</dd>
              </div>
            )}
            {course.created_at && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(course.created_at).toLocaleDateString()}
                </dd>
              </div>
            )}
            {course.updated_at && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(course.updated_at).toLocaleDateString()}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Quick Actions - Based on available views */}
        {courseViews.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Access</h2>
            <div className={`grid grid-cols-1 md:grid-cols-${courseViews.length} gap-4`}>
              {courseViews.includes('student') && (
                <Link
                  href={`/courses/${courseId}/student`}
                  className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                    </svg>
                    <div>
                      <h3 className="font-medium text-gray-900">Student View</h3>
                      <p className="text-xs text-gray-500">Course contents & assignments</p>
                    </div>
                  </div>
                </Link>
              )}

              {courseViews.includes('tutor') && (
                <Link
                  href={`/courses/${courseId}/tutor`}
                  className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <div>
                      <h3 className="font-medium text-gray-900">Tutor View</h3>
                      <p className="text-xs text-gray-500">Manage students & grading</p>
                    </div>
                  </div>
                </Link>
              )}

              {courseViews.includes('lecturer') && (
                <Link
                  href={`/courses/${courseId}/lecturer`}
                  className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    <div>
                      <h3 className="font-medium text-gray-900">Lecturer View</h3>
                      <p className="text-xs text-gray-500">Course management & analytics</p>
                    </div>
                  </div>
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
