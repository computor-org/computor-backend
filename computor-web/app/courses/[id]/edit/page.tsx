'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { GitServersClient } from '@/src/generated/clients/GitServersClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import { Field } from '@/src/components/FormPanel';
import { inputCls, readOnlyInputCls } from '@/src/components/ui/tokens';
import SectionCard, { SectionHint, SectionStatus } from '@/src/components/SectionCard';
import PublicCourseField from '@/src/components/courses/PublicCourseField';
import TutorAgentAutoRouteField from '@/src/components/courses/TutorAgentAutoRouteField';
import DescriptionList from '@/src/components/DescriptionList';
import Button from '@/src/components/ui/Button';
import Badge from '@/src/components/Badge';
import VisibilitySelect, { type VisibilityValue } from '@/src/components/courses/VisibilitySelect';
import type { CourseGet, CourseGitBindingGet, CourseGitBindingUpsert, GitServerGet } from 'types/generated';
import { COURSE_FORM_COPY, STUDENT_REPO_MODES } from '@/src/components/courses/courseFormCopy';

const coursesClient = new CoursesClient();
const gitServersClient = new GitServersClient();

/** Blank (or unparseable) means "no course-wide default", i.e. unlimited. */
const parseLimit = (value: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
};

const COPY = {
  de: {
    edit: 'Bearbeiten',
    loadFailed: 'Ein Fehler ist aufgetreten',
    positionError: 'Gib eine endliche Zahl ein oder lass das Feld leer.',
    seatsError: 'Gib eine ganze Zahl ab 0 ein oder lass das Feld leer für unbegrenzt.',
    saved: 'Gespeichert.',
    saveFailed: 'Speichern fehlgeschlagen',
    forbidden: 'Du hast keinen Zugriff auf die Einstellungen dieses Kurses.',
    backToCourse: 'Zurück zum Kurs',
    pageTitle: 'Kurs bearbeiten',
    general: 'Allgemein',
    git: 'Git-Anbindung',
    courseOrder: 'Kursreihenfolge',
    courseOrderHint: 'Kleinere Zahlen stehen zuerst. Ohne Zahl folgt der Kurs nach den geordneten Kursen, alphabetisch nach Titel.',
    languageCode: 'Sprachcode',
    path: 'Pfad (unveränderlich)',
    maxTestRuns: 'Standardlimit für Testläufe',
    maxSubmissions: 'Standardlimit für Abgaben',
    limitHint: 'Gilt für Aufgaben, die kein eigenes Limit setzen. Leer bedeutet unbegrenzt.',
    unlimited: 'unbegrenzt',
    visibility: 'Sichtbarkeit für Studierende',
    visibilityHint: 'Wenn du den Kurs verbirgst, verbirgst du alle Einheiten und Aufgaben darin. Einheiten und Aufgaben lassen sich auch einzeln verbergen.',
    selfRegistration: 'Selbstanmeldung',
    selfRegistrationHint: 'Unabhängig von der Sichtbarkeit oben: Diese verbirgt Kursinhalte vor Mitgliedern, die Selbstanmeldung entscheidet, wer Mitglied werden darf.',
    selfRegistrationLocked: 'Nur Kursverantwortliche (Maintainer oder Owner) können das ändern, denn ein gelisteter Kurs wird allen Konten dieser Instanz angeboten.',
    seats: 'Plätze für die Selbstanmeldung',
    seatsHint: 'Höchstzahl der Studierenden; mitgezählt werden alle, die als Studierende eingeschrieben sind, egal wie sie beigetreten sind. Leer bedeutet unbegrenzt.',
    nothingSaved: 'Es wurde nichts gespeichert.',
    saving: 'Wird gespeichert …',
    save: 'Speichern',
    locked: 'Gesperrt',
    lockedDefault: 'Die Git-Konfiguration dieses Kurses ist gesperrt.',
    lockedNote: 'Ein anderer Server oder eine andere Vorlage würde die bestehenden Repositories der Studierenden verwaisen lassen, daher sind diese Einstellungen schreibgeschützt.',
    deliveryTerm: 'Bereitstellung',
    template: 'Vorlage',
    noGit: 'Dieser Kurs hat noch keine Git-Konfiguration. Richte sie ein, um Repositories für Studierende zu ermöglichen.',
    serversCentral: 'Die Liste der Git-Server wird zentral verwaltet und ist hier deshalb leer. Bitte eine Administratorin oder einen Administrator, den Server für diesen Kurs auszuwählen.',
    deliveryGit: 'Git (Fork/Klon)',
    deliveryDownload: 'Download',
    templateServer: 'Git-Server (für die Vorlage)',
    templateServerHint: 'Bei einem verwalteten Server (Forgejo oder GitLab) lässt du die Vorlagenfelder leer; das Vorlagen-Repository wird automatisch angelegt.',
    none: '— keiner —',
    tokenStored: 'Es ist bereits ein Token gespeichert. Gib ein neues ein, um es zu ersetzen.',
    tokenStoredPlaceholder: '•••••••• (gespeichert)',
    templateRepo: 'Vorlagen-Repository',
    defaultBranch: 'Standard-Branch',
    templateUrl: 'Klon-URL der Vorlage',
    templateUrlPlaceholder: 'automatisch bei verwalteten Servern',
    saveGit: 'Git-Einstellungen speichern',
    configureGit: 'Git einrichten',
  },
  en: {
    edit: 'Edit',
    loadFailed: 'An error occurred',
    positionError: 'Enter a finite number or leave the field empty.',
    seatsError: 'Enter a whole number of 0 or more, or leave it empty for unlimited.',
    saved: 'Saved.',
    saveFailed: 'Save failed',
    forbidden: 'You do not have access to this course\'s settings.',
    backToCourse: 'Back to course',
    pageTitle: 'Edit course',
    general: 'General',
    git: 'Git',
    courseOrder: 'Course order',
    courseOrderHint: 'Lower numbers come first. Leave empty to list the course after ordered courses, alphabetically by title.',
    languageCode: 'Language code',
    path: 'Path (immutable)',
    maxTestRuns: 'Default max test runs',
    maxSubmissions: 'Default max submissions',
    limitHint: 'Applies to assignments that set no limit of their own. Empty = unlimited.',
    unlimited: 'unlimited',
    visibility: 'Student visibility',
    visibilityHint: 'Hiding the course hides every unit and assignment in it. Units and assignments can also be hidden individually.',
    selfRegistration: 'Self-registration',
    selfRegistrationHint: 'Independent of student visibility above: that hides course content from members, this decides who may become one.',
    selfRegistrationLocked: 'Only a course maintainer or owner can change this — listing a course advertises it to every account on this deployment.',
    seats: 'Self-registration seats',
    seatsHint: 'Maximum number of students; counts everyone enrolled as a student, however they joined. Empty = unlimited.',
    nothingSaved: 'Nothing was saved.',
    saving: 'Saving…',
    save: 'Save',
    locked: 'Locked',
    lockedDefault: 'This course’s git configuration is locked.',
    lockedNote: 'Changing the server or template would orphan students’ existing repositories, so these settings are read-only.',
    deliveryTerm: 'Delivery',
    template: 'Template',
    noGit: 'This course has no git configuration yet. Configure it to enable student repositories.',
    serversCentral: 'The list of git servers is managed centrally, so it is empty here. Ask an administrator to pick the server for this course.',
    deliveryGit: 'git (fork/clone)',
    deliveryDownload: 'download',
    templateServer: 'Git server (for the template)',
    templateServerHint: 'For a managed server (Forgejo or GitLab), leave the template fields blank — the template repo is created automatically.',
    none: '— none —',
    tokenStored: 'A token is already stored — enter a new one to replace it.',
    tokenStoredPlaceholder: '•••••••• (stored)',
    templateRepo: 'Template repo',
    defaultBranch: 'Default branch',
    templateUrl: 'Template clone URL',
    templateUrlPlaceholder: 'auto for managed servers',
    saveGit: 'Save git settings',
    configureGit: 'Configure git',
  },
};

