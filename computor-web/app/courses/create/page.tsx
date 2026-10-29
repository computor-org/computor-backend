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
import TutorAgentAutoRouteField from '@/src/components/courses/TutorAgentAutoRouteField';
import DeploymentCheckReport, { type DeployCheckStatus } from '@/src/components/courses/DeploymentCheckReport';
import { fileInputCls, inputCls } from '@/src/components/ui/tokens';
import type { CourseFamilyList, CourseGitBindingUpsert } from '@/src/generated/types/courses';
import type { CourseDeployResult, GitServerGet } from '@/src/generated/types/common';
import { displayName } from '@/src/utils/displayName';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { COURSE_FORM_COPY, STUDENT_REPO_MODES } from '@/src/components/courses/courseFormCopy';

const coursesClient = new CoursesClient();
const courseFamiliesClient = new CourseFamiliesClient();
const gitServersClient = new GitServersClient();
const systemClient = new SystemClient();

const COPY = {
  de: {
    loadFailed: 'Kursfamilien und Git-Server konnten nicht geladen werden.',
    checkFailed: 'Die Datei konnte nicht geprüft werden.',
    readFailed: 'Die Datei konnte nicht gelesen werden.',
    gitFailed: 'Der Kurs wurde angelegt, aber die Git-Einrichtung ist fehlgeschlagen: ',
    deployFailed: 'Bereitstellung fehlgeschlagen',
    createFailed: 'Anlegen fehlgeschlagen',
    forbidden: 'Du darfst keine Kurse anlegen.',
    courses: 'Kurse',
    newCrumb: 'Neu',
    pageTitle: 'Neuer Kurs',
    pageDescription: 'Ein Kurs ist ein Durchgang einer Lehrveranstaltung in einem Semester: Hier schreiben sich Studierende ein, erhalten ihre Repositories und geben ihre Arbeiten ab. Er gehört zu einer Kursfamilie, der Lehrveranstaltung.',
    created: 'Angelegt ✓',
    createFromFile: 'Aus Datei anlegen',
    create: 'Anlegen',
    family: 'Kursfamilie',
    familyHint: 'Die Lehrveranstaltung, zu der dieser Kurs gehört. Fehlt sie, lege sie zuerst unter „Kursfamilien“ an.',
    selectFamily: 'Kursfamilie wählen …',
    untitledFamily: 'Kursfamilie ohne Titel',
    importFile: 'Aus Datei importieren (optional)',
    importHint: 'Lade eine course_deployment.yaml hoch, um den Kurs mit seinen Inhaltstypen und dem vollständigen Inhaltsbaum anzulegen. Pfad und Titel stammen aus der Datei, die automatisch geprüft wird.',
    path: 'Pfad (Kurzname)',
    pathHint: 'Kleingeschriebene, URL-taugliche Kennung, eindeutig innerhalb der Kursfamilie. Später nur schwer zu ändern.',
    titleHint: 'Anzeigename dieses Durchgangs, z. B. „Algorithmen – Wintersemester 2026“.',
    titlePlaceholder: 'Algorithmen – Wintersemester 2026',
    gitFromFile: <>Git wird über den <code className="font-mono">git:</code>-Block der hochgeladenen Datei eingerichtet. Fehlt er, bleibt der Kurs ohne Git; du kannst es später auf der Bearbeitungsseite des Kurses einrichten.</>,
    setUpGit: 'Git jetzt einrichten',
    deliveryHint: 'Wie Studierende die Aufgaben erhalten: als Fork oder Klon eines Vorlagen-Repositorys (Git) oder als Archiv zum Herunterladen.',
    deliveryGit: 'Git (Vorlage forken oder klonen)',
    deliveryDownload: 'Download (Archiv)',
    deployNow: 'Aufgaben jetzt bereitstellen: Sie werden nach dem Anlegen des Kurses in das Vorlagen-Repository übertragen.',
  },
  en: {
    loadFailed: 'Failed to load course families and git servers.',
    checkFailed: 'The file could not be checked.',
    readFailed: 'Could not read the file',
    gitFailed: 'Course created, but git setup failed: ',
    deployFailed: 'Deploy failed',
    createFailed: 'Create failed',
    forbidden: 'You do not have permission to create courses.',
    courses: 'Courses',
    newCrumb: 'New',
    pageTitle: 'New course',
    pageDescription: 'A course is one run of a lecture in a single term — students enroll here, get their repositories, and submit their work. It belongs to a course family (the lecture).',
    created: 'Created ✓',
    createFromFile: 'Create from file',
    create: 'Create',
    family: 'Course family',
    familyHint: 'The lecture this course runs. Add it under Course Families first if it\'s missing.',
    selectFamily: 'Select a course family…',
    untitledFamily: 'Untitled Course Family',
    importFile: 'Import from file (optional)',
    importHint: 'Upload a course_deployment.yaml to create the course with its content types and full content tree. Identity (path/title) comes from the file, and it is checked automatically.',
    path: 'Path (slug)',
    pathHint: 'Lowercase, URL-safe identifier, unique within the course family. Hard to change later.',
    titleHint: 'Display name for this run, e.g. \'Algorithms — Winter 2026\'.',
    titlePlaceholder: 'Algorithms — Winter 2026',
    gitFromFile: <>Git is configured by the uploaded file&apos;s <code className="font-mono">git:</code> block (or left unbound if it has none — you can set it later on the course&apos;s edit page).</>,
    setUpGit: 'Set up git now',
    deliveryHint: 'How students get assignments: fork/clone a template repo (git), or download an archive.',
    deliveryGit: 'Git (fork/clone template)',
    deliveryDownload: 'Download (archive)',
    deployNow: 'Deploy assignments now — push them into the template repo once the course is created',
  },
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
  const { isAuthenticated, isLoading: authLoading, refreshPermissions } = useAuth();
  const { canManageHierarchy: canConfigureGit, canCreateCourse } = usePermissions();
  const language = useUiLanguage();
  const t = COPY[language];
  const f = COURSE_FORM_COPY[language];

  const [families, setFamilies] = useState<CourseFamilyList[]>([]);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [familyId, setFamilyId] = useState(familyIdParam);
  const [path, setPath] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [autoRoute, setAutoRoute] = useState(false);
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
      setError(e instanceof Error ? e.message : t.loadFailed);
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
            failure: e instanceof Error ? e.message : t.checkFailed,
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
      setError(e instanceof Error ? e.message : t.readFailed);
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
        throw new Error(t.gitFailed + (e instanceof Error ? e.message : ''));
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
        if (!res.course_id) throw new Error(res.errors?.join('; ') || t.deployFailed);
        // The deployment file has no field for this course setting; apply the
        // form's choice to the course the file just created.
        if (autoRoute) {
          await coursesClient.updateCoursesCoursesIdPatch({
            id: res.course_id,
            body: { tutor_agent_auto_route: true },
          });
        }
        // Git comes from the uploaded file's `git:` block (applied server-side by
        // deploy-course). Do NOT also call configureGit here — that would clobber
        // the file's binding with the manual UI selection (and 409 once the file's
        // binding has materialized a template).
        await triggerDeploy(res.course_id);
        // The deploy enrolled us as the course's `_owner` (issue #386); re-pull
        // /user/scopes so the course page gates on the role we now hold. Before
        // the warnings branch — that one leaves the created course on screen.
        await refreshPermissions();
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
          tutor_agent_auto_route: autoRoute,
        },
      });
      // One step: configure git immediately so a course is never left without it.
      await configureGit(course.id);
      await triggerDeploy(course.id);
      // Creating a course enrols the creator as its `_owner` (issue #386). The
      // server has already dropped the stale caches; re-pull /user/scopes so the
      // course page we are about to open gates on the role we now hold.
      await refreshPermissions();
      router.push(`/courses/${course.id}`);
    } catch (e) {
      setSaving(false);
      setConfirmOpen(false);
      setError(e instanceof Error ? e.message : t.createFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canCreateCourse()) {
    return <Forbidden message={t.forbidden} />;
  }

  // A file is only submittable once its automatic check came back clean of
  // blocking errors — an unchecked or failed file would fail the apply anyway.
  const blocked = hasFile && (status !== 'done' || errors.length > 0);
  const selectedServer = servers.find((s) => s.id === serverId);

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: t.courses, href: '/courses' }, { label: t.newCrumb }]}
        title={t.pageTitle}
        description={t.pageDescription}
        error={error}
        submitting={saving}
        disabled={!familyId || !!createdCourseId || (hasFile ? blocked : !path.trim())}
        submitLabel={createdCourseId ? t.created : hasFile ? t.createFromFile : t.create}
        onCancel={() => router.push('/courses')}
        onSubmit={onSubmit}
      >
        <Field label={t.family} required hint={t.familyHint}>
          <select value={familyId} onChange={(e) => setFamilyId(e.target.value)} className={inputCls}>
            <option value="">{t.selectFamily}</option>
            {families.map((family) => (
              <option key={family.id} value={family.id}>{displayName(family, t.untitledFamily)}</option>
            ))}
          </select>
        </Field>

        <Field
          label={t.importFile}
          hint={t.importHint}
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
            <Field label={t.path} required hint={t.pathHint}>
              <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="algorithms-2026w" className={inputCls} />
            </Field>
            <Field label={f.title} hint={t.titleHint}>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t.titlePlaceholder} className={inputCls} />
            </Field>
            <Field label={f.description}>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
            </Field>
          </>
        )}

        <Field label={f.aiTutor}>
          <TutorAgentAutoRouteField value={autoRoute} onChange={setAutoRoute} />
        </Field>

        {hasFile && canConfigureGit && (
          <div className="border-t border-rule pt-4">
            <p className="text-xs text-muted">
              {t.gitFromFile}
            </p>
          </div>
        )}

        {!hasFile && canConfigureGit && servers.length > 0 && (
          <div className="border-t border-rule pt-4 space-y-3">
            <label className="flex items-center gap-2 text-sm font-medium text-body">
              <input type="checkbox" checked={gitEnabled} onChange={(e) => setGitEnabled(e.target.checked)} />
              {t.setUpGit}
            </label>
            {gitEnabled && (
              <>
                <Field label={f.gitServer}>
                  <select value={serverId} onChange={(e) => setServerId(e.target.value)} className={inputCls}>
                    {servers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name || s.base_url} ({s.type})</option>
                    ))}
                  </select>
                </Field>
                <Field label={f.delivery} hint={t.deliveryHint}>
                  <select value={delivery} onChange={(e) => setDelivery(e.target.value as 'git' | 'download')} className={inputCls}>
                    <option value="git">{t.deliveryGit}</option>
                    <option value="download">{t.deliveryDownload}</option>
                  </select>
                </Field>
                {selectedServer?.type === 'gitlab' && (
                  <>
                    <Field label={f.parentGroup} hint={f.parentGroupHint}>
                      <input value={parentGroupId} onChange={(e) => setParentGroupId(e.target.value)} placeholder="12345" className={inputCls} />
                    </Field>
                    <Field label={f.groupToken} hint={f.groupTokenHint}>
                      <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="glpat-…" className={inputCls} />
                    </Field>
                  </>
                )}
                <Field label={f.repoModes}>
                  <div className="flex flex-wrap gap-3">
                    {STUDENT_REPO_MODES.map((m) => (
                      <label key={m} className="flex items-center gap-1.5 text-sm text-body">
                        <input type="checkbox" checked={modes.includes(m)} onChange={() => toggleMode(m)} />
                        {f.modes[m] ?? m}
                      </label>
                    ))}
                  </div>
                </Field>
                <p className="text-xs text-subtle">{f.managedTemplate}</p>
              </>
            )}
          </div>
        )}

        {canConfigureGit && (
          <label className="flex items-center gap-2 border-t border-rule pt-4 text-sm text-body">
            <input type="checkbox" checked={deployNow} onChange={(e) => setDeployNow(e.target.checked)} />
            {t.deployNow}
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
