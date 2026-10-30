'use client';

import { useState, type ReactNode } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { UserClient } from '@/src/generated/clients/UserClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCascadeDelete } from '@/src/hooks/useCascadeDelete';
import { useNotify } from '@/src/contexts/NotificationContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import CascadeDeletePreview from '@/src/components/CascadeDeletePreview';
import DescriptionList from '@/src/components/DescriptionList';
import SectionCard from '@/src/components/SectionCard';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import Notice from '@/src/components/ui/Notice';
import CourseWorkspaceLaunchButtons from '@/src/components/workspaces/CourseWorkspaceLaunchButtons';
import SelfEnrollmentHelp from '@/src/components/courses/SelfEnrollmentHelp';
import CourseProgressCard from '@/src/components/student/CourseProgress';
import { displayName } from '@/src/utils/displayName';
import { localized } from '@/src/utils/localizedText';
import { localizedRoleLabel } from '@/src/utils/courseRoles';
import type { PersonalCloneCredentialGet } from 'types/generated';
import { localeFor, languageName } from '@/src/utils/locale';
import { deliveryLabel, lockReasonText } from '@/src/utils/courseGit';

const coursesClient = new CoursesClient();
const courseFamiliesClient = new CourseFamiliesClient();
const organizationsClient = new OrganizationsClient();

const userClient = new UserClient();

