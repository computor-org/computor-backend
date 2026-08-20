'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useContentTree } from '@/src/hooks/useContentTree';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Badge from '@/src/components/Badge';
import { deploymentBadge } from '@/src/utils/deployment';
import { formatLimit } from '@/src/utils/limits';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import Toolbar from '@/src/components/ui/Toolbar';
import Notice from '@/src/components/ui/Notice';
import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import TreeRow, { TreeRows } from '@/src/components/ui/TreeRow';
import type { CourseContentLecturerList, CourseContentTypeList } from 'types/generated';

export default function LecturerContentPage() {
  const courseId = useParams().id as string;
  const crumbs = useCourseCrumbs(courseId, 'Assignments');

  // reload re-fetches everything (badges move pending → deploying → deployed as
  // the release workflow runs).
  const { data, loading, error, reload } = useResource(async () => {
    // The course itself comes from CourseContext — this page only needs what is
    // specific to it.
    const [ccRes, ctRes] = await Promise.all([
      apiFetch(`${API_BASE_URL}/lecturers/course-contents?course_id=${courseId}&limit=500`),
      apiFetch(`${API_BASE_URL}/course-content-types?course_id=${courseId}&limit=200`),
    ]);
    let contents: CourseContentLecturerList[] = [];
    if (ccRes.ok) {
      // Order is useContentTree's job now — it nests by path and sorts siblings
      // by position, so sorting here as well would only be a second opinion.
      contents = await ccRes.json();
    }
    let typeMap: Record<string, CourseContentTypeList> = {};
    if (ctRes.ok) {
      const types: CourseContentTypeList[] = await ctRes.json();
      typeMap = Object.fromEntries(types.map((t) => [t.id, t]));
    }
    return { contents, typeMap };
  }, [courseId]);

  const contents = useMemo(() => data?.contents ?? [], [data]);
  const typeMap = data?.typeMap ?? {};

  const [releasing, setReleasing] = useState<string | null>(null);
  const [releaseMsg, setReleaseMsg] = useState<string | null>(null);

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

  const [togglingVisibility, setTogglingVisibility] = useState<string | null>(null);

  // Flip a content between "hidden" and "inherit" (issue #338). Going back to
  // null rather than true is deliberate: true would pin the content visible
  // against a future decision to hide the unit above it, which is almost never
  // what a lecturer means by "show this again".
  //
  // This lives on the tree rather than only in the edit form because the
  // workflow it serves is a fast flip at the start and end of an exam.
  async function toggleVisibility(c: CourseContentLecturerList) {
    setTogglingVisibility(c.id);
    setReleaseMsg(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/course-contents/${c.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visible: c.visible === false ? null : false }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || err?.message || `Failed (${res.status})`);
      }
      reload();
    } catch (e) {
      setReleaseMsg(e instanceof Error ? e.message : 'Could not change visibility');
    } finally {
      setTogglingVisibility(null);
    }
  }

  const active = useMemo(() => contents.filter((c) => !c.archived_at), [contents]);
  const archivedCount = contents.length - active.length;
  const submittable = active.filter((c) => c.is_submittable).length;
  const outdated = active.filter((c) => c.deployment?.has_newer_version).length;
  const counts = {
    deployed: active.filter((c) => c.deployment_status === 'deployed').length,
    pending: active.filter((c) => c.deployment_status === 'pending').length,
    failed: active.filter((c) => c.deployment_status === 'failed').length,
    none: active.filter((c) => !c.deployment_status && !c.has_deployment).length,
  };

  // One tree, one indent, one expand model — shared with the student view.
  const { rows, setAllExpanded } = useContentTree(active, {});

  // A unit's nested submittable contents that have an example assigned (only those
  // can be released).
  const releasableDescendants = (unit: CourseContentLecturerList) =>
    active.filter(
      (c) => c.path.startsWith(unit.path + '.') && c.is_submittable && (c.has_deployment || !!c.deployment_status),
    );

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader breadcrumbs={crumbs} title="Assignments" />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            {/* Summary — the at-a-glance deployment signal */}
            <StatGrid columns={5}>
              <StatCard label="Contents" value={active.length} />
              <StatCard label="Assignments" value={submittable} tone="info" />
              <StatCard label="Deployed" value={counts.deployed} tone="success" />
              <StatCard label="Pending" value={counts.pending} tone="warning" />
              <StatCard label="Failed / none" value={counts.failed + counts.none} tone="error" />
            </StatGrid>

            {outdated > 0 && (
              <Notice tone="warning">
                {outdated} deployed content(s) have a newer example version available.
              </Notice>
            )}

            <Toolbar end={releaseMsg && <span className="text-sm text-muted">{releaseMsg}</span>}>
              <Button
                onClick={() => release('all')}
                size="sm"
                disabled={releasing !== null || counts.pending + counts.failed === 0}
                loading={releasing === 'all'}
                loadingLabel="Releasing…"
                title="Deploy every pending/failed assignment into the template repo"
              >
                Release all pending ({counts.pending + counts.failed})
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => release('all-force', undefined, true)}
                disabled={releasing !== null || counts.deployed + counts.pending + counts.failed === 0}
                loading={releasing === 'all-force'}
                loadingLabel="Re-releasing…"
                title="Re-deploy ALL assignments (including already-deployed) — fills both the template and reference repos"
              >
                Re-release all (force)
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setAllExpanded(false)}>
                Collapse all
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setAllExpanded(true)}>
                Expand all
              </Button>
            </Toolbar>

            {/* Content tree with deployment badges */}
            {active.length === 0 ? (
              <EmptyState
                title="No course contents yet"
                description="Units and assignments arrive by uploading a course deployment file."
              />
            ) : (
              <TreeRows>
                {rows.map(({ key, item, depth, label, expanded, hasChildren, toggle }) => {
                  // Nothing is synthesised for the lecturer list — the endpoint
                  // returns the units themselves — so every row has an item.
                  if (!item) return null;
                  const c = item;
                  const type = c.course_content_type ?? typeMap[c.course_content_type_id];
                  const badge = deploymentBadge(c);
                  // Hidden here, or hidden by a unit above / the course itself.
                  const hidden = c.visible_effective === false;
                  const hiddenHere = c.visible === false;
                  const canReleaseOne = c.is_submittable && (c.has_deployment || !!c.deployment_status);
                  const unitKids = c.is_submittable ? [] : releasableDescendants(c);

                  return (
                    <TreeRow
                      key={key}
                      depth={depth}
                      expandable={hasChildren}
                      expanded={expanded}
                      onToggle={toggle}
                      markerColor={type?.color}
                      markerTitle={type?.title || type?.slug || 'content'}
                      label={label}
                      hidden={hidden}
                    >
                      {hidden && (
                        <Badge
                          tone="muted"
                          className="shrink-0"
                          title={
                            hiddenHere
                              ? 'Students do not see this or anything under it.'
                              : 'Hidden because a unit above this one, or the course, is hidden.'
                          }
                        >
                          Invisible
                        </Badge>
                      )}
                      {type && (
                        <Badge tone="muted" className="shrink-0">
                          {type.slug}
                        </Badge>
                      )}
                      {c.is_submittable && (c.max_test_runs != null || c.max_submissions != null) && (
                        <Badge
                          tone="info"
                          className="shrink-0"
                          title={
                            `Test runs: ${formatLimit(c.max_test_runs)} · ` +
                            `Submissions: ${formatLimit(c.max_submissions)}`
                          }
                        >
                          {formatLimit(c.max_test_runs)}T / {formatLimit(c.max_submissions)}S
                        </Badge>
                      )}
                      {c.deployment?.has_newer_version && (
                        <Badge tone="warning" className="shrink-0" title="A newer example version is available">
                          update available
                        </Badge>
                      )}
                      {/* Only offered where the lecturer can actually change
                          the outcome. A row hidden by an ancestor stays hidden
                          whatever we set here, so it gets the badge and no
                          control -- an inert toggle would be a lie. */}
                      {(!hidden || hiddenHere) && (
                        <Button
                          variant="ghost"
                          size="xs"
                          className="shrink-0"
                          loading={togglingVisibility === c.id}
                          loadingLabel="…"
                          onClick={() => toggleVisibility(c)}
                          title={
                            hiddenHere
                              ? 'Show this to students again'
                              : 'Hide this from students, along with everything under it'
                          }
                        >
                          {hiddenHere ? 'Show' : 'Hide'}
                        </Button>
                      )}
                      {canReleaseOne && (
                        <Button
                          variant="ghost"
                          size="xs"
                          className="shrink-0"
                          onClick={() => release(c.id, [c.id])}
                          disabled={releasing !== null}
                          loading={releasing === c.id}
                          loadingLabel="…"
                        >
                          Release
                        </Button>
                      )}
                      {!canReleaseOne && unitKids.length > 0 && (
                        <Button
                          variant="ghost"
                          size="xs"
                          className="shrink-0"
                          onClick={() => release(c.id, unitKids.map((k) => k.id))}
                          disabled={releasing !== null}
                          loading={releasing === c.id}
                          loadingLabel="…"
                          title={`Release ${unitKids.length} assignment(s) in this unit`}
                        >
                          Release unit ({unitKids.length})
                        </Button>
                      )}
                      <Badge tone={badge.tone} className="shrink-0">
                        {badge.label}
                      </Badge>
                      <ButtonLink
                        href={`/courses/${courseId}/lecturer/assignments/${c.id}`}
                        variant="ghost"
                        size="xs"
                        className="shrink-0"
                      >
                        Open
                      </ButtonLink>
                    </TreeRow>
                  );
                })}
              </TreeRows>
            )}

            {archivedCount > 0 && (
              <p className="text-xs text-subtle">{archivedCount} archived content(s) hidden.</p>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
