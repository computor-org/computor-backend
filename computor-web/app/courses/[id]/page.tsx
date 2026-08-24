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

/** What a repository mode means to the person who owns it, rather than the
    word the binding stores. */
const REPO_MODE_LABEL: Record<string, string> = {
  managed: 'Hosted for you',
  external: 'Your own repository',
  download: 'Download only',
};

const PROVIDER_LABEL: Record<string, string> = {
  forgejo: 'Forgejo',
  gitlab: 'GitLab',
};

/** A value nobody wants to select by hand — a clone URL, a token. */
function CopyValue({ value }: { value: string }) {
  const notify = useNotify();
  return (
    <span className="inline-flex items-start gap-2">
      <span className="font-mono text-xs break-all">{value}</span>
      <Button
        size="xs"
        variant="secondary"
        onClick={() =>
          navigator.clipboard
            ?.writeText(value)
            .then(() => notify('Copied.', 'success'))
            .catch(() => notify('Could not copy to clipboard', 'error'))
        }
      >
        Copy
      </Button>
    </span>
  );
}

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
  // Fully controlled rather than an `open` attribute derived from `provisioned`:
  // any unrelated re-render would otherwise snap the disclosure shut under the
  // reader while they are copying out of it.
  const [cloneOpen, setCloneOpen] = useState(false);

  async function ensureGitAccess() {
    setEnsuring(true);
    setProvisioned(null);
    try {
      const r = await userClient.provisionStudentRepositoryEndpointUserCoursesCourseIdProvisionRepositoryPost(
        { courseId },
      );
      setProvisioned(r);
      // The credential is only reachable from inside the disclosure, so open it
      // rather than leaving the freshly-fetched token hidden behind a summary.
      if (r.clone_token) setCloneOpen(true);
      notify('Git access checked — your repository is reachable.', 'success');
      await reload(); // refresh the persisted repository details below
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Could not check git access', 'error');
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
        {/* Cards are ordered by what a member came here to do — open the editor,
            check that their repository is in place — not by what the course *is*;
            About is reference material and sits last.

            Workspaces: launch buttons for the course's allowed templates. The
            component hides itself (card and heading included) when the course
            offers none; the role gate only avoids a guaranteed-403 fetch for
            non-members. The card chrome is the caller's because the compact
            variant on the courses list renders without one. */}
        {(isAdmin || myRole != null) && (
          <CourseWorkspaceLaunchButtons
            courseId={courseId}
            title="Workspaces"
            className="bg-surface rounded-lg border border-rule p-6"
          />
        )}

        {/* Your repository — status, not a chore. The repository is created and
            cloned by the VSCode extension the first time a member opens the
            course, so this frame's job is to say whether that has happened. The
            provisioning call stays reachable because it is also the self-heal
            path (it re-applies the git-server grants) and the only way to get a
            repository without the editor — but as a quiet control, not as the
            loudest button on the page. */}
        {gitConfigured && (
          <SectionCard
            title="Your repository"
            action={
              <div className="flex items-center gap-2">
                {myRepo ? (
                  <Badge tone="success" pill>Ready</Badge>
                ) : (
                  <Badge tone="muted" pill>Not set up yet</Badge>
                )}
                <Button size="sm" variant="secondary" onClick={ensureGitAccess} loading={ensuring} loadingLabel="Checking…">
                  Check access
                </Button>
              </div>
            }
          >
            {myRepo ? (
              <>
                <p className="text-sm text-muted">
                  Set up automatically when you opened this course in VS Code. Your work is
                  pushed from there — nothing here needs doing.
                </p>
                <DescriptionList
                  items={facts([
                    myRepo.repo_ref && { term: 'Repository', value: myRepo.repo_ref, mono: true },
                    myRepo.web_url && {
                      term: 'Browse',
                      value: (
                        <a
                          href={myRepo.web_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-accent-text hover:underline break-all"
                        >
                          {myRepo.web_url}
                        </a>
                      ),
                    },
                  ])}
                />
              </>
            ) : canManageMembers ? (
              // Staff reach this page without ever opening the course in the
              // editor, and for them the call does something the sentence above
              // would not explain: it re-grants their access to the canonical
              // template and reference repositories.
              <p className="text-sm text-muted">
                No repository has been created for you yet. Members get one automatically the
                first time they open the course in VS Code; Check access creates yours now and
                re-grants your staff access to the template and reference repositories.
              </p>
            ) : (
              <p className="text-sm text-muted">
                Nothing to do here. Your repository is created for you the first time you open
                this course in VS Code — in a Computor workspace or with the Computor extension.
              </p>
            )}

            {/* Clone details and the credential: needed only by someone working
                outside the editor, so they are folded away rather than pushed at
                a student who will never type a git command. */}
            <details
              className="border-t border-rule-soft pt-4"
              open={cloneOpen}
              onToggle={(e) => setCloneOpen(e.currentTarget.open)}
            >
              <summary className="cursor-pointer text-sm text-body marker:text-muted">
                Working outside VS Code?
              </summary>
              <div className="mt-3 space-y-3">
                <p className="text-sm text-muted">
                  A Computor workspace configures git for you. These are the details for cloning
                  the repository by hand; use <span className="font-medium">Check access</span> to
                  create it and reveal the credential.
                  {canManage
                    ? ' As staff, that call also re-grants your access to the course template and reference repositories.'
                    : ''}
                </p>
                {myRepo && (
                  <DescriptionList
                    items={facts([
                      { term: 'Hosting', value: REPO_MODE_LABEL[myRepo.mode] ?? myRepo.mode },
                      myRepo.provider_type && {
                        term: 'Git server',
                        value: PROVIDER_LABEL[myRepo.provider_type] ?? myRepo.provider_type,
                      },
                      myRepo.http_url && {
                        term: 'Clone (HTTPS)',
                        value: <CopyValue value={myRepo.http_url} />,
                      },
                    ])}
                  />
                )}
                {provisioned?.clone_token && (
                  <Notice tone="warning">
                    <p className="font-medium">
                      Your git credential for this server — treat it like a password.
                    </p>
                    <p className="mt-1">
                      It is the same credential your workspace already uses, so it is shown again
                      whenever you check access; it is not a one-time secret.
                    </p>
                    <dl className="mt-2 space-y-1">
                      <div className="flex gap-2">
                        <dt className="w-20 shrink-0">Username</dt>
                        <dd><CopyValue value={provisioned.clone_username ?? ''} /></dd>
                      </div>
                      <div className="flex gap-2">
                        <dt className="w-20 shrink-0">Token</dt>
                        <dd><CopyValue value={provisioned.clone_token} /></dd>
                      </div>
                    </dl>
                  </Notice>
                )}
              </div>
            </details>
          </SectionCard>
        )}

        {/* Git configuration — the course's binding. Its own card: it describes
            the course, not the reader, and only the lecturer cohort sees it. */}
        {canManageMembers && (
          <SectionCard title="Git configuration">
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
