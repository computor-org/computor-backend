'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { useAuth } from '@/src/contexts/AuthContext';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import ProgressBar from './ProgressBar';
import ProgressStatCards from './ProgressStatCards';
import Button from '@/src/components/ui/Button';
import Toolbar from '@/src/components/ui/Toolbar';
import Panel from '@/src/components/ui/Panel';
import { Table, Thead, Tbody, Th, Td } from '@/src/components/ui/Table';
import { inputCls } from '@/src/components/ui/tokens';
import { CourseMemberGradingsClient } from '@/src/generated/clients/CourseMemberGradingsClient';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import type { CourseMemberGradingsList } from 'types/generated';

// Charts pull in recharts (~large) — load them only when this view renders
// instead of shipping the library in the shared bundle.
const chartLoading = () => <div className="h-64 bg-sunken rounded animate-pulse" />;
const ProgressDistributionChart = dynamic(() => import('./ProgressDistributionChart'), {
  ssr: false,
  loading: chartLoading,
});
const ContentTypeChart = dynamic(() => import('./ContentTypeChart'), {
  ssr: false,
  loading: chartLoading,
});

const gradingsClient = new CourseMemberGradingsClient();

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
 * charts, shown as the Lecturer → Grading sub-tab. Rows open the per-student
 * detail at `/courses/[id]/lecturer/grading/[memberId]`.
 */
export default function CourseProgressView({ courseId }: { courseId: string }) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const crumbs = useCourseCrumbs(courseId, 'Grading');
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
  }, [authLoading, isAuthenticated, fetchData]);

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
    if (sortKey !== key) return <span className="text-faint ml-1">&#8597;</span>;
    return <span className="text-blue-500 ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={crumbs}
        title="Grading"
        subtitle="Overview of student progress and grading"
        actions={
          <Button variant="secondary" onClick={fetchData} disabled={loading}>
            Refresh
          </Button>
        }
      />

      <ScrollArea>
        {/* Loading */}
        {loading && (
          <div className="space-y-4">
            <div className="grid grid-cols-5 gap-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 bg-sunken rounded-lg animate-pulse" />
              ))}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="h-64 bg-sunken rounded-lg animate-pulse" />
              <div className="h-64 bg-sunken rounded-lg animate-pulse" />
            </div>
          </div>
        )}

        {/* Error */}
        <ErrorBanner>{error}</ErrorBanner>

        {/* Content */}
        {!loading && !error && (
          <>
            {/* Stat Cards */}
            <ProgressStatCards students={students} />

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <ProgressDistributionChart students={students} />
              <ContentTypeChart students={students} />
            </div>

            {/* Student Table */}
            <Panel padding="none">
              <Toolbar className="px-4 py-3 border-b border-rule">
                <h3 className="text-sm font-semibold text-fg">
                  Students ({filtered.length}
                  {filtered.length !== students.length ? ` / ${students.length}` : ''})
                </h3>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`${inputCls} ml-auto w-64`}
                  placeholder="Search students…"
                  aria-label="Search students"
                />
              </Toolbar>
              <div className="overflow-x-auto">
                <Table>
                  <Thead>
                    <tr>
                      <Th
                        className="cursor-pointer select-none normal-case tracking-normal text-sm"
                        onClick={() => handleSort('name')}
                      >
                        Student {sortIcon('name')}
                      </Th>
                      <Th
                        className="cursor-pointer select-none w-48 normal-case tracking-normal text-sm"
                        onClick={() => handleSort('progress')}
                      >
                        Progress {sortIcon('progress')}
                      </Th>
                      <Th className="normal-case tracking-normal text-sm">By type</Th>
                      <Th
                        className="cursor-pointer select-none w-20 normal-case tracking-normal text-sm"
                        onClick={() => handleSort('grade')}
                      >
                        Grade {sortIcon('grade')}
                      </Th>
                      <Th
                        className="cursor-pointer select-none w-28 normal-case tracking-normal text-sm"
                        onClick={() => handleSort('lastActive')}
                      >
                        Last active {sortIcon('lastActive')}
                      </Th>
                    </tr>
                  </Thead>
                  <Tbody>
                    {sorted.length === 0 ? (
                      <tr>
                        <Td colSpan={5} className="py-8 text-center text-muted">
                          {searchQuery ? 'No students match your search' : 'No student data available'}
                        </Td>
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
                            onClick={() => router.push(`/courses/${courseId}/lecturer/grading/${s.course_member_id}`)}
                          >
                            {/* Name */}
                            <Td className="py-2.5">
                              <div>
                                <span className="text-fg font-medium">{name}</span>
                                {s.student_id && (
                                  <span className="ml-2 text-xs text-subtle font-mono">{s.student_id}</span>
                                )}
                              </div>
                            </Td>

                            {/* Progress */}
                            <Td className="py-2.5">
                              <div className="flex items-center gap-2">
                                <ProgressBar value={s.overall_progress_percentage} size="sm" />
                                <span className="text-xs font-medium text-muted w-10 text-right">
                                  {Math.round(s.overall_progress_percentage)}%
                                </span>
                              </div>
                            </Td>

                            {/* By Type */}
                            <Td className="py-2.5">
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
                                    <div className="w-12 h-1.5 bg-sunken rounded-full overflow-hidden">
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
                            </Td>

                            {/* Grade */}
                            <Td className="py-2.5 text-xs font-medium text-body">{gradeDisplay}</Td>

                            {/* Last Active */}
                            <Td className="py-2.5">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className={`inline-block w-2 h-2 rounded-full ${activityDotColor(s.latest_submission_at)}`}
                                />
                                <span className="text-xs text-muted">{relativeDate(s.latest_submission_at)}</span>
                              </div>
                            </Td>
                          </tr>
                        );
                      })
                    )}
                  </Tbody>
                </Table>
              </div>
            </Panel>
          </>
        )}
      </ScrollArea>
    </ListPageLayout>
  );
}
