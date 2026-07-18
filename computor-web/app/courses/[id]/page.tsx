'use client';

import { useState, type ReactNode } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
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
import CourseWorkspaceLaunchButtons from '@/src/components/workspaces/CourseWorkspaceLaunchButtons';
import type {
  CourseMemberRepositoryGet,
  StudentRepositoryProvisioned,
} from 'types/generated';

const coursesClient = new CoursesClient();
const courseFamiliesClient = new CourseFamiliesClient();
const organizationsClient = new OrganizationsClient();

interface ViewCard {
  view: string;
  href: string;
  title: string;
  desc: string;
  icon: ReactNode;
}


const userClient = new UserClient();
export default function CoursePage() {
  const courseId = useParams().id as string;
  const { canManageHierarchy: canManage, isAdmin, isOrganizationManager, courseHasAtLeast, courseRole } = usePermissions();
  const canManageMembers = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const { data, loading, error, reload } = useResource(
    async () => {
      const course = await coursesClient.getCoursesCoursesIdGet({ id: courseId });
      const [courseViews, organization, courseFamily, gitBinding, myRepo, gitDescriptor] = await Promise.all([
        userClient.getCourseViewsForCurrentUserByCourseUserViewsCourseIdGet({ courseId }).catch(() => [] as string[]),
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
      return { course, courseViews, organization, courseFamily, gitBinding, myRepo, gitDescriptor };
    },
    [courseId, canManageMembers],
  );
  const course = data?.course ?? null;
  const courseViews = data?.courseViews ?? [];
  const organization = data?.organization ?? null;
  const courseFamily = data?.courseFamily ?? null;
  const gitBinding = data?.gitBinding ?? null;
  const myRepo = data?.myRepo ?? null;
  const gitDescriptor = data?.gitDescriptor ?? null;
  // The course actually provisions git repos — the exact condition under which
  // provision-repository succeeds (binding present + git delivery). Gate the
  // repo section on this so a non-git course never offers the provision button.
  const gitConfigured = gitDescriptor?.configured === true && gitDescriptor?.delivery === 'git';

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
        <ListLoading />
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

  const viewCards: ViewCard[] = [
    {
      view: 'student',
      href: `/courses/${courseId}/student`,
      title: 'Student view',
      desc: 'Course contents & assignments',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
        </svg>
      ),
    },
    {
      view: 'tutor',
      href: `/courses/${courseId}/tutor`,
      title: 'Tutor view',
      desc: 'Students & grading',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ),
    },
    {
      view: 'lecturer',
      href: `/courses/${courseId}/lecturer`,
      title: 'Lecturer view',
      desc: 'Contents & grading',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      ),
    },
    {
      view: 'management',
      href: `/courses/${courseId}/management/members`,
      title: 'Management',
      desc: 'Members & course administration',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
    // Management is a permission (not a course role): show it to the manager
    // cohort directly, so it appears even before the backend's `management`
    // view is loaded. Student/tutor/lecturer stay driven by the course views.
  ].filter((c) => courseViews.includes(c.view) || (c.view === 'management' && canManageMembers));

  // Literal class strings so Tailwind's JIT actually emits them.
  const quickCols =
    viewCards.length >= 3 ? 'md:grid-cols-3' : viewCards.length === 2 ? 'md:grid-cols-2' : 'md:grid-cols-1';

  // Hierarchy breadcrumb: Organization › Course family › Course, falling back to
  // the flat Courses list when those aren't readable (e.g. for students).
  const crumbs: { label: string; href?: string }[] = [];
  if (organization)
    crumbs.push({ label: organization.title || organization.path, href: `/organizations/${organization.id}` });
  if (courseFamily)
    crumbs.push({ label: courseFamily.title || courseFamily.path, href: `/course-families/${courseFamily.id}` });
  if (crumbs.length === 0) crumbs.push({ label: 'Courses', href: '/courses' });
  crumbs.push({ label: course.title || course.path });

  const repoRow = (label: string, value: ReactNode) => (
    <div className="flex gap-3">
      <dt className="text-gray-500 w-28 shrink-0">{label}</dt>
      <dd className="text-gray-900 min-w-0 break-all">{value}</dd>
    </div>
  );

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={course.title || 'Untitled Course'}
          subtitle={
            <span className="flex items-center gap-3">
              <span className="font-mono text-sm truncate">{course.path}</span>
              {course.language_code && (
                <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 rounded uppercase">
                  {course.language_code}
                </span>
              )}
            </span>
          }
          actions={
            canManage && (
              <Link
                href={`/courses/${courseId}/edit`}
                className="shrink-0 px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Edit
              </Link>
            )
          }
        />

        <ScrollArea className="space-y-8">
        {/* Quick Access — the primary way into the course, so it leads. */}
        {viewCards.length > 0 && (
          <div className={`grid grid-cols-1 gap-4 ${quickCols}`}>
            {viewCards.map((c) => (
              <Link
                key={c.view}
                href={c.href}
                className="group flex items-center gap-4 p-5 bg-white border-2 border-gray-200 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition-all"
              >
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-100">
                  {c.icon}
                </span>
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900">{c.title}</h3>
                  <p className="text-xs text-gray-500">{c.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Workspaces — launch buttons for the course's allowed templates.
            The component hides itself when the course offers none; the role
            gate only avoids a guaranteed-403 fetch for non-members. */}
        {(isAdmin || courseRole(courseId) != null) && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Workspaces</h2>
            <CourseWorkspaceLaunchButtons courseId={courseId} />
          </div>
        )}

        {/* About — description + the few facts worth showing (no identifiers). */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">About</h2>
          {course.description && <p className="text-gray-700 mb-6">{course.description}</p>}
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            {organization && (
              <div>
                <dt className="text-gray-500">Organization</dt>
                <dd className="mt-1 text-gray-900">{organization.title || organization.path}</dd>
              </div>
            )}
            {courseFamily && (
              <div>
                <dt className="text-gray-500">Course family</dt>
                <dd className="mt-1 text-gray-900">{courseFamily.title || courseFamily.path}</dd>
              </div>
            )}
            {course.language_code && (
              <div>
                <dt className="text-gray-500">Language</dt>
                <dd className="mt-1 text-gray-900 uppercase">{course.language_code}</dd>
              </div>
            )}
            {course.created_at && (
              <div>
                <dt className="text-gray-500">Created</dt>
                <dd className="mt-1 text-gray-900">{new Date(course.created_at).toLocaleDateString()}</dd>
              </div>
            )}
            {course.updated_at && (
              <div>
                <dt className="text-gray-500">Last updated</dt>
                <dd className="mt-1 text-gray-900">{new Date(course.updated_at).toLocaleDateString()}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* Git — the caller's own repository (+ ensure access) when the course
            uses git, then the course binding for managers. Hidden entirely for a
            student on a course that doesn't provision git. */}
        {(gitConfigured || canManageMembers) && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">Git</h2>

          {/* Your repository — only when the course actually provisions git, so
              the provision button is never offered on a non-git course. */}
          {gitConfigured && (
          <div>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">Your repository</h3>
            {myRepo ? (
              <dl className="space-y-2 text-sm">
                {repoRow('Mode', myRepo.mode)}
                {myRepo.provider_type && repoRow('Provider', myRepo.provider_type)}
                {myRepo.repo_ref && repoRow('Repository', <span className="font-mono">{myRepo.repo_ref}</span>)}
                {myRepo.web_url &&
                  repoRow(
                    'Web',
                    <a href={myRepo.web_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                      {myRepo.web_url}
                    </a>,
                  )}
                {myRepo.http_url && repoRow('Clone (HTTPS)', <span className="font-mono">{myRepo.http_url}</span>)}
              </dl>
            ) : (
              <p className="text-sm text-gray-600">
                You don&apos;t have a repository for this course yet.
              </p>
            )}

            <button
              onClick={ensureGitAccess}
              disabled={ensuring}
              className="mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {ensuring ? 'Working…' : myRepo ? 'Repair git access' : 'Ensure git access'}
            </button>
            <p className="mt-2 text-xs text-gray-500">
              Creates or repairs your repository for this course
              {canManage ? ' — as staff this also grants access to the template and reference repos.' : '.'}
            </p>
            {provisioned?.clone_token && (
              <div className="mt-3 p-3 rounded border border-amber-200 bg-amber-50 text-sm text-amber-900">
                <p className="font-medium">One-time clone credential — copy it now, it won&apos;t be shown again.</p>
                <p className="mt-1">
                  <span className="text-amber-700">Username:</span>{' '}
                  <span className="font-mono">{provisioned.clone_username}</span>
                </p>
                <p>
                  <span className="text-amber-700">Token:</span>{' '}
                  <span className="font-mono break-all">{provisioned.clone_token}</span>
                </p>
              </div>
            )}
          </div>
          )}

          {/* Course configuration (managers only) */}
          {canManageMembers && (
            <div className="border-t border-gray-100 pt-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-2">Course configuration</h3>
              {gitBinding ? (
                <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                  <div>
                    <dt className="text-gray-500">Delivery</dt>
                    <dd className="mt-1 text-gray-900">{gitBinding.delivery}</dd>
                  </div>
                  {gitBinding.default_branch && (
                    <div>
                      <dt className="text-gray-500">Default branch</dt>
                      <dd className="mt-1 text-gray-900 font-mono">{gitBinding.default_branch}</dd>
                    </div>
                  )}
                  {gitBinding.student_repo_modes && gitBinding.student_repo_modes.length > 0 && (
                    <div>
                      <dt className="text-gray-500">Student repos</dt>
                      <dd className="mt-1 text-gray-900">{gitBinding.student_repo_modes.join(', ')}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="text-gray-500">Status</dt>
                    <dd className="mt-1">
                      {gitBinding.locked ? (
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800"
                          title={gitBinding.lock_reason ?? undefined}
                        >
                          Locked
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                          Editable
                        </span>
                      )}
                    </dd>
                  </div>
                  {(gitBinding.template_url || gitBinding.template_repo) && (
                    <div className="col-span-2 sm:col-span-4">
                      <dt className="text-gray-500">Template</dt>
                      <dd className="mt-1 text-gray-900 break-all">
                        {gitBinding.template_url ? (
                          <a
                            href={gitBinding.template_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {gitBinding.template_url}
                          </a>
                        ) : (
                          gitBinding.template_repo
                        )}
                      </dd>
                    </div>
                  )}
                </dl>
              ) : (
                <p className="text-sm text-gray-500">No git binding configured for this course.</p>
              )}
            </div>
          )}
        </div>
        )}
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
