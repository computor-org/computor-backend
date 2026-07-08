'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';
import { SystemClient } from '@/src/generated/clients/SystemClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { CourseFamilyList, CourseGitBindingUpsert } from '@/src/generated/types/courses';
import type { GitServerGet } from '@/src/generated/types/common';

const coursesClient = new CoursesClient();
const courseFamiliesClient = new CourseFamiliesClient();
const gitServersClient = new GitServersClient();
const systemClient = new SystemClient();

const ALL_MODES = ['managed', 'external', 'download'];
const MODE_LABELS: Record<string, string> = {
  managed: 'Managed — we host it',
  external: 'External — student-hosted (any provider)',
  download: 'Download — no git',
};

// Response of POST /course-families/{id}/deploy-course (validate or apply).
interface DeployWarning { path?: string | null; example_identifier?: string | null; reason: string }
interface DeploySummary { content_types: number; units: number; assignments: number; examples_assigned: number }
interface DeployResult {
  validated: boolean;
  applied: boolean;
  course_id?: string | null;
  course_path: string;
  course_title?: string | null;
  summary: DeploySummary;
  warnings: DeployWarning[];
  errors: string[];
}

function CreateInner() {
  const router = useRouter();
  const familyIdParam = useSearchParam('familyId');
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canConfigureGit, canCreateCourse } = usePermissions();

  const [families, setFamilies] = useState<CourseFamilyList[]>([]);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [familyId, setFamilyId] = useState(familyIdParam);
  const [path, setPath] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [gitEnabled, setGitEnabled] = useState(true);
  const [serverId, setServerId] = useState('');
  const [delivery, setDelivery] = useState<'git' | 'download'>('git');
  const [parentGroupId, setParentGroupId] = useState('');
  const [token, setToken] = useState('');
  const [modes, setModes] = useState<string[]>(['managed']);
  const [deployNow, setDeployNow] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Optional "upload a course_deployment.yaml" flow.
  const [fileName, setFileName] = useState('');
  const [fileText, setFileText] = useState('');
  const [validating, setValidating] = useState(false);
  const [check, setCheck] = useState<DeployResult | null>(null);
  const [createdCourseId, setCreatedCourseId] = useState<string | null>(null);
  const hasFile = !!fileText;

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    (async () => {
      const fams = await courseFamiliesClient.listCourseFamiliesCourseFamiliesGet({});
      const creatable = fams.filter((f) => canCreateCourse(f.organization_id, f.id));
      setFamilies(creatable);
      if (!familyIdParam && creatable.length === 1) setFamilyId(creatable[0].id);
      if (canConfigureGit) {
        const srv = await gitServersClient.listGitServersEndpointGitServersGet({});
        setServers(srv);
        const def = srv.find((s) => s.managed)?.id ?? srv[0]?.id ?? '';
        setServerId(def);
        setGitEnabled(!!def);
      }
    })().catch((e) => {
      setError(e instanceof Error ? e.message : 'Failed to load course families and git servers.');
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated, canConfigureGit]);

  const toggleMode = (m: string) => setModes((ms) => (ms.includes(m) ? ms.filter((x) => x !== m) : [...ms, m]));

  async function onPickFile(file: File | undefined) {
    setCheck(null);
    setCreatedCourseId(null);
    setError(null);
    if (!file) {
      setFileName('');
      setFileText('');
      return;
    }
    try {
      const text = await file.text();
      setFileName(file.name);
      setFileText(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not read the file');
    }
  }

  async function validate() {
    if (!familyId || !fileText) return;
    setValidating(true);
    setError(null);
    setCreatedCourseId(null);
    try {
      const res = (await courseFamiliesClient.deployCourseCourseFamiliesCourseFamilyIdDeployCoursePost({
        courseFamilyId: familyId,
        body: { yaml: fileText, validate_only: true },
      })) as unknown as DeployResult;
      setCheck(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation failed');
    } finally {
      setValidating(false);
    }
  }

  async function configureGit(courseId: string) {
    if (canConfigureGit && gitEnabled && serverId) {
      const selected = servers.find((s) => s.id === serverId);
      const body: CourseGitBindingUpsert = {
        delivery,
        git_server_id: serverId,
        student_repo_modes: modes,
      };
      // External GitLab: the course brings its own parent group + group token
      // (stored encrypted on the binding). Forgejo needs neither.
      if (selected?.type === 'gitlab') {
        if (parentGroupId.trim()) body.parent_group_id = parentGroupId.trim();
        if (token.trim()) body.token = token.trim();
      }
      try {
        await coursesClient.upsertCourseGitBindingEndpointCoursesCourseIdGitPut({ courseId, body });
      } catch (e) {
        throw new Error('Course created, but git setup failed: ' + (e instanceof Error ? e.message : ''));
      }
    }
  }

  // Opt-in: once the course exists (and has a git binding), kick off the
  // student-template deploy for all pending assignments. Best-effort — the course
  // is already created, so a deploy hiccup can be retried from the assignments page.
  async function triggerDeploy(courseId: string) {
    if (!deployNow) return;
    try {
      await systemClient.generateStudentTemplateSystemCoursesCourseIdGenerateStudentTemplatePost({
        courseId,
        body: {},
      });
    } catch {
      /* best-effort; ignore */
    }
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      if (hasFile) {
        const res = (await courseFamiliesClient.deployCourseCourseFamiliesCourseFamilyIdDeployCoursePost({
          courseFamilyId: familyId,
          body: { yaml: fileText, validate_only: false },
        })) as unknown as DeployResult;
        if (!res.course_id) throw new Error(res.errors?.join('; ') || 'Deploy failed');
        // Git comes from the uploaded file's `git:` block (applied server-side by
        // deploy-course). Do NOT also call configureGit here — that would clobber
        // the file's binding with the manual UI selection (and 409 once the file's
        // binding has materialized a template).
        await triggerDeploy(res.course_id);
        if (res.warnings?.length) {
          // The course was created, but something is off (e.g. a service slug
          // didn't resolve, so assignments have no testing service). Surface the
          // warnings instead of silently navigating away; the user can proceed.
          setCheck(res);
          setCreatedCourseId(res.course_id);
          setSaving(false);
          return;
        }
        router.push(`/courses/${res.course_id}`);
        return;
      }
      const course = await coursesClient.createCoursesCoursesPost({
        body: {
          path: path.trim(),
          course_family_id: familyId,
          title: title.trim() || null,
          description: description.trim() || null,
        },
      });
      // One step: configure git immediately so a course is never left without it.
      await configureGit(course.id);
      await triggerDeploy(course.id);
      router.push(`/courses/${course.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canCreateCourse()) {
    return <Forbidden message="You do not have permission to create courses." />;
  }

  const blocked = hasFile && (check?.errors?.length ?? 0) > 0;
  const selectedServer = servers.find((s) => s.id === serverId);

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Courses', href: '/courses' }, { label: 'New' }]}
        title="New Course"
        description="A course is one run of a lecture in a single term — students enroll here, get their repositories, and submit their work. It belongs to a course family (the lecture)."
        error={error}
        submitting={saving}
        disabled={!familyId || !!createdCourseId || (hasFile ? blocked : !path.trim())}
        submitLabel={createdCourseId ? 'Created ✓' : hasFile ? 'Create from file' : 'Create'}
        onCancel={() => router.push('/courses')}
        onSubmit={save}
      >
        <Field label="Course family" required hint="The lecture this course runs. Add it under Course Families first if it's missing.">
          <select value={familyId} onChange={(e) => setFamilyId(e.target.value)} className={inputCls}>
            <option value="">Select a course family…</option>
            {families.map((f) => (
              <option key={f.id} value={f.id}>{f.title || f.path}</option>
            ))}
          </select>
        </Field>

        <Field
          label="Import from file (optional)"
          hint="Upload a course_deployment.yaml to create the course with its content types and full content tree. Identity (path/title) comes from the file."
        >
          <input
            type="file"
            accept=".yaml,.yml,application/x-yaml,text/yaml"
            onChange={(e) => onPickFile(e.target.files?.[0])}
            className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 file:text-sm file:font-medium hover:file:bg-blue-100"
          />
          {hasFile && (
            <div className="mt-2 space-y-2">
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 font-mono truncate">{fileName}</span>
                <button
                  type="button"
                  onClick={validate}
                  disabled={!familyId || validating}
                  className="px-3 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                >
                  {validating ? 'Validating…' : 'Validate'}
                </button>
                <button
                  type="button"
                  onClick={() => onPickFile(undefined)}
                  className="px-3 py-1 text-xs text-gray-500 hover:bg-gray-100 rounded-lg"
                >
                  Clear
                </button>
              </div>

              {check && (
                <div className="text-xs space-y-1 border border-gray-200 rounded-lg p-3 bg-gray-50">
                  <div className="text-gray-700">
                    <span className="font-medium">{check.course_title || check.course_path}</span>{' '}
                    <span className="font-mono text-gray-500">({check.course_path})</span>
                  </div>
                  <div className="text-gray-500">
                    {check.summary.content_types} content types · {check.summary.units} units ·{' '}
                    {check.summary.assignments} assignments · {check.summary.examples_assigned} examples
                  </div>
                  {check.errors.length > 0 && (
                    <ul className="text-red-600 list-disc pl-4">
                      {check.errors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  )}
                  {check.warnings.length > 0 && (
                    <ul className="text-amber-600 list-disc pl-4">
                      {check.warnings.map((w, i) => (
                        <li key={i}>{w.path ? `${w.path}: ` : ''}{w.reason}</li>
                      ))}
                    </ul>
                  )}
                  {check.errors.length === 0 && !createdCourseId && (
                    <div className="text-green-600">Looks good — ready to create.</div>
                  )}
                  {createdCourseId && (
                    <div className="flex items-center gap-2 pt-1 text-green-700">
                      <span>Course created{check.warnings.length > 0 ? ' with warnings (above)' : ''}.</span>
                      <button
                        type="button"
                        onClick={() => router.push(`/courses/${createdCourseId}`)}
                        className="text-blue-600 underline"
                      >
                        Open course
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Field>

        {!hasFile && (
          <>
            <Field label="Path (slug)" required hint="Lowercase, URL-safe identifier, unique within the course family. Hard to change later.">
              <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="algorithms-2026w" className={inputCls} />
            </Field>
            <Field label="Title" hint="Display name for this run, e.g. 'Algorithms — Winter 2026'.">
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Algorithms — Winter 2026" className={inputCls} />
            </Field>
            <Field label="Description">
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
            </Field>
          </>
        )}

        {hasFile && canConfigureGit && (
          <div className="border-t border-gray-200 pt-4">
            <p className="text-xs text-gray-500">
              Git is configured by the uploaded file&apos;s <code className="font-mono">git:</code> block
              (or left unbound if it has none — you can set it later on the course&apos;s edit page).
            </p>
          </div>
        )}

        {!hasFile && canConfigureGit && servers.length > 0 && (
          <div className="border-t border-gray-200 pt-4 space-y-3">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input type="checkbox" checked={gitEnabled} onChange={(e) => setGitEnabled(e.target.checked)} />
              Set up git now
            </label>
            {gitEnabled && (
              <>
                <Field label="Git server">
                  <select value={serverId} onChange={(e) => setServerId(e.target.value)} className={inputCls}>
                    {servers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name || s.base_url} ({s.type})</option>
                    ))}
                  </select>
                </Field>
                <Field label="Delivery" hint="How students get assignments: fork/clone a template repo (git), or download an archive.">
                  <select value={delivery} onChange={(e) => setDelivery(e.target.value as 'git' | 'download')} className={inputCls}>
                    <option value="git">Git (fork/clone template)</option>
                    <option value="download">Download (archive)</option>
                  </select>
                </Field>
                {selectedServer?.type === 'gitlab' && (
                  <>
                    <Field label="GitLab parent group id" hint="The course's own GitLab group is created under this parent group.">
                      <input value={parentGroupId} onChange={(e) => setParentGroupId(e.target.value)} placeholder="12345" className={inputCls} />
                    </Field>
                    <Field label="GitLab group token" hint="A group access token scoped to the parent group — stored encrypted on this course, never shown again.">
                      <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="glpat-…" className={inputCls} />
                    </Field>
                  </>
                )}
                <Field label="Student-repo modes">
                  <div className="flex flex-wrap gap-3">
                    {ALL_MODES.map((m) => (
                      <label key={m} className="flex items-center gap-1.5 text-sm text-gray-700">
                        <input type="checkbox" checked={modes.includes(m)} onChange={() => toggleMode(m)} />
                        {MODE_LABELS[m] ?? m}
                      </label>
                    ))}
                  </div>
                </Field>
                <p className="text-xs text-gray-400">For a managed server (Forgejo or GitLab) the course template repo is created automatically.</p>
              </>
            )}
          </div>
        )}

        {canConfigureGit && (
          <label className="flex items-center gap-2 border-t border-gray-200 pt-4 text-sm text-gray-700">
            <input type="checkbox" checked={deployNow} onChange={(e) => setDeployNow(e.target.checked)} />
            Deploy assignments now — push them into the template repo once the course is created
          </label>
        )}
      </FormPanel>
    </AuthenticatedLayout>
  );
}

export default function CourseCreatePage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><div className="p-6 text-gray-500">Loading…</div></AuthenticatedLayout>}>
      <CreateInner />
    </Suspense>
  );
}
