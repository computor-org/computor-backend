'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useLecturerCopy } from '@/src/hooks/useLecturerCopy';
import { LecturersClient } from '@/src/generated/clients/LecturersClient';
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
  const t = useLecturerCopy();
  const courseId = useParams().id as string;
  const crumbs = useCourseCrumbs(courseId, t("Assignments"));

  // reload re-fetches everything (badges move pending → deploying → deployed as
  // the release workflow runs).
  const { data, loading, error, reload } = useResource(async () => {
    // The course itself comes from CourseContext — this page only needs what is
    // specific to it.
    const [ccRes, ctRes] = await Promise.all([
      apiFetch(`${API_BASE_URL}/lecturers/course-contents?course_id=${courseId}&limit=500`),
      apiFetch(`${API_BASE_URL}/course-content-types?course_id=${courseId}&limit=200`),
    ]);
    if (!ccRes.ok || !ctRes.ok) throw new Error(t('Could not load assignments.'));
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

  const [upgrading, setUpgrading] = useState(false);
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
        setReleaseMsg(`${t('Release failed')} (HTTP ${res.status}). ${t('Try again.')}`);
        return;
      }
      setReleaseMsg(t("Release started — badges move to “deploying”, then “deployed”."));
      reload();
      setTimeout(() => reload(), 3000);
    } catch {
      setReleaseMsg(`${t("Release failed")}. ${t("Try again.")}`);
    } finally {
      setReleasing(null);
    }
  }

  async function upgrade() {
    setUpgrading(true);
    setReleaseMsg(null);
    try {
      const result = await new LecturersClient().batchUpgradeVersionsEndpointLecturersCoursesCourseIdUpgradeVersionsPost({
        courseId,
        body: { course_content_ids: contents.filter(c => !c.archived_at && c.deployment?.has_newer_version).map(c => c.id) },
      });
      setReleaseMsg(`${t("Versions selected")}: ${result.total_upgraded}. ${t("Already current")}: ${result.total_skipped}. ${t("Failed")}: ${result.total_failed}. ${t("Release pending assignments to publish the selected versions.")}`);
      reload();
    } catch {
      setReleaseMsg(t("Could not select newer versions. Try again."));
    } finally {
      setUpgrading(false);
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
        setReleaseMsg(`${t('Could not change visibility')} (HTTP ${res.status}) ${t('Try again.')}`);
        return;
      }
      reload();
    } catch {
      setReleaseMsg(`${t("Could not change visibility")} ${t("Try again.")}`);
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
    none: active.filter((c) => c.is_submittable && !c.deployment_status && !c.has_deployment).length,
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
        <PageHeader breadcrumbs={crumbs} title={t("Assignments")} />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            {/* Summary — the at-a-glance deployment signal */}
            <StatGrid columns={5}>
              <StatCard label={t("Contents")} value={active.length} />
              <StatCard label={t("Assignments")} value={submittable} tone="info" />
              <StatCard label={t("Deployed")} value={counts.deployed} tone="success" />
              <StatCard label={t("Pending")} value={counts.pending} tone="warning" />
              <StatCard label={t("Failed / none")} value={counts.failed + counts.none} tone="error" />
            </StatGrid>

            <Notice tone="info">
              {t('Existing workspaces: ask learners to open the course in the Student view, expand it and click “Refresh” to receive the released files. Their local changes are kept.')}
            </Notice>

            {outdated > 0 && (
              <Notice tone="warning">
                {t("Newer example versions available")}: {outdated}. <p>{t("Select the latest versions, then release the pending assignments. Existing learner work is kept.")}</p>
                <Button size="sm" onClick={upgrade} disabled={upgrading || releasing !== null} loading={upgrading} loadingLabel={t("Selecting versions…")}>{t("Select latest versions")} ({outdated})</Button>
              </Notice>
            )}

            <Toolbar end={releaseMsg && <span role="status" className="text-sm text-muted">{releaseMsg}</span>}>
              <Button variant="secondary" size="sm" onClick={reload} disabled={upgrading || releasing !== null}>
                {t('Refresh status')}
              </Button>
              <Button
                onClick={() => release('all')}
                size="sm"
                disabled={upgrading || releasing !== null || counts.pending + counts.failed === 0}
                loading={releasing === 'all'}
                loadingLabel={t("Releasing…")}
                title={t("Deploy every pending/failed assignment into the template repo")}
              >
                {t('Release all pending')} ({counts.pending + counts.failed})
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => release('all-force', undefined, true)}
                disabled={upgrading || releasing !== null || counts.deployed + counts.pending + counts.failed === 0}
                loading={releasing === 'all-force'}
                loadingLabel={t("Re-releasing…")}
                title={t("Re-deploy ALL assignments (including already-deployed) — fills both the template and reference repos")}
              >{t("Re-release all (force)")}</Button>
              <Button variant="ghost" size="sm" onClick={() => setAllExpanded(false)}>{t("Collapse all")}</Button>
              <Button variant="ghost" size="sm" onClick={() => setAllExpanded(true)}>{t("Expand all")}</Button>
            </Toolbar>

            {/* Content tree with deployment badges */}
            {active.length === 0 ? (
              <EmptyState
                title={t("No course contents yet")}
                description={t("Units and assignments arrive by uploading a course deployment file.")}
              />
            ) : (
              <div className="[&>div>div]:flex-wrap [&>div>div>div:nth-child(4)]:min-w-40"><TreeRows>
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
                              ? t("Students do not see this or anything under it.")
                              : t("Hidden because a unit above this one, or the course, is hidden.")
                          }
                        >{t("Invisible")}</Badge>
                      )}
                      {type && (
                        <Badge tone="muted" className="shrink-0">
                          {type.title || type.slug}
                        </Badge>
                      )}
                      {c.is_submittable && (c.max_test_runs != null || c.max_submissions != null) && (
                        <Badge
                          tone="info"
                          className="shrink-0"
                          title={
                            `${t('Test runs')}: ${formatLimit(c.max_test_runs)} · ` +
                            `${t('Submissions')}: ${formatLimit(c.max_submissions)}`
                          }
                        >
                          {formatLimit(c.max_test_runs)}T / {formatLimit(c.max_submissions)}S
                        </Badge>
                      )}
                      {c.deployment?.has_newer_version && (
                        <Badge tone="warning" className="shrink-0" title={t("A newer example version is available")}>{t("update available")}</Badge>
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
                              ? t("Show this to students again")
                              : t("Hide this from students, along with everything under it")
                          }
                        >
                          {hiddenHere ? t("Show") : t("Hide")}
                        </Button>
                      )}
                      {canReleaseOne && (
                        <Button
                          variant="ghost"
                          size="xs"
                          className="shrink-0"
                          onClick={() => release(c.id, [c.id])}
                          disabled={upgrading || releasing !== null}
                          loading={releasing === c.id}
                          loadingLabel="…"
                        >{t("Release")}</Button>
                      )}
                      {!canReleaseOne && unitKids.length > 0 && (
                        <Button
                          variant="ghost"
                          size="xs"
                          className="shrink-0"
                          onClick={() => release(c.id, unitKids.map((k) => k.id))}
                          disabled={upgrading || releasing !== null}
                          loading={releasing === c.id}
                          loadingLabel="…"
                          title={`${t('Release unit')} (${unitKids.length})`}
                        >
                          {t('Release unit')} ({unitKids.length})
                        </Button>
                      )}
                      <Badge tone={badge.tone} className="shrink-0">
                        {t(badge.label)}
                      </Badge>
                      <ButtonLink
                        href={`/courses/${courseId}/lecturer/assignments/${c.id}`}
                        variant="ghost"
                        size="xs"
                        className="shrink-0"
                      >{t("Open")}</ButtonLink>
                    </TreeRow>
                  );
                })}
              </TreeRows></div>
            )}

            {archivedCount > 0 && (
              <p className="text-xs text-subtle">{archivedCount} {t('archived contents hidden.')}</p>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
