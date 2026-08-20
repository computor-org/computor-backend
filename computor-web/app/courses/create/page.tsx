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
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import ConfirmDeployWarningsDialog from '@/src/components/courses/ConfirmDeployWarningsDialog';
import DeploymentCheckReport, { type DeployCheckStatus } from '@/src/components/courses/DeploymentCheckReport';
import { fileInputCls, inputCls } from '@/src/components/ui/tokens';
import type { CourseFamilyList, CourseGitBindingUpsert } from '@/src/generated/types/courses';
import type { CourseDeployResult, GitServerGet } from '@/src/generated/types/common';
import { displayName } from '@/src/utils/displayName';

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

/**
 * Outcome of POST /course-families/{id}/deploy-course, tagged with the exact
 * (family, file) it belongs to. The tag is what makes the automatic check
 * race-free: a result is only ever shown next to the input that produced it, so
 * a slow response for an old file cannot describe the current one.
 */
interface Check {
  key: string;
  result: CourseDeployResult | null;
  failure: string | null;
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
  const [check, setCheck] = useState<Check | null>(null);
  const [recheck, setRecheck] = useState(0);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [createdCourseId, setCreatedCourseId] = useState<string | null>(null);
  const hasFile = !!fileText;

  // The file only means something relative to the family it is deployed into
  // (the path-taken and content-type checks are family-scoped), so both go into
  // the key: change either and the previous verdict stops applying. `recheck`
  // lets the user retry after a transport failure.
  const checkKey = hasFile && familyId ? `${recheck}:${familyId}:${fileText}` : '';
  // Once the course exists the report describes what actually happened, so it
  // stops tracking the form instead of falling back to "checking…".
  const current = check && (!!createdCourseId || check.key === checkKey) ? check : null;
  const status: DeployCheckStatus = createdCourseId
    ? 'done'
    : !familyId
      ? 'waiting'
      : !current
        ? 'checking'
        : current.failure
          ? 'failed'
          : 'done';
  const errors = current?.result?.errors ?? [];
  const warnings = current?.result?.warnings ?? [];

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