const COPY = {
  de: {
    // What a repository mode means to the person who owns it, rather than the
    // word the binding stores.
    repoModeLabel: {
      managed: 'Für dich gehostet',
      external: 'Dein eigenes Repository',
      download: 'Nur Download',
    } as Record<string, string>,
    // Role labels as usePermissions().courseRole returns them.
    copied: 'Kopiert.',
    copyFailed: 'Kopieren in die Zwischenablage nicht möglich',
    copy: 'Kopieren',
    courseArchived: 'Kurs archiviert.',
    courseUnarchived: 'Kurs wiederhergestellt.',
    updateFailed: 'Kurs konnte nicht aktualisiert werden',
    gitChecked: 'Git-Zugriff geprüft. Dein Repository ist erreichbar.',
    gitCheckFailed: 'Git-Zugriff konnte nicht geprüft werden',
    notFound: 'Kurs nicht gefunden',
    left: (title: string) => `Du hast ${title} verlassen.`,
    leaveFailed: 'Der Kurs konnte nicht verlassen werden.',
    courses: 'Kurse',
    untitled: 'Kurs ohne Titel',
    untitledShort: 'Ohne Titel',
    archived: 'Archiviert',
    edit: 'Bearbeiten',
    unarchive: 'Wiederherstellen',
    archive: 'Archivieren',
    delete: 'Löschen',
    archivedNotice:
      'Archiviert: Studierende sehen diesen Kurs nicht mehr und können nichts einreichen. Eigentümer können ihn wiederherstellen.',
    about: 'Über diesen Kurs',
    yourRole: 'Deine Rolle',
    organization: 'Organisation',
    courseFamily: 'Kursfamilie',
    language: 'Sprache',
    created: 'Erstellt',
    lastUpdated: 'Zuletzt geändert',
    workspaces: 'Arbeitsumgebungen',
    yourRepository: 'Dein Repository',
    ready: 'Bereit',
    notSetUp: 'Noch nicht eingerichtet',
    checking: 'Wird geprüft …',
    checkAccess: 'Zugriff prüfen',
    repoSetUp:
      'Automatisch eingerichtet, als du diesen Kurs in VS Code geöffnet hast. Deine Arbeit wird von dort hochgeladen. Hier ist nichts zu tun.',
    repository: 'Repository',
    browse: 'Ansehen',
    noRepoStaff:
      'Für dich wurde noch kein Repository erstellt. Mitglieder erhalten es automatisch, wenn sie den Kurs zum ersten Mal in VS Code öffnen. „Zugriff prüfen“ erstellt deines jetzt und gewährt dir als Lehrperson erneut Zugriff auf die Vorlagen- und Referenz-Repositories.',
    noRepoStudent:
      'Hier ist nichts zu tun. Dein Repository wird für dich erstellt, sobald du diesen Kurs zum ersten Mal in VS Code öffnest, in einer Computor-Arbeitsumgebung oder mit der Computor-Erweiterung.',
    outsideVscode: 'Außerhalb von VS Code arbeiten?',
    outsideIntroBefore:
      'Eine Computor-Arbeitsumgebung richtet Git für dich ein. Hier findest du die Angaben, um das Repository von Hand zu klonen. Mit ',
    outsideIntroAfter: ' erstellst du es und zeigst die Zugangsdaten an.',
    outsideStaff:
      ' Als Lehrperson gewährt dieser Aufruf dir außerdem erneut Zugriff auf die Kursvorlage und die Referenz-Repositories.',
    hosting: 'Hosting',
    gitServer: 'Git-Server',
    cloneHttps: 'Klonen (HTTPS)',
    credentialTitle: 'Deine persönlichen Git-Zugangsdaten. Behandle sie wie ein Passwort.',
    credentialBody:
      'Sie sind unabhängig von den Zugangsdaten deiner Arbeitsumgebung und funktionieren immer weiter, egal was die Arbeitsumgebung tut. Wenn du den Zugriff erneut prüfst, werden dieselben angezeigt. Klonen in einem Schritt:',
    username: 'Benutzername',
    token: 'Token',
    gitConfiguration: 'Git-Konfiguration',
    delivery: 'Bereitstellung',
    defaultBranch: 'Standard-Branch',
    studentRepos: 'Repositories der Studierenden',
    repoModes: {
      managed: 'Von Computor bereitgestellt',
      external: 'Selbst gehostet',
      download: 'Download ohne Git',
    } as Record<string, string>,
    status: 'Status',
    locked: 'Gesperrt',
    editable: 'Bearbeitbar',
    template: 'Vorlage',
    noGitBinding: 'Für diesen Kurs ist keine Git-Anbindung konfiguriert.',
    deleteTitle: (name: string) => `Kurs „${name}“ löschen?`,
    deleteMessage:
      'Dadurch werden der Kurs, seine Mitglieder, Aufgaben, Abgaben und Ergebnisse sowie seine Vorlagen- und Referenz-Repositories dauerhaft gelöscht. Das kann nicht rückgängig gemacht werden.',
  },
  en: {
    repoModeLabel: {
      managed: 'Hosted for you',
      external: 'Your own repository',
      download: 'Download only',
    } as Record<string, string>,
    copied: 'Copied.',
    copyFailed: 'Could not copy to clipboard',
    copy: 'Copy',
    courseArchived: 'Course archived.',
    courseUnarchived: 'Course unarchived.',
    updateFailed: 'Could not update the course',
    gitChecked: 'Git access checked — your repository is reachable.',
    gitCheckFailed: 'Could not check git access',
    notFound: 'Course not found',
    left: (title: string) => `You left ${title}.`,
    leaveFailed: 'Could not leave the course.',
    courses: 'Courses',
    untitled: 'Untitled Course',
    untitledShort: 'Untitled',
    archived: 'Archived',
    edit: 'Edit',
    unarchive: 'Unarchive',
    archive: 'Archive',
    delete: 'Delete',
    archivedNotice:
      'Archived: students no longer see this course and cannot submit. An owner can unarchive it.',
    about: 'About',
    yourRole: 'Your role',
    organization: 'Organization',
    courseFamily: 'Course family',
    language: 'Language',
    created: 'Created',
    lastUpdated: 'Last updated',
    workspaces: 'Workspaces',
    yourRepository: 'Your repository',
    ready: 'Ready',
    notSetUp: 'Not set up yet',
    checking: 'Checking…',
    checkAccess: 'Check access',
    repoSetUp:
      'Set up automatically when you opened this course in VS Code. Your work is pushed from there — nothing here needs doing.',
    repository: 'Repository',
    browse: 'Browse',
    noRepoStaff:
      'No repository has been created for you yet. Members get one automatically the first time they open the course in VS Code; Check access creates yours now and re-grants your staff access to the template and reference repositories.',
    noRepoStudent:
      'Nothing to do here. Your repository is created for you the first time you open this course in VS Code — in a Computor workspace or with the Computor extension.',
    outsideVscode: 'Working outside VS Code?',
    outsideIntroBefore:
      'A Computor workspace configures git for you. These are the details for cloning the repository by hand; use ',
    outsideIntroAfter: ' to create it and reveal the credential.',
    outsideStaff:
      ' As staff, that call also re-grants your access to the course template and reference repositories.',
    hosting: 'Hosting',
    gitServer: 'Git server',
    cloneHttps: 'Clone (HTTPS)',
    credentialTitle: 'Your personal git credential — treat it like a password.',
    credentialBody:
      'It is independent of the credential your workspace manages, so it keeps working no matter what the workspace does; checking access again shows the same one. Clone in one step:',
    username: 'Username',
    token: 'Token',
    gitConfiguration: 'Git configuration',
    delivery: 'Delivery',
    defaultBranch: 'Default branch',
    studentRepos: 'Student repos',
    repoModes: {
      managed: 'Hosted by Computor',
      external: 'Self-hosted',
      download: 'Download without git',
    } as Record<string, string>,
    status: 'Status',
    locked: 'Locked',
    editable: 'Editable',
    template: 'Template',
    noGitBinding: 'No git binding configured for this course.',
    deleteTitle: (name: string) => `Delete course “${name}”?`,
    deleteMessage:
      'This permanently deletes the course, its members, assignments, submissions and results, and its template and reference repositories. It is irreversible.',
  },
};

