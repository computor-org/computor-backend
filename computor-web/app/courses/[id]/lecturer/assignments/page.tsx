'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge, { BadgeColor } from '@/src/components/Badge';
import type { CourseGet, CourseContentLecturerList, CourseContentTypeList } from 'types/generated';

// Deployment status → badge styling. The lecturer list always carries the
// top-level has_deployment + deployment_status (no include needed); values are
// deployed | pending | failed | unassigned (see business_logic/lecturer_deployment).
const STATUS_STYLES: Record<string, { label: string; color: BadgeColor }> = {
  deployed: { label: 'Deployed', color: 'green' },
  pending: { label: 'Pending', color: 'yellow' },
  failed: { label: 'Failed', color: 'red' },
  unassigned: { label: 'Unassigned', color: 'gray' },
};

function deploymentBadge(c: CourseContentLecturerList): { label: string; color: BadgeColor } {
  const status = c.deployment_status || (c.has_deployment ? 'deployed' : null);
  if (!status) {
    // A unit isn't deployable (no example of its own) — label it as such rather
    // than implying a submittable assignment is missing its example.
    if (!c.is_submittable) return { label: 'Unit', color: 'gray' };
    return { label: 'No example', color: 'gray' };
  }
  return STATUS_STYLES[status] ?? { label: status, color: 'gray' };
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
  const [releasing, setReleasing] = useState<string | null>(null);
  const [releaseMsg, setReleaseMsg] = useState<string | null>(null);

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

  // Re-fetch just the content list (badges move pending → deploying → deployed as
  // the release workflow runs).
  const reload = useCallback(async () => {
    try {
      const ccRes = await apiFetch(`${API_BASE_URL}/lecturers/course-contents?course_id=${courseId}&limit=500`);
      if (ccRes.ok) {
        const list: CourseContentLecturerList[] = await ccRes.json();
        list.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : a.position - b.position));
        setContents(list);
      }
    } catch {
      /* ignore refresh errors */
    }
  }, [courseId]);

  // "Release" == deploy the assigned example(s) into the student-template repo via
  // the course-git-aware generate-student-template workflow. No ids => all pending.
  async function release(key: string, ids?: string[], force?: boolean) {
    setReleasing(key);
    setReleaseMsg(null);
    try {
      const body: Record<string, unknown> = ids && ids.length ? { release: { course_content_ids: ids } } : {};
      // force_redeploy re-processes already-'deployed' contents too — needed to
      // backfill the reference repo for assignments whose template was pushed
      // before reference support existed.
      if (force) body.force_redeploy = true;
      const res = await apiFetch(`${API_BASE_URL}/system/courses/${courseId}/generate-student-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || err?.message || `Release failed (${res.status})`);
      }
      setReleaseMsg('Release started — badges move to “deploying”, then “deployed”.');
      setTimeout(() => reload(), 3000);
    } catch (e) {
      setReleaseMsg(e instanceof Error ? e.message : 'Release failed');
    } finally {
      setReleasing(null);
    }
  }

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

  // A unit's nested submittable contents that have an example assigned (only those
  // can be released).
  const releasableDescendants = (unit: CourseContentLecturerList) =>
    active.filter(
      (c) => c.path.startsWith(unit.path + '.') && c.is_submittable && (c.has_deployment || !!c.deployment_status),
    );

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: course?.title || course?.path || 'Course', href: `/courses/${courseId}` },
            { label: 'Lecturer View', href: `/courses/${courseId}/lecturer` },
            { label: 'Assignments' },
          ]}
          title="Assignments"
          subtitle={course ? <span className="text-sm text-gray-500 font-mono">{course.path}</span> : undefined}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea className="space-y-6">
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

            {/* Release toolbar */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => release('all')}
                disabled={releasing !== null || counts.pending + counts.failed === 0}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                title="Deploy every pending/failed assignment into the template repo"
              >
                {releasing === 'all' ? 'Releasing…' : `Release all pending (${counts.pending + counts.failed})`}
              </button>
              <button
                type="button"
                onClick={() => release('all-force', undefined, true)}
                disabled={releasing !== null || counts.deployed + counts.pending + counts.failed === 0}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
                title="Re-deploy ALL assignments (including already-deployed) — fills both the template and reference repos"
              >
                {releasing === 'all-force' ? 'Re-releasing…' : 'Re-release all (force)'}
              </button>
              {releaseMsg && <span className="text-sm text-gray-500">{releaseMsg}</span>}
            </div>

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
                      {(() => {
                        const canReleaseOne = c.is_submittable && (c.has_deployment || !!c.deployment_status);
                        const unitKids = c.is_submittable ? [] : releasableDescendants(c);
                        if (canReleaseOne) {
                          return (
                            <button
                              type="button"
                              onClick={() => release(c.id, [c.id])}
                              disabled={releasing !== null}
                              className="shrink-0 px-2 py-0.5 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 disabled:opacity-50"
                            >
                              {releasing === c.id ? '…' : 'Release'}
                            </button>
                          );
                        }
                        if (unitKids.length > 0) {
                          return (
                            <button
                              type="button"
                              onClick={() => release(c.id, unitKids.map((k) => k.id))}
                              disabled={releasing !== null}
                              className="shrink-0 px-2 py-0.5 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 disabled:opacity-50"
                              title={`Release ${unitKids.length} assignment(s) in this unit`}
                            >
                              {releasing === c.id ? '…' : `Release unit (${unitKids.length})`}
                            </button>
                          );
                        }
                        return null;
                      })()}
                      <Badge color={badge.color} className="shrink-0">
                        {badge.label}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            )}

            {archivedCount > 0 && (
              <p className="text-xs text-gray-400">{archivedCount} archived content(s) hidden.</p>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
