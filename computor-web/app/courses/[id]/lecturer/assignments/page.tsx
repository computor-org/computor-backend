'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
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

const COPY = {
  de: {
    assignments: 'Aufgaben',
    releaseFailedStatus: (status: number) => `Freigabe fehlgeschlagen (${status})`,
    releaseStarted: 'Freigabe gestartet. Der Status wechselt zu „Wird bereitgestellt“ und dann zu „Bereitgestellt“.',
    releaseFailed: 'Freigabe fehlgeschlagen',
    failedStatus: (status: number) => `Fehlgeschlagen (${status})`,
    visibilityFailed: 'Die Sichtbarkeit konnte nicht geändert werden',
    contents: 'Inhalte',
    deployed: 'Bereitgestellt',
    pending: 'Ausstehend',
    failedNone: 'Fehlgeschlagen / keine',
    outdated: (n: number) => `Für ${n} bereitgestellte(n) Inhalt(e) ist eine neuere Beispielversion verfügbar.`,
    releasing: 'Wird freigegeben …',
    releaseAllTitle: 'Alle ausstehenden oder fehlgeschlagenen Aufgaben im Vorlagen-Repository bereitstellen',
    releaseAll: (n: number) => `Alle ausstehenden freigeben (${n})`,
    rereleasing: 'Wird erneut freigegeben …',
    rereleaseTitle: 'ALLE Aufgaben erneut bereitstellen (auch bereits bereitgestellte), füllt Vorlagen- und Referenz-Repository',
    rereleaseAll: 'Alle erneut freigeben (erzwingen)',
    collapseAll: 'Alle einklappen',
    expandAll: 'Alle ausklappen',
    emptyTitle: 'Noch keine Kursinhalte',
    emptyDescription: 'Einheiten und Aufgaben kommen durch das Hochladen einer Kurs-Deployment-Datei hinzu.',
    contentMarker: 'Inhalt',
    hiddenHereTitle: 'Studierende sehen das und alles darunter nicht.',
    hiddenAboveTitle: 'Verborgen, weil eine Einheit darüber oder der Kurs verborgen ist.',
    invisible: 'Unsichtbar',
    limitsTitle: (runs: string, subs: string) => `Testläufe: ${runs} · Abgaben: ${subs}`,
    limitsBadge: (runs: string, subs: string) => `${runs}T / ${subs}A`,
    newerTitle: 'Eine neuere Beispielversion ist verfügbar',
    updateAvailable: 'Update verfügbar',
    showTitle: 'Das wieder für Studierende anzeigen',
    hideTitle: 'Das samt allem darunter vor Studierenden verbergen',
    show: 'Einblenden',
    hide: 'Ausblenden',
    release: 'Freigeben',
    releaseUnitTitle: (n: number) => `${n} Aufgabe(n) in dieser Einheit freigeben`,
    releaseUnit: (n: number) => `Einheit freigeben (${n})`,
    open: 'Öffnen',
    archived: (n: number) => `${n} archivierte(r) Inhalt(e) ausgeblendet.`,
  },
  en: {
    assignments: 'Assignments',
    releaseFailedStatus: (status: number) => `Release failed (${status})`,
    releaseStarted: 'Release started — badges move to “deploying”, then “deployed”.',
    releaseFailed: 'Release failed',
    failedStatus: (status: number) => `Failed (${status})`,
    visibilityFailed: 'Could not change visibility',
    contents: 'Contents',
    deployed: 'Deployed',
    pending: 'Pending',
    failedNone: 'Failed / none',
    outdated: (n: number) => `${n} deployed content(s) have a newer example version available.`,
    releasing: 'Releasing…',
    releaseAllTitle: 'Deploy every pending/failed assignment into the template repo',
    releaseAll: (n: number) => `Release all pending (${n})`,
    rereleasing: 'Re-releasing…',
    rereleaseTitle: 'Re-deploy ALL assignments (including already-deployed) — fills both the template and reference repos',
    rereleaseAll: 'Re-release all (force)',
    collapseAll: 'Collapse all',
    expandAll: 'Expand all',
    emptyTitle: 'No course contents yet',
    emptyDescription: 'Units and assignments arrive by uploading a course deployment file.',
    contentMarker: 'content',
    hiddenHereTitle: 'Students do not see this or anything under it.',
    hiddenAboveTitle: 'Hidden because a unit above this one, or the course, is hidden.',
    invisible: 'Invisible',
    limitsTitle: (runs: string, subs: string) => `Test runs: ${runs} · Submissions: ${subs}`,
    limitsBadge: (runs: string, subs: string) => `${runs}T / ${subs}S`,
    newerTitle: 'A newer example version is available',
    updateAvailable: 'update available',
    showTitle: 'Show this to students again',
    hideTitle: 'Hide this from students, along with everything under it',
    show: 'Show',
    hide: 'Hide',
    release: 'Release',
    releaseUnitTitle: (n: number) => `Release ${n} assignment(s) in this unit`,
    releaseUnit: (n: number) => `Release unit (${n})`,
    open: 'Open',
    archived: (n: number) => `${n} archived content(s) hidden.`,
  },
};