const PROVIDER_LABEL: Record<string, string> = {
  forgejo: 'Forgejo',
  gitlab: 'GitLab',
};

/** A value nobody wants to select by hand — a clone URL, a token. */
function CopyValue({ value }: { value: string }) {
  const t = COPY[useUiLanguage()];
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
            .then(() => notify(t.copied, 'success'))
            .catch(() => notify(t.copyFailed, 'error'))
        }
      >
        {t.copy}
      </Button>
    </span>
  );
}

export default function CoursePage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const courseId = useParams().id as string;
  const router = useRouter();
  const { refreshPermissions } = useAuth();
  const {
    canManageHierarchy: canManage,
    isAdmin,
    isOrganizationManager,
    courseHasAtLeast,
    courseRole,
    canArchiveCourse,
    canDeleteCourse,
  } = usePermissions();
  const canManageMembers = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');
  // Progress is the learner's own: a tutor or lecturer has no submissions here.
  const isLearner = courseHasAtLeast(courseId, '_student') && !courseHasAtLeast(courseId, '_tutor');
  // Any course role at all, without the admin bypass of courseHasAtLeast.
  const isMember = courseRole(courseId) != null;
  const isOrdinaryLearner = !isAdmin && !isOrganizationManager && isLearner;

  const { data, loading, error, reload } = useResource(
    async () => {
      const course = await coursesClient.getCoursesCoursesIdGet({ id: courseId });
      const [organization, courseFamily, gitBinding, myRepo, gitDescriptor, selfEnrollment] = await Promise.all([
        organizationsClient.getOrganizationsOrganizationsIdGet({ id: course.organization_id }).catch(() => null),
        courseFamiliesClient.getCourseFamiliesCourseFamiliesIdGet({ id: course.course_family_id }).catch(() => null),
        // Git binding is lecturer-cohort only; fetch it only for managers.
        canManageMembers
          ? coursesClient.getCourseGitBindingEndpointCoursesCourseIdGitGet({ courseId }).catch(() => null)
          : Promise.resolve(null),
        // The caller's own repository and enrolment exist only for members;
        // asking for them as a non-member (an admin browsing a course) is a
        // 404 in the console on every visit, so skip both.
        isMember
          ? userClient.getStudentRepositoryEndpointUserCoursesCourseIdRepositoryGet({ courseId }).catch(() => null)
          : Promise.resolve(null),
        // Whether this course provisions git at all — drives the repo section
        // (everyone), so a non-git course never shows the provision button.
        userClient.getCourseGitDescriptorEndpointUserCoursesCourseIdGitGet({ courseId }).catch(() => null),
        // Whether the caller joined through the catalog (help block, leave).
        isMember
          ? userClient.getOwnSelfEnrollmentUserCoursesCourseIdSelfEnrollmentGet({ courseId }).catch(() => null)
          : Promise.resolve(null),
      ]);
      return { course, organization, courseFamily, gitBinding, myRepo, gitDescriptor, selfEnrollment };
    },
    [courseId, canManageMembers, isMember],
  );
  // Display only; the course edit page loads its own copy with the source text.
  const course = localized(data?.course ?? null, language);
  const organization = data?.organization ?? null;
  const courseFamily = localized(data?.courseFamily ?? null, language);
  const gitBinding = data?.gitBinding ?? null;
  const myRepo = data?.myRepo ?? null;
  const gitDescriptor = data?.gitDescriptor ?? null;
  const selfEnrollment = data?.selfEnrollment ?? null;
  // The course actually provisions git repos — the exact condition under which
  // provision-repository succeeds (binding present + git delivery). Gate the
  // repo section on this so a non-git course never offers the provision button.
  const gitConfigured = gitDescriptor?.configured === true && gitDescriptor?.delivery === 'git';

  // The caller's own standing in this course, as a label ('Student',
  // 'Lecturer', …) or null when they hold no course role.
  const roleEnglish = courseRole(courseId);
  const myRole = roleEnglish && (localizedRoleLabel(roleEnglish, language));

  const notify = useNotify();
  const [ensuring, setEnsuring] = useState(false);
  const [archiving, setArchiving] = useState(false);

  // Owner-only lifecycle. Archiving hides the course from students and closes
  // submissions; it is reversible. Deleting previews first (dry run) and then
  // asks for the course path — and the preview carries the server's
  // `blocked_reason` when the real call would be refused (a course with student
  // submissions is admin-only, and even an admin must archive it first).
  async function setArchived(archived: boolean) {
    setArchiving(true);
    try {
      if (archived) await coursesClient.routeCoursesCoursesIdArchivePatch({ id: courseId });
      else await coursesClient.unarchiveCoursesCoursesIdUnarchivePatch({ id: courseId });
      notify(archived ? t.courseArchived : t.courseUnarchived, 'success');
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.updateFailed, 'error');
    } finally {
      setArchiving(false);
    }
  }
  const del = useCascadeDelete(
    () => coursesClient.deleteCourseEndpointCoursesCourseIdDelete({ courseId, dryRun: true }),
    () => coursesClient.deleteCourseEndpointCoursesCourseIdDelete({ courseId, dryRun: false }),
    async () => {
      // The caller just lost their _owner membership; refresh the cached scopes
      // so the list does not keep offering a course that is gone.
      await refreshPermissions();
      router.push('/courses');
    },
  );
  const [personalCred, setPersonalCred] = useState<PersonalCloneCredentialGet | null>(null);
  // Fully controlled rather than an `open` attribute derived from `provisioned`:
  // any unrelated re-render would otherwise snap the disclosure shut under the
  // reader while they are copying out of it.
  const [cloneOpen, setCloneOpen] = useState(false);

  // Ends the caller's own self-enrolment. The backend keeps the membership
  // (submissions and results hang on it) but withdraws every course claim, so
  // re-pull the scopes before leaving a page the caller can no longer read.
  async function leaveCourse() {
    if (!course) return;
    try {
      await userClient.leaveCourseUserCoursesCourseIdLeavePost({ courseId });
      await refreshPermissions();
      notify(t.left(displayName(course, t.untitled)), 'success');
      router.push('/courses');
    } catch (err) {
      notify(err instanceof Error && err.message ? err.message : t.leaveFailed, 'error');
    }
  }

  async function ensureGitAccess() {
    setEnsuring(true);
    setPersonalCred(null);
    try {
      await userClient.provisionStudentRepositoryEndpointUserCoursesCourseIdProvisionRepositoryPost(
        { courseId },
      );
      // A credential of the reader's own, NOT the workspace-managed token: that
      // one is re-minted by every workspace credential repair, which silently
      // killed whatever a student had copied from this page (#342).
      const cred = await userClient
        .personalCloneCredentialEndpointUserCoursesCourseIdCloneCredentialPost({ courseId })
        .catch(() => null);
      setPersonalCred(cred);
      // The credential is only reachable from inside the disclosure, so open it
      // rather than leaving the freshly-fetched token hidden behind a summary.
      if (cred?.clone_token) setCloneOpen(true);
      notify(t.gitChecked, 'success');
      await reload(); // refresh the persisted repository details below
    } catch (e) {
      notify(e instanceof Error ? e.message : t.gitCheckFailed, 'error');
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
          <ErrorBanner>{error || t.notFound}</ErrorBanner>
        </div>
      </AuthenticatedLayout>
    );
  }

  // Hierarchy breadcrumb: Organization › Course family › Course, falling back to
  // the flat Courses list when those aren't readable (e.g. for students).
  const crumbs: { label: string; href?: string }[] = [];
  if (organization)
    crumbs.push({ label: displayName(organization, t.untitledShort), href: `/organizations/${organization.id}` });
  if (courseFamily)
    crumbs.push({ label: displayName(courseFamily, t.untitledShort), href: `/course-families/${courseFamily.id}` });
  if (crumbs.length === 0) crumbs.push({ label: t.courses, href: '/courses' });
  crumbs.push({ label: displayName(course, t.untitled) });

  type Fact = { term: string; value: ReactNode; mono?: boolean };
  const facts = (items: (Fact | false | null | undefined | '')[]): Fact[] =>
    items.filter(Boolean) as Fact[];

  const isArchived = Boolean(course.archived_at);
  const dateLocale = localeFor(language);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={crumbs}
          title={displayName(course, t.untitled)}
          subtitle={isArchived && <Badge tone="muted">{t.archived}</Badge>}
          actions={
            <>
              {canManage && (
                <ButtonLink href={`/courses/${courseId}/edit`} variant="secondary">
                  {t.edit}
                </ButtonLink>
              )}
              {canArchiveCourse(courseId) && (
                <Button
                  variant="secondary"
                  onClick={() => setArchived(!isArchived)}
                  loading={archiving}
                  loadingLabel={isArchived ? t.unarchive : t.archive}
                >
                  {isArchived ? t.unarchive : t.archive}
                </Button>
              )}
              {canDeleteCourse(courseId) && (
                <Button variant="dangerGhost" onClick={del.begin} loading={del.opening} loadingLabel={t.delete}>
                  {t.delete}
                </Button>
              )}
            </>
          }
        />

        <ScrollArea>
        {isArchived && (
          <Notice tone="info">
            {t.archivedNotice}
          </Notice>
        )}
        {/* About — description + the few facts worth showing (no identifiers).
            First card: the course introduces itself before it hands out tools,
            and the description is what a member opening an unfamiliar course
            came to read.

            "Your role" leads because it is the only line here that is about the
            reader. The record timestamps are administrative trivia to everyone
            below the lecturer cohort, so a student is not shown them. */}
        <SectionCard title={t.about}>
          {course.description && <p className="text-body">{course.description}</p>}
          <DescriptionList
            items={facts([
              myRole && { term: t.yourRole, value: <Badge tone="info">{myRole}</Badge> },
              organization && { term: t.organization, value: displayName(organization, t.untitledShort) },
              courseFamily && { term: t.courseFamily, value: displayName(courseFamily, t.untitledShort) },
              course.language_code && {
                term: t.language,
                value: languageName(course.language_code, language),
              },
              canManageMembers &&
                course.created_at && {
                  term: t.created,
                  value: new Date(course.created_at).toLocaleDateString(dateLocale),
                },
              canManageMembers &&
                course.updated_at && {
                  term: t.lastUpdated,
                  value: new Date(course.updated_at).toLocaleDateString(dateLocale),
                },
            ])}
          />
        </SectionCard>

        {/* How far the learner is and where to pick up (issues#408, #525). It
            sits above the workspace launch, so a returning learner sees which
            assignment comes next before opening the editor. */}
        {isLearner && <CourseProgressCard courseId={courseId} language={language} />}

        {/* Workspaces: launch buttons for the course's allowed templates. The
            component hides itself (card and heading included) when the course
            offers none; the role gate only avoids a guaranteed-403 fetch for
            non-members. The card chrome is the caller's because the compact
            variant on the courses list renders without one. */}
        {!isOrdinaryLearner && (isAdmin || myRole != null) && (
          <CourseWorkspaceLaunchButtons
            courseId={courseId}
            title={t.workspaces}
            className="bg-surface rounded-lg border border-rule p-6"
          />
        )}

        {/* Help & contact for a course joined through the catalog: a
            self-enrolled learner has no lecturer or tutor to ask (issues#458). */}
        {selfEnrollment?.self_registered && (
          <SelfEnrollmentHelp
            courseId={courseId}
            courseTitle={displayName(course, t.untitled)}
            canLeave={selfEnrollment.can_leave === true}
            language={language}
            onLeave={leaveCourse}
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
            title={t.yourRepository}
            action={
              <div className="flex items-center gap-2">
                {myRepo ? (
                  <Badge tone="success" pill>{t.ready}</Badge>
                ) : (
                  <Badge tone="muted" pill>{t.notSetUp}</Badge>
                )}
                <Button size="sm" variant="secondary" onClick={ensureGitAccess} loading={ensuring} loadingLabel={t.checking}>
                  {t.checkAccess}
                </Button>
              </div>
            }
          >
            {myRepo ? (
              <>
                <p className="text-sm text-muted">
                  {t.repoSetUp}
                </p>
                <DescriptionList
                  items={facts([
                    myRepo.repo_ref && { term: t.repository, value: myRepo.repo_ref, mono: true },
                    myRepo.web_url && {
                      term: t.browse,
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
                {t.noRepoStaff}
              </p>
            ) : (
              <p className="text-sm text-muted">
                {t.noRepoStudent}
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
                {t.outsideVscode}
              </summary>
              <div className="mt-3 space-y-3">
                <p className="text-sm text-muted">
                  {t.outsideIntroBefore}
                  <span className="font-medium">{t.checkAccess}</span>
                  {t.outsideIntroAfter}
                  {canManage ? t.outsideStaff : ''}
                </p>
                {myRepo && (
                  <DescriptionList
                    items={facts([
                      { term: t.hosting, value: t.repoModeLabel[myRepo.mode] ?? myRepo.mode },
                      myRepo.provider_type && {
                        term: t.gitServer,
                        value: PROVIDER_LABEL[myRepo.provider_type] ?? myRepo.provider_type,
                      },
                      myRepo.http_url && {
                        term: t.cloneHttps,
                        value: <CopyValue value={myRepo.http_url} />,
                      },
                    ])}
                  />
                )}
                {personalCred?.clone_token && (
                  <Notice tone="warning">
                    <p className="font-medium">
                      {t.credentialTitle}
                    </p>
                    <p className="mt-1">
                      {t.credentialBody}
                    </p>
                    <div className="mt-2">
                      {personalCred.clone_command && <CopyValue value={personalCred.clone_command} />}
                    </div>
                    <dl className="mt-2 space-y-1">
                      <div className="flex gap-2">
                        <dt className="w-20 shrink-0">{t.username}</dt>
                        <dd><CopyValue value={personalCred.clone_username ?? ''} /></dd>
                      </div>
                      <div className="flex gap-2">
                        <dt className="w-20 shrink-0">{t.token}</dt>
                        <dd><CopyValue value={personalCred.clone_token} /></dd>
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
          <SectionCard title={t.gitConfiguration}>
            {gitBinding ? (
              <DescriptionList
                items={facts([
                  { term: t.delivery, value: deliveryLabel(gitBinding.delivery, language) },
                  gitBinding.default_branch && {
                    term: t.defaultBranch,
                    value: gitBinding.default_branch,
                    mono: true,
                  },
                  gitBinding.student_repo_modes &&
                    gitBinding.student_repo_modes.length > 0 && {
                      term: t.studentRepos,
                      value: gitBinding.student_repo_modes.map((m) => t.repoModes[m] ?? m).join(', '),
                    },
                  {
                    term: t.status,
                    value: gitBinding.locked ? (
                      <Badge tone="warning" title={lockReasonText(gitBinding.lock_reason, language) ?? undefined}>
                        {t.locked}
                      </Badge>
                    ) : (
                      <Badge tone="success">{t.editable}</Badge>
                    ),
                  },
                  (gitBinding.template_url || gitBinding.template_repo) && {
                    term: t.template,
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
              <p className="text-sm text-muted">{t.noGitBinding}</p>
            )}
          </SectionCard>
        )}

        </ScrollArea>
      </ListPageLayout>

      {del.preview && (
        <ConfirmDeleteDialog
          title={t.deleteTitle(displayName(course, t.untitled))}
          message={t.deleteMessage}
          confirmWord={course.path}
          preview={<CascadeDeletePreview result={del.preview} />}
          blockedReason={del.preview.blocked_reason}
          onConfirm={del.confirm}
          onClose={del.close}
        />
      )}
    </AuthenticatedLayout>
  );
}