  // Check the file automatically, as soon as there is something to check. The
  // user never has to ask what the upload will do — and, because a file that
  // has not passed the check cannot be submitted, never creates a course from a
  // file nobody looked at. `validate_only` touches no data server-side.
  useEffect(() => {
    if (!checkKey || createdCourseId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = (await courseFamiliesClient.deployCourseCourseFamiliesCourseFamilyIdDeployCoursePost({
          courseFamilyId: familyId,
          body: { yaml: fileText, validate_only: true },
        })) as unknown as CourseDeployResult;
        if (!cancelled) setCheck({ key: checkKey, result: res, failure: null });
      } catch (e) {
        if (!cancelled) {
          setCheck({
            key: checkKey,
            result: null,
            failure: e instanceof Error ? e.message : 'The file could not be checked.',
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // fileText is part of checkKey; re-running on its identity alone would
    // repeat the request for an unchanged file.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checkKey]);

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

  /** Submit — but never past unacknowledged warnings. */
  function onSubmit() {
    if (hasFile && warnings.length > 0 && !createdCourseId) {
      setConfirmOpen(true);
      return;
    }
    void save();
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      if (hasFile) {
        const res = (await courseFamiliesClient.deployCourseCourseFamiliesCourseFamilyIdDeployCoursePost({
          courseFamilyId: familyId,
          body: { yaml: fileText, validate_only: false },
        })) as unknown as CourseDeployResult;
        if (!res.course_id) throw new Error(res.errors?.join('; ') || 'Deploy failed');
        // Git comes from the uploaded file's `git:` block (applied server-side by
        // deploy-course). Do NOT also call configureGit here — that would clobber
        // the file's binding with the manual UI selection (and 409 once the file's
        // binding has materialized a template).
        await triggerDeploy(res.course_id);
        if (res.warnings?.length) {
          // The course was created, but something is off (e.g. a service slug
          // didn't resolve, so assignments have no testing service). Replace the
          // pre-flight verdict with what actually happened instead of silently
          // navigating away.
          setCheck({ key: checkKey, result: res, failure: null });
          setCreatedCourseId(res.course_id);
          setConfirmOpen(false);
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
      setConfirmOpen(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canCreateCourse()) {
    return <Forbidden message="You do not have permission to create courses." />;
  }

  // A file is only submittable once its automatic check came back clean of
  // blocking errors — an unchecked or failed file would fail the apply anyway.
  const blocked = hasFile && (status !== 'done' || errors.length > 0);
  const selectedServer = servers.find((s) => s.id === serverId);

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Courses', href: '/courses' }, { label: 'New' }]}
        title="New course"
        description="A course is one run of a lecture in a single term — students enroll here, get their repositories, and submit their work. It belongs to a course family (the lecture)."
        error={error}
        submitting={saving}
        disabled={!familyId || !!createdCourseId || (hasFile ? blocked : !path.trim())}
        submitLabel={createdCourseId ? 'Created ✓' : hasFile ? 'Create from file' : 'Create'}
        onCancel={() => router.push('/courses')}
        onSubmit={onSubmit}
      >
        <Field label="Course family" required hint="The lecture this course runs. Add it under Course Families first if it's missing.">
          <select value={familyId} onChange={(e) => setFamilyId(e.target.value)} className={inputCls}>
            <option value="">Select a course family…</option>
            {families.map((f) => (
              <option key={f.id} value={f.id}>{displayName(f, 'Untitled Course Family')}</option>
            ))}
          </select>
        </Field>

        <Field
          label="Import from file (optional)"
          hint="Upload a course_deployment.yaml to create the course with its content types and full content tree. Identity (path/title) comes from the file, and it is checked automatically."
        >
          <input
            type="file"
            accept=".yaml,.yml,application/x-yaml,text/yaml"
            onChange={(e) => onPickFile(e.target.files?.[0])}
            className={fileInputCls}
          />
          {hasFile && (
            <DeploymentCheckReport
              status={status}
              result={current?.result ?? null}
              failure={current?.failure}
              createdCourseId={createdCourseId}
              onClear={() => onPickFile(undefined)}
              onRecheck={() => setRecheck((n) => n + 1)}
              onOpenCourse={() => router.push(`/courses/${createdCourseId}`)}
            />
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
          <div className="border-t border-rule pt-4">
            <p className="text-xs text-muted">
              Git is configured by the uploaded file&apos;s <code className="font-mono">git:</code> block
              (or left unbound if it has none — you can set it later on the course&apos;s edit page).
            </p>
          </div>
        )}

        {!hasFile && canConfigureGit && servers.length > 0 && (
          <div className="border-t border-rule pt-4 space-y-3">
            <label className="flex items-center gap-2 text-sm font-medium text-body">
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
                      <label key={m} className="flex items-center gap-1.5 text-sm text-body">
                        <input type="checkbox" checked={modes.includes(m)} onChange={() => toggleMode(m)} />
                        {MODE_LABELS[m] ?? m}
                      </label>
                    ))}
                  </div>
                </Field>
                <p className="text-xs text-subtle">For a managed server (Forgejo or GitLab) the course template repo is created automatically.</p>
              </>
            )}
          </div>
        )}

        {canConfigureGit && (
          <label className="flex items-center gap-2 border-t border-rule pt-4 text-sm text-body">
            <input type="checkbox" checked={deployNow} onChange={(e) => setDeployNow(e.target.checked)} />
            Deploy assignments now — push them into the template repo once the course is created
          </label>
        )}
      </FormPanel>

      {confirmOpen && (
        <ConfirmDeployWarningsDialog
          warnings={warnings}
          courseLabel={current?.result?.course_title || current?.result?.course_path || fileName}
          submitting={saving}
          onConfirm={() => void save()}
          onCancel={() => setConfirmOpen(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}

export default function CourseCreatePage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><PageLoading /></AuthenticatedLayout>}>
      <CreateInner />
    </Suspense>
  );
}
