'use client';

import { useEffect, useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';

interface LecturerStats {
  totalCourses: number;
  totalContent: number;
  activeAssignments: number;
  totalStudents: number;
}

export default function LecturerDashboard() {
  const [stats, setStats] = useState<LecturerStats>({
    totalCourses: 0,
    totalContent: 0,
    activeAssignments: 0,
    totalStudents: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [coursesRes, contentsRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/lecturers/courses`, { credentials: 'include' }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/lecturers/course-contents`, { credentials: 'include' }),
        ]);

        const courses = coursesRes.ok ? await coursesRes.json() : [];
        const contents = contentsRes.ok ? await contentsRes.json() : [];

        setStats({
          totalCourses: courses.length,
          totalContent: contents.length,
          activeAssignments: contents.filter((c: any) => !c.archived_at).length,
          totalStudents: 0, // TODO: Fetch from course enrollments
        });
      } catch (error) {
        console.error('Failed to fetch lecturer stats:', error);
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
          <h1 className="text-3xl font-bold text-gray-900">Lecturer Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Manage your courses, create content, and monitor student performance.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="My Courses"
            value={stats.totalCourses}
            icon="📚"
            loading={loading}
          />
          <StatCard
            title="Course Content"
            value={stats.totalContent}
            icon="📄"
            loading={loading}
          />
          <StatCard
            title="Active Assignments"
            value={stats.activeAssignments}
            icon="✍️"
            loading={loading}
          />
          <StatCard
            title="Total Students"
            value={stats.totalStudents}
            icon="👥"
            loading={loading}
            highlight
          />
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <ActionButton
              href="/lecturer/courses"
              icon="📚"
              title="Course Management"
              description="Create and manage courses"
            />
            <ActionButton
              href="/lecturer/content"
              icon="📄"
              title="Course Content"
              description="Manage course materials and assignments"
            />
            <ActionButton
              href="/lecturer/assignments"
              icon="✍️"
              title="Assignments"
              description="Create and configure assignments"
            />
            <ActionButton
              href="/lecturer/students"
              icon="👥"
              title="Students"
              description="View student enrollment and progress"
            />
            <ActionButton
              href="/lecturer/grading"
              icon="📊"
              title="Grading Overview"
              description="Review grades and submissions"
            />
            <ActionButton
              href="/lecturer/analytics"
              icon="📈"
              title="Analytics"
              description="View course and student analytics"
            />
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
          <div className="text-center py-8 text-gray-500">
            <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>No recent activity to display</p>
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
    <div className={`bg-white rounded-lg border p-6 ${highlight ? 'border-purple-300 bg-purple-50' : 'border-gray-200'}`}>
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
