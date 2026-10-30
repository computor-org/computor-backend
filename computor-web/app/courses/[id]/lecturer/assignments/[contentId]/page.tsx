'use client';

import { useParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import DetailPanel from '@/src/components/DetailPanel';
import Forbidden from '@/src/components/Forbidden';
import SectionCard from '@/src/components/SectionCard';
import DescriptionList from '@/src/components/DescriptionList';
import Badge from '@/src/components/Badge';
import EmptyState from '@/src/components/EmptyState';
import { ButtonLink } from '@/src/components/ui/Button';
import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import { formatLimit } from '@/src/utils/limits';
import { displayName } from '@/src/utils/displayName';
import { deploymentBadge, deploymentStatusLabel } from '@/src/utils/deployment';
import { CourseContentsClient } from '@/src/generated/clients/CourseContentsClient';
import { localized } from '@/src/utils/localizedText';

const contentsClient = new CourseContentsClient();

const COPY = {
  de: {
    content: 'Inhalt',
    assignments: 'Aufgaben',
    forbidden: 'Zum Ansehen dieses Inhalts brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    assignment: 'Aufgabe',
    unit: 'Einheit',
    hiddenHereTitle: 'Studierende sehen das und alles darunter nicht.',
    hiddenAboveTitle: 'Verborgen, weil eine Einheit darüber oder der Kurs verborgen ist.',
    invisible: 'Für Studierende unsichtbar',
    edit: 'Bearbeiten',
    maxGroupSize: 'Maximale Gruppengröße',
    maxTestRuns: 'Maximale Testläufe',
    maxSubmissions: 'Maximale Abgaben',
    description: 'Beschreibung',
    noDescription: 'Keine Beschreibung.',
    placement: 'Einordnung',
    path: 'Pfad in der Kursdatei',
    type: 'Typ',
    kind: 'Art',
    position: 'Position',
    deployment: 'Bereitstellung',
    example: 'Beispiel',
    version: 'Version',
    status: 'Status',
    deployed: 'Bereitgestellt',
    notYet: 'Noch nicht',
    message: 'Meldung',
    noExample: 'Dieser Aufgabe ist noch kein Beispiel zugewiesen.',
    noExampleUnit: 'Einheiten haben kein eigenes Beispiel.',
    history: 'Verlauf',
  },
  en: {
    content: 'Content',
    assignments: 'Assignments',
    forbidden: 'You need lecturer access (or higher) on this course to see its content.',
    assignment: 'Assignment',
    unit: 'Unit',
    hiddenHereTitle: 'Students do not see this or anything under it.',
    hiddenAboveTitle: 'Hidden because a unit above this one, or the course, is hidden.',
    invisible: 'Invisible to students',
    edit: 'Edit',
    maxGroupSize: 'Max group size',
    maxTestRuns: 'Max test runs',
    maxSubmissions: 'Max submissions',
    description: 'Description',
    noDescription: 'No description.',
    placement: 'Placement',
    path: 'Path in the course file',
    type: 'Type',
    kind: 'Kind',
    position: 'Position',
    deployment: 'Deployment',
    example: 'Example',
    version: 'Version',
    status: 'Status',
    deployed: 'Deployed',
    notYet: 'Not yet',
    message: 'Message',
    noExample: 'No example assigned to this assignment yet.',
    noExampleUnit: 'Units carry no example of their own.',
    history: 'History',
  },
};

/**
 * Read-only view of one unit or assignment.
 *
 * The lecturer's only route into a content used to be the edit form, so
 * "what is this, and is it deployed?" could not be answered without opening a
 * page whose Save button was one keystroke away — while a student, looking at
 * the same row, got a proper detail page. Edit is now an action here.
 */
export default function CourseContentDetailPage() {
  const params = useParams();
  const courseId = params.id as string;
  const contentId = params.contentId as string;
  const language = useUiLanguage();
  const t = COPY[language];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const { data, loading, error } = useResource(
    async () => {
      const content = await contentsClient.getCourseContentsCourseContentsIdGet({ id: contentId });
      // The base GET only carries has_deployment/deployment_status; the record
      // itself lives behind its own endpoint. 404s for a content that has never
      // been assigned an example, which is a normal state, not a failure.
      const deployment = await contentsClient
        .getContentDeploymentCourseContentsContentIdDeploymentGet({ contentId })
        .catch(() => null);
      return { content, deployment };
    },
    [contentId],
    { enabled: canManage },
  );

  // Display only; the edit page keeps the source text it saves back.
  const content = localized(data?.content ?? null, language);
  const name = displayName(content, t.content);
  const crumbs = useCourseCrumbs(
    courseId,
    { label: t.assignments, href: `/courses/${courseId}/lecturer/assignments` },
    name,
  );

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  const badge = content ? deploymentBadge(content, language) : null;
  const type = localized(content?.course_content_type ?? null, language);
  const deployment = data?.deployment?.deployment ?? null;
  const history = data?.deployment?.history ?? [];
  // Hidden here, or hidden by a unit above this one / the course itself.
  const hiddenHere = content?.visible === false;
  const hidden = content?.visible_effective === false;

  return (
    <AuthenticatedLayout>
      <DetailPanel
        breadcrumbs={crumbs}
        title={name}
        loading={loading}
        error={error}
        subtitle={
          content && (
            <div className="flex flex-wrap items-center gap-2">
              {badge && <Badge tone={badge.tone}>{badge.label}</Badge>}
              {content.is_submittable && <Badge tone="info">{t.assignment}</Badge>}
              {!content.is_submittable && <Badge tone="muted">{t.unit}</Badge>}
              {hidden && (
                <Badge
                  tone="muted"
                  title={
                    hiddenHere
                      ? t.hiddenHereTitle
                      : t.hiddenAboveTitle
                  }
                >
                  {t.invisible}
                </Badge>
              )}
            </div>
          )
        }
        actions={
          content && (
            <ButtonLink
              href={`/courses/${courseId}/lecturer/assignments/${contentId}/edit`}
              variant="secondary"
            >
              {t.edit}
            </ButtonLink>
          )
        }
      >
        {content && (
          <>
            {content.is_submittable && (
              <StatGrid columns={3}>
                <StatCard label={t.maxGroupSize} value={formatLimit(content.max_group_size, language)} />
                <StatCard label={t.maxTestRuns} value={formatLimit(content.max_test_runs, language)} />
                <StatCard label={t.maxSubmissions} value={formatLimit(content.max_submissions, language)} />
              </StatGrid>
            )}

            <SectionCard title={t.description}>
              {content.description ? (
                <div className="prose markdown max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.description}</ReactMarkdown>
                </div>
              ) : (
                <EmptyState compact title={t.noDescription} />
              )}
            </SectionCard>

            <SectionCard title={t.placement}>
              <DescriptionList
                items={[
                  { term: t.path, value: content.path, mono: true },
                  { term: t.type, value: type ? displayName(type, type.slug) : '—' },
                  { term: t.kind, value: content.is_submittable ? t.assignment : t.unit },
                  { term: t.position, value: String(content.position) },
                ]}
              />
            </SectionCard>

            <SectionCard title={t.deployment}>
              {deployment ? (
                <DescriptionList
                  items={[
                    { term: t.example, value: deployment.example_identifier ?? '—', mono: true },
                    { term: t.version, value: deployment.version_tag ?? deployment.version_identifier ?? '—' },
                    { term: t.status, value: deploymentStatusLabel(deployment.deployment_status, language) },
                    {
                      term: t.deployed,
                      value: formatDateTime(deployment.deployed_at, language, t.notYet),
                    },
                    ...(deployment.deployment_message
                      ? [{ term: t.message, value: deployment.deployment_message }]
                      : []),
                  ]}
                />
              ) : (
                <EmptyState
                  compact
                  title={
                    content.is_submittable
                      ? t.noExample
                      : t.noExampleUnit
                  }
                />
              )}

              {history.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-fg mb-2">{t.history}</h3>
                  <ul className="text-sm text-muted space-y-1">
                    {history.slice(0, 10).map((h) => (
                      <li key={h.id} className="flex gap-3">
                        <span className="text-subtle shrink-0 w-40">
                          {formatDateTime(h.created_at, language)}
                        </span>
                        <span className="min-w-0">
                          {h.action}
                          {h.version_tag ? ` · ${h.version_tag}` : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </SectionCard>
          </>
        )}
      </DetailPanel>
    </AuthenticatedLayout>
  );
}
