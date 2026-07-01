'use client';


import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useParams, useRouter, useSearchParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseGet } from 'types/generated';
import {
  AnalyticsApiError,
  DEFAULT_ANALYTICS_CUTOFFS,
  analyticsRoleAtLeast,
  getCourseSummary,
  getStudentExamples,
  listCourseContentsForFind,
  listAnalyticsCourses,
  listStudents,
  type AnalyticsCourseAccess,
  type AnalyticsCourseSummary,
  type AnalyticsCutoffs,
  type RosterStudent,
} from '@/src/api/analytics';
import SummaryCards from '@/src/components/analytics/SummaryCards';
import CutoffControls from '@/src/components/analytics/CutoffControls';
import RefreshControl from '@/src/components/analytics/RefreshControl';
import RosterList from '@/src/components/analytics/RosterList';
import StudentTimelinePanel from '@/src/components/analytics/StudentTimelinePanel';

export default function LecturerAnalyticsPage() {
  const courseId = useParams().id as string;
  const searchParams = useSearchParams();
  const requestedMember = searchParams.get('student');
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { courseHasAtLeast } = usePermissions();

  const [course, setCourse] = useState<CourseGet | null>(null);
  const [analyticsCourse, setAnalyticsCourse] = useState<AnalyticsCourseAccess | null>(null);
  const [cutoffs, setCutoffs] = useState<AnalyticsCutoffs>(DEFAULT_ANALYTICS_CUTOFFS);
  const [summary, setSummary] = useState<AnalyticsCourseSummary | null>(null);
  const [students, setStudents] = useState<RosterStudent[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [exampleFindEntries, setExampleFindEntries] = useState<ExampleFindEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const loadSequence = useRef(0);
  const [emptyReason, setEmptyReason] = useState<'none' | 'no-snapshot' | 'forbidden' | 'error'>(
    'none',
  );
  const [errorText, setErrorText] = useState<string | null>(null);
  const canRefresh =
    courseHasAtLeast(courseId, '_lecturer') ||
    analyticsRoleAtLeast(analyticsCourse?.role, '_lecturer');
  const selected = useMemo(
    () =>
      requestedMember
        ? students.find((s) => s.course_member_id === requestedMember) ?? null
        : null,
    [requestedMember, students],
  );

  const load = useCallback(async () => {
    const sequence = loadSequence.current + 1;
    loadSequence.current = sequence;
    setLoading(true);
    setErrorText(null);
    setExampleFindEntries([]);
    try {
      const [s, list] = await Promise.all([
        getCourseSummary(courseId, cutoffs),
        listStudents(courseId, cutoffs),
      ]);
      const roster = list.students ?? [];
      if (loadSequence.current !== sequence) return;
      setSummary(s);
      setStudents(roster);
      setEmptyReason('none');
      void buildExampleFindEntries(courseId, roster, cutoffs).then((examples) => {
        if (loadSequence.current === sequence) setExampleFindEntries(examples);
      });
    } catch (e) {
      if (loadSequence.current !== sequence) return;
      setSummary(null);
      setStudents([]);
      if (e instanceof AnalyticsApiError && e.status === 404) {
        setEmptyReason('no-snapshot');
      } else if (e instanceof AnalyticsApiError && e.status === 403) {
        setEmptyReason('forbidden');
      } else {
        setEmptyReason('error');
        setErrorText(e instanceof Error ? e.message : 'Failed to load analytics.');
      }
    } finally {
      if (loadSequence.current === sequence) setLoading(false);
    }
  }, [courseId, cutoffs]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const [localRes, analyticsRes] = await Promise.allSettled([
          apiFetch(`${API_BASE_URL}/courses/${courseId}`),
          listAnalyticsCourses(),
        ]);
        if (cancelled) return;
        if (localRes.status === 'fulfilled' && localRes.value.ok) {
          setCourse(await localRes.value.json());
        }
        if (analyticsRes.status === 'fulfilled') {
          setAnalyticsCourse(
            analyticsRes.value.find((entry) => entry.course_id === courseId) ?? null,
          );
        }
      } catch {
        /* header is best-effort */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId, authLoading, isAuthenticated]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  const selectStudent = useCallback(
    (student: RosterStudent) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('student', student.course_member_id);
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 p-2 md:p-4">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link
              href={`/courses/${courseId}/lecturer/analytics`}
              className="text-sm text-blue-600 hover:underline print:hidden"
            >
              Back to{' '}
              {course?.title ||
                analyticsCourse?.title ||
                course?.path ||
                analyticsCourse?.path ||
                'Analytics'}
            </Link>
            <h1 className="mt-2 text-3xl font-bold text-gray-900">Course Analytics</h1>
            <p className="mt-1 text-sm text-gray-500">
              Submission and grading checkpoint from the latest analytics snapshot.
            </p>
          </div>
          <div className="flex items-center gap-2 print:hidden">
            <button
              type="button"
              onClick={() => window.print()}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Print report
            </button>
            {canRefresh && (
              <RefreshControl
                courseId={courseId}
                cutoffs={cutoffs}
                initialJob={summary?.latest_job ?? null}
                onRefreshed={load}
              />
            )}
          </div>
        </header>

        <div className="print:hidden">
          <CutoffControls
            key={`${cutoffs.submissionCutoff ?? ''}|${cutoffs.gradingCutoff ?? ''}`}
            value={cutoffs}
            onApply={setCutoffs}
            disabled={loading}
          />
        </div>

        {loading && <p className="text-sm text-gray-500">Loading analytics…</p>}

        {!loading && emptyReason === 'forbidden' && (
          <EmptyState
            title="No analytics access"
            message="You need a tutor role or higher on this course to view analytics."
          />
        )}
        {!loading && emptyReason === 'no-snapshot' && (
          <EmptyState
            title="No snapshot yet"
            message={
              canRefresh
                ? 'Run “Update data” to import the latest course data from the source site.'
                : 'A lecturer needs to run the first analytics update for this course.'
            }
          />
        )}
        {!loading && emptyReason === 'error' && (
          <EmptyState title="Could not load analytics" message={errorText ?? 'Unknown error.'} />
        )}

        {!loading && summary && emptyReason === 'none' && (
          <>
            <SummaryCards summary={summary} />
            <div className="grid gap-6 lg:grid-cols-[minmax(200px,260px)_1fr] print:block">
              <div className="lg:max-h-[calc(100vh-13rem)] lg:overflow-y-auto print:max-h-none print:overflow-visible">
                <RosterList
                  students={students}
                  selectedId={selected?.course_member_id ?? null}
                  query={searchQuery}
                  onQueryChange={setSearchQuery}
                  onSelect={selectStudent}
                />
              </div>
              <div className="lg:sticky lg:top-4 lg:self-start">
                {selected ? (
                  <StudentTimelinePanel
                    courseId={courseId}
                    student={selected}
                    cutoffs={cutoffs}
                  />
                ) : (
                  <p className="rounded-lg border-2 border-dashed border-gray-200 p-10 text-center text-sm text-gray-400">
                    Select a student to see their evidence.
                  </p>
                )}
              </div>
            </div>
            <BrowserFindText examples={exampleFindEntries} />
          </>
        )}
      </div>
    </AuthenticatedLayout>
  );
}

interface ExampleFindEntry {
  key: string;
  title: string;
  path: string;
  contentId: string;
  unit: string;
  category: string;
}

async function buildExampleFindEntries(
  courseId: string,
  students: RosterStudent[],
  cutoffs: AnalyticsCutoffs,
): Promise<ExampleFindEntry[]> {
  const examplesByKey = new Map<string, ExampleFindEntry>();
  const add = (entry: ExampleFindEntry) => {
    if (!examplesByKey.has(entry.key)) examplesByKey.set(entry.key, entry);
  };
  await Promise.all([
    addCourseContentFindEntries(courseId, add),
    addStudentExampleFindEntries(courseId, students, cutoffs, add),
  ]);
  return [...examplesByKey.values()].sort((a, b) =>
    `${a.title} ${a.path}`.localeCompare(`${b.title} ${b.path}`),
  );
}

async function addCourseContentFindEntries(
  courseId: string,
  add: (entry: ExampleFindEntry) => void,
) {
  try {
    const contents = await listCourseContentsForFind(courseId);
    for (const content of contents) {
      const deployment = content.deployment;
      add({
        key: content.id,
        title: content.title || content.path || content.id,
        path: content.path || '',
        contentId: content.id,
        unit: content.course_content_type?.slug || '',
        category: [
          content.course_content_kind_id,
          deployment?.example_identifier,
          deployment?.version_identifier,
          deployment?.version_tag,
        ]
          .filter(Boolean)
          .join(' '),
      });
    }
  } catch {
    /* The analytics page must not depend on the auxiliary find index. */
  }
}

async function addStudentExampleFindEntries(
  courseId: string,
  students: RosterStudent[],
  cutoffs: AnalyticsCutoffs,
  add: (entry: ExampleFindEntry) => void,
) {
  const batchSize = 8;
  for (let i = 0; i < students.length; i += batchSize) {
    const batch = students.slice(i, i + batchSize);
    await Promise.all(
      batch.map(async (student) => {
        try {
          const examples = await getStudentExamples(courseId, student.course_member_id, cutoffs);
          for (const ex of examples) {
            const key = ex.content_id || `${ex.title}|${ex.path}`;
            add({
              key,
              title: ex.title || ex.path || key,
              path: ex.path || '',
              contentId: ex.content_id || '',
              unit: ex.unit || '',
              category: ex.category || '',
            });
          }
        } catch {
          /* keep the course page usable if one student's detail endpoint fails */
        }
      }),
    );
  }
}

function BrowserFindText({ examples }: { examples: ExampleFindEntry[] }) {
  if (examples.length === 0) return null;

  return (
    <div
      className="print:hidden text-[11px] leading-snug text-gray-400"
      data-testid="analytics-browser-find-text"
    >
      {examples.map((example) => (
        <span key={example.key} className="mr-3">
          {findTextParts(example).join(' ')}
        </span>
      ))}
    </div>
  );
}

function findTextParts(example: ExampleFindEntry): string[] {
  const raw = [example.title, example.path, example.contentId, example.unit, example.category]
    .filter(Boolean)
    .join(' ');
  const parts = new Set(raw.split(/\s+/).filter(Boolean));
  for (const token of raw.split(/[^0-9A-Za-zÄÖÜäöüß]+/).filter(Boolean)) {
    parts.add(token);
  }
  return [...parts];
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-lg border-2 border-dashed border-gray-300 bg-white p-10 text-center">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      <p className="mx-auto mt-1 max-w-md text-sm text-gray-500">{message}</p>
    </div>
  );
}
