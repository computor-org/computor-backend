'use client';

import { useState, type ReactNode } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/src/utils/api';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import type {
  CourseGet,
  CourseFamilyGet,
  CourseGitBindingGet,
  CourseMemberRepositoryGet,
  OrganizationGet,
  StudentRepositoryProvisioned,
} from 'types/generated';

interface ViewCard {
  view: string;
  href: string;
  title: string;
  desc: string;
  icon: ReactNode;
}

export default function CoursePage() {
  const courseId = useParams().id as string;
  const { canManageHierarchy: canManage, isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();
  const canManageMembers = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const { data, loading, error, reload } = useResource(
    async () => {
      const course = await api.get<CourseGet>(`/courses/${courseId}`);
      const [courseViews, organization, courseFamily, gitBinding, myRepo] = await Promise.all([
        api.get<string[]>(`/user/views/${courseId}`).catch(() => [] as string[]),
        api.get<OrganizationGet>(`/organizations/${course.organization_id}`).catch(() => null),
        api.get<CourseFamilyGet>(`/course-families/${course.course_family_id}`).catch(() => null),
        // Git binding is lecturer-cohort only; fetch it only for managers.
        canManageMembers
          ? api.get<CourseGitBindingGet>(`/courses/${courseId}/git`).catch(() => null)
          : Promise.resolve(null),
        // The caller's own repository. 404s (→ null) when they aren't a member.
        api.get<CourseMemberRepositoryGet>(`/user/courses/${courseId}/repository`).catch(() => null),
      ]);
      return { course, courseViews, organization, courseFamily, gitBinding, myRepo };
    },
    [courseId, canManageMembers],
  );
  const course = data?.course ?? null;
  const courseViews = data?.courseViews ?? [];
  const organization = data?.organization ?? null;
  const courseFamily = data?.courseFamily ?? null;
  const gitBinding = data?.gitBinding ?? null;
  const myRepo = data?.myRepo ?? null;

  const [ensuring, setEnsuring] = useState(false);
  const [ensureMsg, setEnsureMsg] = useState<string | null>(null);
  const [ensureErr, setEnsureErr] = useState(false);
  const [provisioned, setProvisioned] = useState<StudentRepositoryProvisioned | null>(null);

  async function ensureGitAccess() {
    setEnsuring(true);
    setEnsureMsg(null);
    setEnsureErr(false);
    setProvisioned(null);
    try {
      const r = await api.post<StudentRepositoryProvisioned>(
        `/user/courses/${courseId}/provision-repository`,
        {},
      );
      setProvisioned(r);
      setEnsureMsg('Git access ensured.');
      await reload(); // refresh the persisted repository details below
    } catch (e) {
      setEnsureErr(true);
      setEnsureMsg(e instanceof Error ? e.message : 'Failed to ensure git access');
    } finally {
      setEnsuring(false);
    }
  }

  if (loading) {
    return (
      <AuthenticatedLayout>
        <div className="p-6 space-y-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  if (error || !course) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-800">{error || 'Course not found'}</p>
            </div>
          </div>
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
      desc: 'Management & analytics',
      icon: (
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      ),
    },
  ].filter((c) => courseViews.includes(c.view));

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
      <div className="p-6 space-y-8">
        <Breadcrumbs items={crumbs} />

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-bold text-gray-900">{course.title || 'Untitled Course'}</h1>
            <p className="mt-2 flex items-center gap-3 text-gray-600">
              <span className="font-mono text-sm truncate">{course.path}</span>
              {course.language_code && (
                <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 rounded uppercase">
                  {course.language_code}
                </span>
              )}
            </p>
          </div>
          {canManage && (
            <Link
              href={`/courses/${courseId}/edit`}
              className="shrink-0 px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Edit
            </Link>
          )}
        </div>

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
            {course.team_mode && (
              <div>
                <dt className="text-gray-500">Team mode</dt>
                <dd className="mt-1 text-gray-900">{course.team_mode}</dd>
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

        {/* Git — the caller's own repository (+ ensure access), then the course
            binding for managers. */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">Git</h2>

          {/* Your repository (everyone) */}
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
                {myRepo.ssh_url && repoRow('Clone (SSH)', <span className="font-mono">{myRepo.ssh_url}</span>)}
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
            {ensureMsg && (
              <p className={`mt-3 text-sm break-all ${ensureErr ? 'text-red-600' : 'text-green-700'}`}>{ensureMsg}</p>
            )}
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

        {/* Members — managers only; hidden entirely from everyone else. */}
        {canManageMembers && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-1">Members</h2>
              <p className="text-sm text-gray-600">
                View the roster, change member roles, and add users to the course.
              </p>
            </div>
            <Link
              href={`/courses/${courseId}/members`}
              className="shrink-0 self-start px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Manage members
            </Link>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
