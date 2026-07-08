'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useAuth } from '@/src/contexts/AuthContext';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import StatCards from './StatCards';
import ProgressBar from './ProgressBar';
import { CourseMemberGradingsClient } from '@/src/generated/clients/CourseMemberGradingsClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import type { CourseMemberGradingsList } from 'types/generated';

// Charts pull in recharts (~large) — load them only when this view renders
// instead of shipping the library in the shared bundle.
const chartLoading = () => <div className="h-64 bg-gray-100 rounded animate-pulse" />;
const ProgressDistributionChart = dynamic(() => import('./ProgressDistributionChart'), {
  ssr: false,
  loading: chartLoading,
});
const ContentTypeChart = dynamic(() => import('./ContentTypeChart'), {
  ssr: false,
  loading: chartLoading,
});

const gradingsClient = new CourseMemberGradingsClient();
const coursesClient = new CoursesClient();

function daysSince(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / (1000 * 60 * 60 * 24));
}

function relativeDate(dateStr: string | null | undefined): string {
  const days = daysSince(dateStr);
  if (days === null) return 'Never';
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

function activityDotColor(dateStr: string | null | undefined): string {
  const days = daysSince(dateStr);
  if (days === null || days > 14) return 'bg-red-400';
  if (days > 7) return 'bg-amber-400';
  return 'bg-green-400';
}

type SortKey = 'name' | 'progress' | 'grade' | 'lastActive';
type SortDir = 'asc' | 'desc';

/**
 * Student progress & grading overview — the sortable roster with stat cards and
 * charts, shown as the Lecturer → Students sub-tab. Rows open the per-student
 * detail at `/courses/[id]/lecturer/students/[memberId]`.
 */
export default function CourseProgressView({ courseId }: { courseId: string }) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [courseTitle, setCourseTitle] = useState('Course');
  const [students, setStudents] = useState<CourseMemberGradingsList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const fetchData = useCallback(async () => {
    try {
      const data = await gradingsClient.listCourseMemberGradingsEndpointCourseMemberGradingsGet({
        courseId,
      });
      setStudents(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load progress data');
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    fetchData();
    // Course title is best-effort — the breadcrumb falls back to "Course".
    coursesClient.getCoursesCoursesIdGet({ id: courseId }).then(
      (c) => setCourseTitle(c.title || c.path || 'Course'),
      () => {},
    );
  }, [authLoading, isAuthenticated, fetchData, courseId]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const filtered = students.filter((s) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      s.given_name?.toLowerCase().includes(q) ||
      s.family_name?.toLowerCase().includes(q) ||
      s.username?.toLowerCase().includes(q) ||
      s.student_id?.toLowerCase().includes(q)
    );
  });

  const sorted = [...filtered].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1;
    switch (sortKey) {
      case 'name': {
        const nameA = `${a.given_name || ''} ${a.family_name || ''}`.trim().toLowerCase();
        const nameB = `${b.given_name || ''} ${b.family_name || ''}`.trim().toLowerCase();
        return nameA.localeCompare(nameB) * dir;
      }
      case 'progress':
        return (a.overall_progress_percentage - b.overall_progress_percentage) * dir;
      case 'grade':
        return ((a.overall_average_grading ?? -1) - (b.overall_average_grading ?? -1)) * dir;
      case 'lastActive': {
        const dateA = a.latest_submission_at ? new Date(a.latest_submission_at).getTime() : 0;
        const dateB = b.latest_submission_at ? new Date(b.latest_submission_at).getTime() : 0;
        return (dateA - dateB) * dir;
      }
      default:
        return 0;
    }
  });

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return <span className="text-gray-300 ml-1">&#8597;</span>;
    return <span className="text-blue-500 ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={[
          { label: 'Courses', href: '/courses' },
          { label: courseTitle, href: `/courses/${courseId}` },
          { label: 'Lecturer View', href: `/courses/${courseId}/lecturer` },
          { label: 'Students' },
        ]}
        title="Students"
        subtitle="Overview of student progress and grading"
        actions={
          <button
            onClick={fetchData}
            disabled={loading}
            className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
          >
            Refresh
          </button>
        }
      />

      <ScrollArea className="space-y-6">
        {/* Loading */}
        {loading && (
          <div className="space-y-4">
            <div className="grid grid-cols-5 gap-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="h-64 bg-gray-100 rounded-lg animate-pulse" />
              <div className="h-64 bg-gray-100 rounded-lg animate-pulse" />
            </div>
          </div>
        )}

        {/* Error */}
        <ErrorBanner>{error}</ErrorBanner>

        {/* Content */}
        {!loading && !error && (
          <>
            {/* Stat Cards */}
            <StatCards students={students} />

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ProgressDistributionChart students={students} />
              <ContentTypeChart students={students} />
            </div>

            {/* Student Table */}
            <div className="bg-white rounded-lg border border-gray-200">
              <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-900">
                  Students ({filtered.length}
                  {filtered.length !== students.length ? ` / ${students.length}` : ''})
                </h3>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-64 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Search students..."
                />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th
                        className="text-left px-4 py-2.5 font-medium text-gray-600 cursor-pointer select-none"
                        onClick={() => handleSort('name')}
                      >
                        Student {sortIcon('name')}
                      </th>
                      <th
                        className="text-left px-4 py-2.5 font-medium text-gray-600 cursor-pointer select-none w-48"
                        onClick={() => handleSort('progress')}
                      >
                        Progress {sortIcon('progress')}
                      </th>
                      <th className="text-left px-4 py-2.5 font-medium text-gray-600">By Type</th>
                      <th
                        className="text-left px-4 py-2.5 font-medium text-gray-600 cursor-pointer select-none w-20"
                        onClick={() => handleSort('grade')}
                      >
                        Grade {sortIcon('grade')}
                      </th>
                      <th
                        className="text-left px-4 py-2.5 font-medium text-gray-600 cursor-pointer select-none w-28"
                        onClick={() => handleSort('lastActive')}
                      >
                        Last Active {sortIcon('lastActive')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {sorted.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                          {searchQuery ? 'No students match your search' : 'No student data available'}
                        </td>
                      </tr>
                    ) : (
                      sorted.map((s) => {
                        const name = `${s.given_name || ''} ${s.family_name || ''}`.trim() || s.username || '-';
                        const gradeDisplay =
                          s.overall_average_grading != null
                            ? `${Math.round(s.overall_average_grading * 100)}%`
                            : '-';

                        return (
                          <tr
                            key={s.course_member_id}
                            className="hover:bg-blue-50/50 cursor-pointer transition-colors"
                            onClick={() => router.push(`/courses/${courseId}/lecturer/students/${s.course_member_id}`)}
                          >
                            {/* Name */}
                            <td className="px-4 py-2.5">
                              <div>
                                <span className="text-gray-900 font-medium">{name}</span>
                                {s.student_id && (
                                  <span className="ml-2 text-xs text-gray-400 font-mono">{s.student_id}</span>
                                )}
                              </div>
                            </td>

                            {/* Progress */}
                            <td className="px-4 py-2.5">
                              <div className="flex items-center gap-2">
                                <ProgressBar value={s.overall_progress_percentage} size="sm" />
                                <span className="text-xs font-medium text-gray-600 w-10 text-right">
                                  {Math.round(s.overall_progress_percentage)}%
                                </span>
                              </div>
                            </td>

                            {/* By Type */}
                            <td className="px-4 py-2.5">
                              <div className="flex items-center gap-1.5">
                                {(s.by_content_type || []).map((ct) => (
                                  <div
                                    key={ct.course_content_type_id}
                                    className="flex items-center gap-1"
                                    title={`${ct.course_content_type_title || ct.course_content_type_slug}: ${Math.round(ct.progress_percentage)}%`}
                                  >
                                    <span
                                      className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                                      style={{ backgroundColor: ct.course_content_type_color || '#6366f1' }}
                                    />
                                    <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                      <div
                                        className="h-1.5 rounded-full"
                                        style={{
                                          width: `${Math.min(ct.progress_percentage, 100)}%`,
                                          backgroundColor: ct.course_content_type_color || '#6366f1',
                                        }}
                                      />
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </td>

                            {/* Grade */}
                            <td className="px-4 py-2.5 text-xs font-medium text-gray-700">{gradeDisplay}</td>

                            {/* Last Active */}
                            <td className="px-4 py-2.5">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className={`inline-block w-2 h-2 rounded-full ${activityDotColor(s.latest_submission_at)}`}
                                />
                                <span className="text-xs text-gray-600">{relativeDate(s.latest_submission_at)}</span>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </ScrollArea>
    </ListPageLayout>
  );
}
