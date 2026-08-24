'use client';

import { useState, type ReactNode } from 'react';
import { useParams } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { UserClient } from '@/src/generated/clients/UserClient';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useNotify } from '@/src/contexts/NotificationContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import DescriptionList from '@/src/components/DescriptionList';
import SectionCard from '@/src/components/SectionCard';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import Notice from '@/src/components/ui/Notice';
import CourseWorkspaceLaunchButtons from '@/src/components/workspaces/CourseWorkspaceLaunchButtons';
import { displayName } from '@/src/utils/displayName';
import type { StudentRepositoryProvisioned } from 'types/generated';

const coursesClient = new CoursesClient();
const courseFamiliesClient = new CourseFamiliesClient();
const organizationsClient = new OrganizationsClient();

const userClient = new UserClient();
export default function CoursePage() {
  const courseId = useParams().id as string;
  const { canManageHierarchy: canManage, isAdmin, isOrganizationManager, courseHasAtLeast, courseRole, courseRoles } = usePermissions();
  const canManageMembers = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const { data, loading, error, reload } = useResource(
    async () => {
      const course = await coursesClient.getCoursesCoursesIdGet({ id: courseId });
      const [organization, courseFamily, gitBinding, myRepo, gitDescriptor] = await Promise.all([
        organizationsClient.getOrganizationsOrganizationsIdGet({ id: course.organization_id }).catch(() => null),
        courseFamiliesClient.getCourseFamiliesCourseFamiliesIdGet({ id: course.course_family_id }).catch(() => null),
        // Git binding is lecturer-cohort only; fetch it only for managers.
        canManageMembers
          ? coursesClient.getCourseGitBindingEndpointCoursesCourseIdGitGet({ courseId }).catch(() => null)
          : Promise.resolve(null),
        // The caller's own repository. 404s (→ null) when they aren't a member.
        userClient.getStudentRepositoryEndpointUserCoursesCourseIdRepositoryGet({ courseId }).catch(() => null),
        // Whether this course provisions git at all — drives the repo section
        // (everyone), so a non-git course never shows the provision button.
        userClient.getCourseGitDescriptorEndpointUserCoursesCourseIdGitGet({ courseId }).catch(() => null),
      ]);
      return { course, organization, courseFamily, gitBinding, myRepo, gitDescriptor };
    },
    [courseId, canManageMembers],
  );
  const course = data?.course ?? null;
  const organization = data?.organization ?? null;
  const courseFamily = data?.courseFamily ?? null;
  const gitBinding = data?.gitBinding ?? null;
  const myRepo = data?.myRepo ?? null;
  const gitDescriptor = data?.gitDescriptor ?? null;
  // The course actually provisions git repos — the exact condition under which
  // provision-repository succeeds (binding present + git delivery). Gate the
  // repo section on this so a non-git course never offers the provision button.
  const gitConfigured = gitDescriptor?.configured === true && gitDescriptor?.delivery === 'git';

  // The caller's own standing in this course, as a label ('Student',
  // 'Lecturer', …) or null when they hold no course role.
  const myRole = courseRole(courseId);

  // Where this course's work actually happens, so the overview isn't a dead
  // end that leaves the sidebar as the only way on. The lecturer cohort is
  // sent to their own authoring list; a plain member to the student one. A
  // tutor-only member has no destination while the tutor view is disabled,
  // and then the header simply carries no primary action.
  const workHref = canManageMembers
    ? `/courses/${courseId}/lecturer/assignments`
    : (courseRoles[courseId] ?? []).includes('_student')
      ? `/courses/${courseId}/student/assignments`
      : null;

  const notify = useNotify();
  const [ensuring, setEnsuring] = useState(false);
  const [provisioned, setProvisioned] = useState<StudentRepositoryProvisioned | null>(null);

  async function ensureGitAccess() {
    setEnsuring(true);
    setProvisioned(null);
    try {
      const r = await userClient.provisionStudentRepositoryEndpointUserCoursesCourseIdProvisionRepositoryPost(
        { courseId },
      );
      setProvisioned(r);
      notify('Git access ensured.', 'success');
      await reload(); // refresh the persisted repository details below
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to ensure git access', 'error');
    } finally {
      setEnsuring(false);
    }
  }

  if (loading) {
    return (
      <AuthenticatedLayout>
        <ListPageLayout>
          <ListLoading />
        </ListPageLayout>
      </AuthenticatedLayout>
    );
  }

  if (error || !course) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <ErrorBanner>{error || 'Course not found'}</ErrorBanner>
        </div>
      </AuthenticatedLayout>
    );
  }

  // Hierarchy breadcrumb: Organization › Course family › Course, falling back to
  // the flat Courses list when those aren't readable (e.g. for students).
  const crumbs: { label: string; href?: string }[] = [];
  if (organization)
    crumbs.push({ label: displayName(organization), href: `/organizations/${organization.id}` });
  if (courseFamily)
    crumbs.push({ label: displayName(courseFamily), href: `/course-families/${courseFamily.id}` });
  if (crumbs.length === 0) crumbs.push({ label: 'Courses', href: '/courses' });
  crumbs.push({ label: displayName(course, 'Untitled Course') });

  type Fact = { term: string; value: ReactNode; mono?: boolean };
  const facts = (items: (Fact | false | null | undefined | '')[]): Fact[] =>
    items.filter(Boolean) as Fact[];

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={displayName(course, 'Untitled Course')}
          subtitle={
            course.language_code && (
              <span className="px-2 py-0.5 text-xs font-medium bg-sunken text-body rounded uppercase">
                {course.language_code}
              </span>
            )
          }
          actions={
            <>
              {workHref && (
                <ButtonLink href={workHref}>Go to assignments</ButtonLink>
              )}
              {canManage && (
                <ButtonLink href={`/courses/${courseId}/edit`} variant="secondary">
                  Edit
                </ButtonLink>
              )}
            </>
          }
        />

        <ScrollArea>
        {/* Ordered by what a member came here to do — open the editor, check
            that their repository is in place — not by what the course *is*.
            About holds the description and a handful of facts, so it reads as
            reference material and sits last. */}
        {/* Workspaces — launch buttons for the course's allowed templates.
            The component hides itself (card and heading included) when the
            course offers none; the role gate only avoids a guaranteed-403
            fetch for non-members. The card chrome is the caller's because the
            compact variant on the courses list renders without one. */}
        {(isAdmin || myRole != null) && (
          <CourseWorkspaceLaunchButtons
            courseId={courseId}
            title="Workspaces"
            className="bg-surface rounded-lg border border-rule p-6"
          />
        )}

        {/* Git — the caller's own repository (+ ensure access) when the course
            uses git, then the course binding for managers. Hidden entirely for a
            student on a course that doesn't provision git. */}
        {(gitConfigured || canManageMembers) && (
        <SectionCard title="Git">
          {/* Your repository — only when the course actually provisions git, so
              the provision button is never offered on a non-git course. */}
          {gitConfigured && (
          <div>
            <h3 className="text-sm font-semibold text-fg mb-2">Your repository</h3>
            {myRepo ? (
              <DescriptionList
                items={facts([
                  { term: 'Mode', value: myRepo.mode },
                  myRepo.provider_type && { term: 'Provider', value: myRepo.provider_type },
                  myRepo.repo_ref && { term: 'Repository', value: myRepo.repo_ref, mono: true },
                  myRepo.web_url && {
                    term: 'Web',
                    value: (
                      <a href={myRepo.web_url} target="_blank" rel="noreferrer" className="text-accent-text hover:underline">
                        {myRepo.web_url}
                      </a>
                    ),
                  },
                  myRepo.http_url && { term: 'Clone (HTTPS)', value: myRepo.http_url, mono: true },
                ])}
              />
            ) : (
              <p className="text-sm text-muted">
                You don&apos;t have a repository for this course yet.
              </p>
            )}

            <Button
              className="mt-4"
              onClick={ensureGitAccess}
              loading={ensuring}
              loadingLabel="Working…"
            >
              {myRepo ? 'Repair git access' : 'Ensure git access'}
            </Button>
            <p className="mt-2 text-xs text-muted">
              Creates or repairs your repository for this course
              {canManage ? ' — as staff this also grants access to the template and reference repos.' : '.'}
            </p>
            {provisioned?.clone_token && (
              <Notice tone="warning" className="mt-3">
                <p className="font-medium">One-time clone credential — copy it now, it won&apos;t be shown again.</p>
                <p className="mt-1">
                  Username: <span className="font-mono">{provisioned.clone_username}</span>
                </p>
                <p>
                  Token: <span className="font-mono break-all">{provisioned.clone_token}</span>
                </p>
              </Notice>
            )}
          </div>
          )}

          {/* Course configuration (managers only) */}
          {canManageMembers && (
            <div className="border-t border-rule-soft pt-6">
              <h3 className="text-sm font-semibold text-fg mb-2">Course configuration</h3>
              {gitBinding ? (
                <DescriptionList
                  items={facts([
                    { term: 'Delivery', value: gitBinding.delivery },
                    gitBinding.default_branch && {
                      term: 'Default branch',
                      value: gitBinding.default_branch,
                      mono: true,
                    },
                    gitBinding.student_repo_modes &&
                      gitBinding.student_repo_modes.length > 0 && {
                        term: 'Student repos',
                        value: gitBinding.student_repo_modes.join(', '),
                      },
                    {
                      term: 'Status',
                      value: gitBinding.locked ? (
                        <Badge tone="warning" title={gitBinding.lock_reason ?? undefined}>
                          Locked
                        </Badge>
                      ) : (
                        <Badge tone="success">Editable</Badge>
                      ),
                    },
                    (gitBinding.template_url || gitBinding.template_repo) && {
                      term: 'Template',
                      value: gitBinding.template_url ? (
                        <a
                          href={gitBinding.template_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-accent-text hover:underline break-all"
                        >
                          {gitBinding.template_url}
                        </a>
                      ) : (
                        gitBinding.template_repo
                      ),
                    },
                  ])}
                />
              ) : (
                <p className="text-sm text-muted">No git binding configured for this course.</p>
              )}
            </div>
          )}
        </SectionCard>
        )}
        {/* About — description + the few facts worth showing (no identifiers).
            "Your role" leads because it is the only line here that is about the
            reader. The record timestamps are administrative trivia to everyone
            below the lecturer cohort, and the language already sits in the page
            header, so neither is repeated to a student. */}
        <SectionCard title="About">
          {course.description && <p className="text-body">{course.description}</p>}
          <DescriptionList
            items={facts([
              myRole && { term: 'Your role', value: <Badge tone="info">{myRole}</Badge> },
              organization && { term: 'Organization', value: displayName(organization) },
              courseFamily && { term: 'Course family', value: displayName(courseFamily) },
              canManageMembers &&
                course.created_at && {
                  term: 'Created',
                  value: new Date(course.created_at).toLocaleDateString(),
                },
              canManageMembers &&
                course.updated_at && {
                  term: 'Last updated',
                  value: new Date(course.updated_at).toLocaleDateString(),
                },
            ])}
          />
        </SectionCard>

        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
