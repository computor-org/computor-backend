'use client';

import { useEffect, useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';

interface CourseStats {
  totalCourses: number;
  activeCourses: number;
  totalAssignments: number;
  pendingSubmissions: number;
}

export default function StudentDashboard() {
  const [stats, setStats] = useState<CourseStats>({
    totalCourses: 0,
    activeCourses: 0,
    totalAssignments: 0,
    pendingSubmissions: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        // Fetch student courses to calculate stats
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/students/courses`, {
          credentials: 'include',
        });

        if (response.ok) {
          const courses = await response.json();

          // Fetch course contents to count assignments
          const contentsResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/students/course-contents`, {
            credentials: 'include',
          });

          const contents = contentsResponse.ok ? await contentsResponse.json() : [];

          setStats({
            totalCourses: courses.length,
            activeCourses: courses.filter((c: any) => !c.archived_at).length,
            totalAssignments: contents.length,
            pendingSubmissions: contents.filter((c: any) => !c.submitted).length || 0,
          });
        }
      } catch (error) {
        console.error('Failed to fetch student stats:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Student Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Welcome to your student view. Here you can access your courses, assignments, and grades.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Courses"
            value={stats.totalCourses}
            icon="📚"
            loading={loading}
          />
          <StatCard
            title="Active Courses"
            value={stats.activeCourses}
            icon="✅"
            loading={loading}
          />
          <StatCard
            title="Assignments"
            value={stats.totalAssignments}
            icon="📝"
            loading={loading}
          />
          <StatCard
            title="Pending Submissions"
            value={stats.pendingSubmissions}
            icon="⏰"
            loading={loading}
            highlight
          />
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ActionButton
              href="/student/courses"
              icon="📚"
              title="My Courses"
              description="View all your enrolled courses"
            />
            <ActionButton
              href="/student/assignments"
              icon="📝"
              title="Assignments"
              description="View and submit assignments"
            />
            <ActionButton
              href="/student/submissions"
              icon="📤"
              title="Submissions"
              description="Track your submission history"
            />
            <ActionButton
              href="/student/grades"
              icon="📊"
              title="Grades"
              description="View your grades and feedback"
            />
          </div>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

function StatCard({
  title,
  value,
  icon,
  loading,
  highlight = false
}: {
  title: string;
  value: number;
  icon: string;
  loading: boolean;
  highlight?: boolean;
}) {
  return (
    <div className={`bg-white rounded-lg border p-6 ${highlight ? 'border-blue-300 bg-blue-50' : 'border-gray-200'}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          {loading ? (
            <div className="mt-2 h-8 w-16 bg-gray-200 animate-pulse rounded"></div>
          ) : (
            <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
          )}
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
    </div>
  );
}

function ActionButton({
  href,
  icon,
  title,
  description
}: {
  href: string;
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <a
      href={href}
      className="flex items-start p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors border border-gray-200"
    >
      <div className="text-3xl mr-4">{icon}</div>
      <div>
        <h3 className="font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600 mt-1">{description}</p>
      </div>
    </a>
  );
}