export default function LecturerContentPage() {
  const courseId = useParams().id as string;
  const language = useUiLanguage();
  const t = COPY[language];
  const crumbs = useCourseCrumbs(courseId, t.assignments);

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
      typeMap = Object.fromEntries(types.map((ty) => [ty.id, ty]));
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
        throw new Error(err?.detail || err?.message || t.releaseFailedStatus(res.status));
      }
      setReleaseMsg(t.releaseStarted);
      setTimeout(() => reload(), 3000);
    } catch (e) {
      setReleaseMsg(e instanceof Error ? e.message : t.releaseFailed);
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
        throw new Error(err?.detail || err?.message || t.failedStatus(res.status));
      }
      reload();
    } catch (e) {
      setReleaseMsg(e instanceof Error ? e.message : t.visibilityFailed);
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
        <PageHeader breadcrumbs={crumbs} title={t.assignments} />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            {/* Summary — the at-a-glance deployment signal */}
            <StatGrid columns={5}>
              <StatCard label={t.contents} value={active.length} />
              <StatCard label={t.assignments} value={submittable} tone="info" />
              <StatCard label={t.deployed} value={counts.deployed} tone="success" />
              <StatCard label={t.pending} value={counts.pending} tone="warning" />
              <StatCard label={t.failedNone} value={counts.failed + counts.none} tone="error" />
            </StatGrid>

            {outdated > 0 && (
              <Notice tone="warning">
                {t.outdated(outdated)}
              </Notice>
            )}

            <Toolbar end={releaseMsg && <span className="text-sm text-muted">{releaseMsg}</span>}>
              <Button
                onClick={() => release('all')}
                size="sm"
                disabled={releasing !== null || counts.pending + counts.failed === 0}
                loading={releasing === 'all'}
                loadingLabel={t.releasing}
                title={t.releaseAllTitle}
              >
                {t.releaseAll(counts.pending + counts.failed)}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => release('all-force', undefined, true)}
                disabled={releasing !== null || counts.deployed + counts.pending + counts.failed === 0}
                loading={releasing === 'all-force'}
                loadingLabel={t.rereleasing}
                title={t.rereleaseTitle}
              >
                {t.rereleaseAll}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setAllExpanded(false)}>
                {t.collapseAll}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setAllExpanded(true)}>
                {t.expandAll}
              </Button>
            </Toolbar>

            {/* Content tree with deployment badges */}
            {active.length === 0 ? (
              <EmptyState
                title={t.emptyTitle}
                description={t.emptyDescription}
              />
            ) : (
              <TreeRows>
                {rows.map(({ key, item, depth, label, expanded, hasChildren, toggle }) => {
                  // Nothing is synthesised for the lecturer list — the endpoint
                  // returns the units themselves — so every row has an item.
                  if (!item) return null;
                  const c = item;
                  const type = c.course_content_type ?? typeMap[c.course_content_type_id];
                  const badge = deploymentBadge(c, language);
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
                      markerTitle={type?.title || type?.slug || t.contentMarker}
                      label={label}
                      hidden={hidden}
                    >
                      {hidden && (
                        <Badge
                          tone="muted"
                          className="shrink-0"
                          title={
                            hiddenHere
                              ? t.hiddenHereTitle
                              : t.hiddenAboveTitle
                          }
                        >
                          {t.invisible}
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
                            t.limitsTitle(
                              formatLimit(c.max_test_runs, language),
                              formatLimit(c.max_submissions, language),
                            )
                          }
                        >
                          {t.limitsBadge(formatLimit(c.max_test_runs, language), formatLimit(c.max_submissions, language))}
                        </Badge>
                      )}
                      {c.deployment?.has_newer_version && (
                        <Badge tone="warning" className="shrink-0" title={t.newerTitle}>
                          {t.updateAvailable}
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
                              ? t.showTitle
                              : t.hideTitle
                          }
                        >
                          {hiddenHere ? t.show : t.hide}
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
                          {t.release}
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
                          title={t.releaseUnitTitle(unitKids.length)}
                        >
                          {t.releaseUnit(unitKids.length)}
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
                        {t.open}
                      </ButtonLink>
                    </TreeRow>
                  );
                })}
              </TreeRows>
            )}

            {archivedCount > 0 && (
              <p className="text-xs text-subtle">{t.archived(archivedCount)}</p>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
