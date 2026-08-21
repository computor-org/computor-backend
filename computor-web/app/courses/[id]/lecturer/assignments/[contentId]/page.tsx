'use client';

import { useParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '@/src/contexts/AuthContext';
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
import { deploymentBadge } from '@/src/utils/deployment';
import { CourseContentsClient } from '@/src/generated/clients/CourseContentsClient';

const contentsClient = new CourseContentsClient();

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

  const content = data?.content ?? null;
  const name = displayName(content, 'Content');
  const crumbs = useCourseCrumbs(
    courseId,
    { label: 'Assignments', href: `/courses/${courseId}/lecturer/assignments` },
    name,
  );

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You need lecturer access (or higher) on this course to see its content." />;
  }

  const badge = content ? deploymentBadge(content) : null;
  const type = content?.course_content_type;
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
              {content.is_submittable && <Badge tone="info">Assignment</Badge>}
              {!content.is_submittable && <Badge tone="muted">Unit</Badge>}
              {hidden && (
                <Badge
                  tone="muted"
                  title={
                    hiddenHere
                      ? 'Students do not see this or anything under it.'
                      : 'Hidden because a unit above this one, or the course, is hidden.'
                  }
                >
                  Invisible to students
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
              Edit
            </ButtonLink>
          )
        }
      >
        {content && (
          <>
            {content.is_submittable && (
              <StatGrid columns={3}>
                <StatCard label="Max group size" value={formatLimit(content.max_group_size)} />
                <StatCard label="Max test runs" value={formatLimit(content.max_test_runs)} />
                <StatCard label="Max submissions" value={formatLimit(content.max_submissions)} />
              </StatGrid>
            )}

            <SectionCard title="Description">
              {content.description ? (
                <div className="prose prose-slate max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{content.description}</ReactMarkdown>
                </div>
              ) : (
                <EmptyState compact title="No description." />
              )}
            </SectionCard>

            <SectionCard title="Placement">
              <DescriptionList
                items={[
                  { term: 'Path', value: content.path, mono: true },
                  { term: 'Type', value: type ? displayName(type, type.slug) : '—' },
                  { term: 'Kind', value: content.course_content_kind_id },
                  { term: 'Position', value: String(content.position) },
                ]}
              />
            </SectionCard>

            <SectionCard title="Deployment">
              {deployment ? (
                <DescriptionList
                  items={[
                    { term: 'Example', value: deployment.example_identifier ?? '—', mono: true },
                    { term: 'Version', value: deployment.version_tag ?? deployment.version_identifier ?? '—' },
                    { term: 'Status', value: deployment.deployment_status },
                    {
                      term: 'Deployed',
                      value: deployment.deployed_at
                        ? new Date(deployment.deployed_at).toLocaleString()
                        : 'Not yet',
                    },
                    ...(deployment.deployment_message
                      ? [{ term: 'Message', value: deployment.deployment_message }]
                      : []),
                  ]}
                />
              ) : (
                <EmptyState
                  compact
                  title={
                    content.is_submittable
                      ? 'No example assigned to this assignment yet.'
                      : 'Units carry no example of their own.'
                  }
                />
              )}

              {history.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-fg mb-2">History</h3>
                  <ul className="text-sm text-muted space-y-1">
                    {history.slice(0, 10).map((h) => (
                      <li key={h.id} className="flex gap-3">
                        <span className="text-subtle shrink-0 w-40">
                          {h.created_at ? new Date(h.created_at).toLocaleString() : '—'}
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