export default function CourseEditPage() {
  const courseId = useParams().id as string;
  const uiLanguage = useUiLanguage();
  const t = COPY[uiLanguage];
  const f = COURSE_FORM_COPY[uiLanguage];
  const crumbs = useCourseCrumbs(courseId, t.edit);
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage, courseHasAtLeast } = usePermissions();
  // Course staff reach this page too, not only the org hierarchy: the backend
  // behind it is the _lecturer cohort (Course.update, and api/course_git.py's
  // "lecturer cohort only"), so gating the page on admin/_organization_manager
  // locked lecturers out of their own course's settings.
  const canEdit = canManage || courseHasAtLeast(courseId, '_lecturer');
  // Opening a course for self-registration is held one rung higher — it
  // advertises the course to every account on the deployment. Mirrors the
  // backend guard in interfaces/course.py.
  const canSetPublic = canManage || courseHasAtLeast(courseId, '_maintainer');

  const [course, setCourse] = useState<CourseGet | null>(null);
  const [binding, setBinding] = useState<CourseGitBindingGet | null>(null);
  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // General form
  const [position, setPosition] = useState('');
  const [positionError, setPositionError] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [autoRoute, setAutoRoute] = useState(false);
  // Self-registration seat cap; empty = unlimited, same convention as budgets.
  const [maxSelfRegistrations, setMaxSelfRegistrations] = useState('');
  const [seatsError, setSeatsError] = useState<string | null>(null);
  // Course-wide budget defaults. Held as strings so an empty field can mean
  // "unlimited" rather than collapsing to 0.
  const [maxTestRuns, setMaxTestRuns] = useState('');
  const [maxSubmissions, setMaxSubmissions] = useState('');
  // Tri-state: null inherits (= visible), false hides the whole content tree.
  const [visible, setVisible] = useState<VisibilityValue>(null);
  const [savingGeneral, setSavingGeneral] = useState(false);
  const [generalMsg, setGeneralMsg] = useState<string | null>(null);

  // Git binding form
  const [delivery, setDelivery] = useState<'git' | 'download'>('git');
  const [gitServerId, setGitServerId] = useState('');
  const [templateRepo, setTemplateRepo] = useState('');
  const [templateUrl, setTemplateUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [modes, setModes] = useState<string[]>([]);
  const [parentGroupId, setParentGroupId] = useState('');
  const [token, setToken] = useState('');
  const [hasToken, setHasToken] = useState(false);
  const [savingGit, setSavingGit] = useState(false);
  const [gitMsg, setGitMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const c = await coursesClient.getCoursesCoursesIdGet({ id: courseId });
      setCourse(c);
      setTitle(c.title || '');
      setPosition(c.position != null ? String(c.position) : '');
      setDescription(c.description || '');
      setLanguage(c.language_code || '');
      setIsPublic(c.public ?? false);
      setAutoRoute(c.tutor_agent_auto_route ?? false);
      setMaxSelfRegistrations(
        c.max_self_registrations != null ? String(c.max_self_registrations) : '',
      );
      setMaxTestRuns(c.max_test_runs != null ? String(c.max_test_runs) : '');
      setMaxSubmissions(c.max_submissions != null ? String(c.max_submissions) : '');
      setVisible(c.visible ?? null);
      const srv = await gitServersClient.listGitServersEndpointGitServersGet({}).catch(() => [] as GitServerGet[]);
      setServers(srv);
      // The binding endpoint 404s when a course has none yet — treat as null.
      const b = await coursesClient.getCourseGitBindingEndpointCoursesCourseIdGitGet({ courseId }).catch(() => null);
      setBinding(b);
      if (b && b.delivery) {
        setDelivery(b.delivery === 'download' ? 'download' : 'git');
        setGitServerId(b.git_server_id || '');
        setTemplateRepo(b.template_repo || '');
        setTemplateUrl(b.template_url || '');
        setBranch(b.default_branch || 'main');
        setModes(b.student_repo_modes || []);
        setParentGroupId(b.parent_group_id || '');
        setHasToken(!!b.has_token);
        setToken('');
      } else {
        // No binding yet — default to a managed server + the managed mode.
        setGitServerId(srv.find((s) => s.managed)?.id ?? srv[0]?.id ?? '');
        setModes(['managed']);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canEdit) return;
    load();
  }, [authLoading, isAuthenticated, canEdit, load]);

  async function saveGeneral() {
    const orderText = position.trim();
    const order = orderText ? Number(orderText) : null;
    if (order !== null && !Number.isFinite(order)) {
      setPositionError(t.positionError);
      return;
    }
    setPositionError(null);
    // Unlike the budget fields, parseLimit's "unparseable = unlimited" is not
    // acceptable here: a typo would silently open the course to everyone.
    // Only an explicitly blank field means unlimited.
    const seats = maxSelfRegistrations.trim();
    const seatCap = parseLimit(seats);
    if (seats && seatCap === null) {
      setSeatsError(t.seatsError);
      return;
    }
    setSeatsError(null);
    setSavingGeneral(true);
    setGeneralMsg(null);
    try {
      const updated = await coursesClient.updateCoursesCoursesIdPatch({
        id: courseId,
        body: {
          title: title.trim() || null,
          position: order,
          description: description.trim() || null,
          language_code: language.trim() || null,
          // Only sent when the caller may change it: the backend guard keys on
          // the field being present at all, so a lecturer including it — even
          // unchanged — would have their whole save rejected.
          ...(canSetPublic ? { public: isPublic } : {}),
          max_self_registrations: seatCap,
          tutor_agent_auto_route: autoRoute,
          max_test_runs: parseLimit(maxTestRuns),
          max_submissions: parseLimit(maxSubmissions),
          visible,
        },
      });
      setCourse(updated);
      setGeneralMsg(t.saved);
    } catch (e) {
      setGeneralMsg(e instanceof Error ? e.message : t.saveFailed);
    } finally {
      setSavingGeneral(false);
    }
  }

  const toggleMode = (m: string) => setModes((ms) => (ms.includes(m) ? ms.filter((x) => x !== m) : [...ms, m]));

  async function saveGit() {
    setSavingGit(true);
    setGitMsg(null);
    try {
      const selected = servers.find((s) => s.id === gitServerId);
      const body: CourseGitBindingUpsert = {
        delivery,
        git_server_id: gitServerId || null,
        template_repo: templateRepo.trim() || null,
        template_url: templateUrl.trim() || null,
        default_branch: branch.trim() || 'main',
        student_repo_modes: modes,
      };
      // External GitLab carries its own parent group + group token on the course.
      // Only send the token when the field was filled (blank keeps the stored one).
      if (selected?.type === 'gitlab') {
        if (parentGroupId.trim()) body.parent_group_id = parentGroupId.trim();
        if (token.trim()) body.token = token.trim();
      }
      await coursesClient.upsertCourseGitBindingEndpointCoursesCourseIdGitPut({ courseId, body });
      setGitMsg(t.saved);
      await load();
    } catch (e) {
      setGitMsg(e instanceof Error ? e.message : t.saveFailed);
    } finally {
      setSavingGit(false);
    }
  }

  if (!authLoading && isAuthenticated && !canEdit) {
    return <Forbidden message={t.forbidden} backLink={`/courses/${courseId}`} backText={t.backToCourse} />;
  }

  const serverLabel = (id?: string | null) => {
    const s = servers.find((x) => x.id === id);
    return s ? `${s.name || s.base_url} (${s.type})` : id || '—';
  };
  const gitConfigured = binding && binding.delivery;
  const gitLocked = !!binding?.locked;
  const selectedServer = servers.find((s) => s.id === gitServerId);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={t.pageTitle}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading />
        ) : (
          <ScrollArea>
            <div className="max-w-3xl space-y-6">
              {/* General */}
              <SectionCard title={t.general}>
                <Field label={f.title}>
                  <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
                </Field>
                <Field
                  label={t.courseOrder}
                  hint={t.courseOrderHint}
                >
                  <input
                    value={position}
                    onChange={(e) => setPosition(e.target.value)}
                    inputMode="decimal"
                    aria-invalid={!!positionError}
                    aria-describedby={positionError ? 'course-position-error' : undefined}
                    className={inputCls}
                  />
                </Field>
                {positionError && <p id="course-position-error" role="alert" className="text-sm text-danger-text">{positionError}</p>}
                <Field label={f.description}>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className={inputCls} />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label={t.languageCode}>
                    <input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="en" className={inputCls} />
                  </Field>
                  <Field label={t.path}>
                    <input value={course?.path || ''} readOnly className={readOnlyInputCls} />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field
                    label={t.maxTestRuns}
                    hint={t.limitHint}
                  >
                    <input
                      inputMode="numeric"
                      value={maxTestRuns}
                      onChange={(e) => setMaxTestRuns(e.target.value)}
                      placeholder={t.unlimited}
                      className={inputCls}
                    />
                  </Field>
                  <Field
                    label={t.maxSubmissions}
                    hint={t.limitHint}
                  >
                    <input
                      inputMode="numeric"
                      value={maxSubmissions}
                      onChange={(e) => setMaxSubmissions(e.target.value)}
                      placeholder={t.unlimited}
                      className={inputCls}
                    />
                  </Field>
                </div>
                <Field
                  label={t.visibility}
                  hint={t.visibilityHint}
                >
                  <VisibilitySelect
                    scope="course"
                    value={visible}
                    onChange={setVisible}
                  />
                </Field>
                <Field
                  label={t.selfRegistration}
                  hint={canSetPublic ? t.selfRegistrationHint : t.selfRegistrationLocked}
                >
                  <PublicCourseField
                    value={isPublic}
                    onChange={setIsPublic}
                    disabled={!canSetPublic}
                  />
                </Field>
                <Field
                  label={t.seats}
                  hint={t.seatsHint}
                >
                  <input
                    inputMode="numeric"
                    value={maxSelfRegistrations}
                    onChange={(e) => {
                      setMaxSelfRegistrations(e.target.value);
                      setSeatsError(null);
                    }}
                    placeholder={t.unlimited}
                    aria-invalid={seatsError ? true : undefined}
                    className={inputCls}
                  />
                </Field>
                {seatsError && (
                  <p role="alert" className="-mt-2 text-xs text-danger-text">
                    {seatsError} {t.nothingSaved}
                  </p>
                )}
                <Field label={f.aiTutor}>
                  <TutorAgentAutoRouteField value={autoRoute} onChange={setAutoRoute} />
                </Field>
                <div className="flex items-center gap-3">
                  <Button onClick={saveGeneral} loading={savingGeneral} loadingLabel={t.saving}>
                    {t.save}
                  </Button>
                  <SectionStatus>{generalMsg}</SectionStatus>
                </div>
              </SectionCard>

              {/* Git */}
              <SectionCard
                title={t.git}
                action={
                  gitLocked ? (
                    <Badge color="gray" className="inline-flex items-center gap-1">
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                      {t.locked}
                    </Badge>
                  ) : undefined
                }
                note={
                  gitLocked
                    ? `${binding?.lock_reason || t.lockedDefault} ${t.lockedNote}`
                    : undefined
                }
              >
                {gitLocked ? (
                  <DescriptionList
                    items={[
                      { term: t.deliveryTerm, value: binding!.delivery },
                      { term: f.gitServer, value: binding!.git_server_id ? serverLabel(binding!.git_server_id) : '—' },
                      { term: f.repoModes, value: (binding!.student_repo_modes || []).map((m) => f.modes[m] ?? m).join(', ') || '—' },
                      { term: t.template, value: binding!.template_repo || '—', mono: true },
                    ]}
                  />
                ) : (
                  <>
                    {!gitConfigured && (
                      <SectionHint>{t.noGit}</SectionHint>
                    )}
                    {!canManage && servers.length === 0 && (
                      <SectionHint>{t.serversCentral}</SectionHint>
                    )}
                    <Field label={f.delivery}>
                      <select value={delivery} onChange={(e) => setDelivery(e.target.value as 'git' | 'download')} className={inputCls}>
                        <option value="git">{t.deliveryGit}</option>
                        <option value="download">{t.deliveryDownload}</option>
                      </select>
                    </Field>
                    <Field label={t.templateServer} hint={t.templateServerHint}>
                      <select value={gitServerId} onChange={(e) => setGitServerId(e.target.value)} className={inputCls}>
                        <option value="">{t.none}</option>
                        {servers.map((s) => (
                          <option key={s.id} value={s.id}>{s.name || s.base_url} ({s.type})</option>
                        ))}
                      </select>
                    </Field>
                    {selectedServer?.type === 'gitlab' && (
                      <>
                        <Field label={f.parentGroup} hint={f.parentGroupHint}>
                          <input value={parentGroupId} onChange={(e) => setParentGroupId(e.target.value)} placeholder="12345" className={inputCls} />
                        </Field>
                        <Field label={f.groupToken} hint={hasToken ? t.tokenStored : f.groupTokenHint}>
                          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={hasToken ? t.tokenStoredPlaceholder : 'glpat-…'} className={inputCls} />
                        </Field>
                      </>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                      <Field label={t.templateRepo}>
                        <input value={templateRepo} onChange={(e) => setTemplateRepo(e.target.value)} placeholder="owner/repo" className={inputCls} />
                      </Field>
                      <Field label={t.defaultBranch}>
                        <input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="main" className={inputCls} />
                      </Field>
                    </div>
                    <Field label={t.templateUrl}>
                      <input value={templateUrl} onChange={(e) => setTemplateUrl(e.target.value)} placeholder={t.templateUrlPlaceholder} className={inputCls} />
                    </Field>
                    <Field label={f.repoModes}>
                      <div className="flex flex-wrap gap-3">
                        {STUDENT_REPO_MODES.map((m) => (
                          <label key={m} className="flex items-center gap-1.5 text-sm">
                            <input type="checkbox" checked={modes.includes(m)} onChange={() => toggleMode(m)} />
                            {f.modes[m] ?? m}
                          </label>
                        ))}
                      </div>
                    </Field>
                    <div className="flex items-center gap-3">
                      <Button onClick={saveGit} loading={savingGit} loadingLabel={t.saving}>
                        {gitConfigured ? t.saveGit : t.configureGit}
                      </Button>
                      <SectionStatus>{gitMsg}</SectionStatus>
                    </div>
                  </>
                )}
              </SectionCard>
            </div>
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
