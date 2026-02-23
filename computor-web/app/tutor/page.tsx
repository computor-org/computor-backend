'use client';

import { useEffect, useState } from 'react';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';

interface TutorStats {
  totalCourses: number;
  totalStudents: number;
  totalSubmissionGroups: number;
  pendingReviews: number;
}

export default function TutorDashboard() {
  const [stats, setStats] = useState<TutorStats>({
    totalCourses: 0,
    totalStudents: 0,
    totalSubmissionGroups: 0,
    pendingReviews: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [coursesRes, studentsRes, groupsRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/tutors/courses`, { credentials: 'include' }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/tutors/course-members`, { credentials: 'include' }),
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/tutors/submission-groups`, { credentials: 'include' }),
        ]);

        const courses = coursesRes.ok ? await coursesRes.json() : [];
        const students = studentsRes.ok ? await studentsRes.json() : [];
        const groups = groupsRes.ok ? await groupsRes.json() : [];

        setStats({
          totalCourses: courses.length,
          totalStudents: students.length,
          totalSubmissionGroups: groups.length,
          pendingReviews: 0, // TODO: Calculate from submissions
        });
      } catch (error) {
        console.error('Failed to fetch tutor stats:', error);
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
          <h1 className="text-3xl font-bold text-gray-900">Tutor Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Manage your students, review submissions, and provide feedback.
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
            title="Students"
            value={stats.totalStudents}
            icon="👥"
            loading={loading}
          />
          <StatCard
            title="Submission Groups"
            value={stats.totalSubmissionGroups}
            icon="📦"
            loading={loading}
          />
          <StatCard
            title="Pending Reviews"
            value={stats.pendingReviews}
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
              href="/tutor/courses"
              icon="📚"
              title="My Courses"
              description="View courses you're tutoring"
            />
            <ActionButton
              href="/tutor/students"
              icon="👥"
              title="Students"
              description="Manage and view student progress"
            />
            <ActionButton
              href="/tutor/submissions"
              icon="📤"
              title="Submissions"
              description="Review student submissions"
            />
            <ActionButton
              href="/tutor/grading"
              icon="📊"
              title="Grading"
              description="Grade assignments and provide feedback"
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
    <div className={`bg-white rounded-lg border p-6 ${highlight ? 'border-orange-300 bg-orange-50' : 'border-gray-200'}`}>
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
