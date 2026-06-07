'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseGet, CourseContentLecturerList, CourseContentTypeList } from 'types/generated';

// Deployment status → badge styling. The lecturer list always carries the
// top-level has_deployment + deployment_status (no include needed); values are
// deployed | pending | failed | unassigned (see business_logic/lecturer_deployment).
const STATUS_STYLES: Record<string, { label: string; cls: string }> = {
  deployed: { label: 'Deployed', cls: 'bg-green-100 text-green-700' },
  pending: { label: 'Pending', cls: 'bg-amber-100 text-amber-700' },
  failed: { label: 'Failed', cls: 'bg-red-100 text-red-700' },
  unassigned: { label: 'Unassigned', cls: 'bg-gray-100 text-gray-500' },
};

function deploymentBadge(c: CourseContentLecturerList) {
  const status = c.deployment_status || (c.has_deployment ? 'deployed' : null);
  if (!status) {
    return { label: 'No example', cls: 'bg-gray-100 text-gray-400' };
  }
  return STATUS_STYLES[status] ?? { label: status, cls: 'bg-gray-100 text-gray-600' };
}

// ltree depth: "week1.assignment2" → 1 (indent), "week1" → 0
const depthOf = (path: string) => Math.max(0, path.split('.').length - 1);
const lastSegment = (path: string) => path.split('.').slice(-1)[0];

export default function LecturerContentPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [course, setCourse] = useState<CourseGet | null>(null);
  const [contents, setContents] = useState<CourseContentLecturerList[]>([]);
  const [typeMap, setTypeMap] = useState<Record<string, CourseContentTypeList>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [cRes, ccRes, ctRes] = await Promise.all([
          apiFetch(`${API_BASE_URL}/courses/${courseId}`),
          apiFetch(`${API_BASE_URL}/lecturers/course-contents?course_id=${courseId}&limit=500`),
          apiFetch(`${API_BASE_URL}/course-content-types?course_id=${courseId}&limit=200`),
        ]);
        if (cancelled) return;
        if (!cRes.ok) throw new Error('Failed to load course');
        setCourse(await cRes.json());
        if (ccRes.ok) {
          const list: CourseContentLecturerList[] = await ccRes.json();
          // Tree order: lexicographic by ltree path keeps each parent directly
          // above its descendants; position orders siblings within a level.
          list.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : a.position - b.position));
          setContents(list);
        }
        if (ctRes.ok) {
          const types: CourseContentTypeList[] = await ctRes.json();
          setTypeMap(Object.fromEntries(types.map((t) => [t.id, t])));
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'An error occurred');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId, authLoading, isAuthenticated]);

  const active = contents.filter((c) => !c.archived_at);
  const archivedCount = contents.length - active.length;
  const submittable = active.filter((c) => c.is_submittable).length;
  const outdated = active.filter((c) => c.deployment?.has_newer_version).length;
  const counts = {
    deployed: active.filter((c) => c.deployment_status === 'deployed').length,
    pending: active.filter((c) => c.deployment_status === 'pending').length,
    failed: active.filter((c) => c.deployment_status === 'failed').length,
    none: active.filter((c) => !c.deployment_status && !c.has_deployment).length,
  };

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <div>
          <Link href={`/courses/${courseId}`} className="text-sm text-blue-600 hover:underline">
            ← {course?.title || course?.path || 'Course'}
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-gray-900">Course Contents</h1>
          {course && <p className="mt-1 text-sm text-gray-500 font-mono">{course.path}</p>}
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
        )}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : (
          <>
            {/* Summary — the at-a-glance deployment signal */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { label: 'Contents', value: active.length, cls: 'text-gray-900' },
                { label: 'Assignments', value: submittable, cls: 'text-blue-700' },
                { label: 'Deployed', value: counts.deployed, cls: 'text-green-700' },
                { label: 'Pending', value: counts.pending, cls: 'text-amber-700' },
                { label: 'Failed / none', value: counts.failed + counts.none, cls: 'text-red-700' },
              ].map((s) => (
                <div key={s.label} className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className={`text-2xl font-bold ${s.cls}`}>{s.value}</div>
                  <div className="text-xs text-gray-500 mt-1">{s.label}</div>
                </div>
              ))}
            </div>

            {outdated > 0 && (
              <div className="p-3 bg-orange-50 border border-orange-200 rounded text-sm text-orange-800">
                {outdated} deployed content(s) have a newer example version available.
              </div>
            )}

            {/* Content tree with deployment badges */}
            {active.length === 0 ? (
              <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
                No course contents yet. Add units and assignments to this course.
              </div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg divide-y">
                {active.map((c) => {
                  const type = c.course_content_type ?? typeMap[c.course_content_type_id];
                  const badge = deploymentBadge(c);
                  return (
                    <div key={c.id} className="flex items-center gap-3 px-4 py-3">
                      <div style={{ width: depthOf(c.path) * 18 }} className="shrink-0" />
                      <span
                        className="shrink-0 h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: type?.color || '#cbd5e1' }}
                        title={type?.title || type?.slug || 'content'}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {c.title || lastSegment(c.path)}
                        </div>
                        <div className="text-xs text-gray-400 font-mono truncate">{c.path}</div>
                      </div>
                      {type && (
                        <span className="shrink-0 px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                          {type.slug}
                        </span>
                      )}
                      {c.is_submittable && (
                        <span className="shrink-0 px-2 py-0.5 text-xs font-medium bg-blue-50 text-blue-600 rounded">
                          submittable
                        </span>
                      )}
                      {c.deployment?.has_newer_version && (
                        <span
                          className="shrink-0 px-2 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 rounded"
                          title="A newer example version is available"
                        >
                          update available
                        </span>
                      )}
                      <span className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {archivedCount > 0 && (
              <p className="text-xs text-gray-400">{archivedCount} archived content(s) hidden.</p>
            )}
          </>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
