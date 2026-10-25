'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import Forbidden from '@/src/components/Forbidden';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import WorkspaceStatusBadge from '@/src/components/workspaces/WorkspaceStatusBadge';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useNotify } from '@/src/contexts/NotificationContext';
import { inputCls } from '@/src/components/ui/tokens';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CourseWorkspacesClient } from '@/src/clients/CourseWorkspacesClient';
import type { StudentWorkspaceProvisionOutcome } from '@/src/types/workspaces';
import { userName } from '@/src/utils/userName';

const membersClient = new CourseMembersClient();
const courseWorkspacesClient = new CourseWorkspacesClient();

const COPY = {
  de: {
    workspaces: 'Arbeitsumgebungen',
    policySaved: 'Richtlinie gespeichert. Neue Arbeitsumgebungen übernehmen sie sofort.',
    policySaveFailed: 'Die Richtlinie konnte nicht gespeichert werden',
    applied: (n: number) => `${n} Arbeitsumgebung(en) unter der aktuellen Richtlinie neu gestartet`,
    appliedSkipped: (n: number) => `; ${n} unverändert gelassen (siehe Liste)`,
    applyFailed: 'Die Richtlinie konnte nicht angewendet werden',
    provisioned: (n: number) => `${n} Arbeitsumgebung(en) bereitgestellt`,
    provisionedFailed: (n: number) => `, ${n} fehlgeschlagen`,
    provisionFailed: 'Bereitstellung fehlgeschlagen',
    deleted: 'Arbeitsumgebung gelöscht',
    deleteFailed: 'Die Arbeitsumgebung konnte nicht gelöscht werden',
    title: 'Arbeitsumgebungen der Studierenden',
    subtitle: 'Stelle (temporäre) Arbeitsumgebungen für deine Studierenden bereit und verwalte die vorhandenen.',
    loading: 'Wird geladen …',
    notEnabled: 'Die Bereitstellung durch Lehrende ist für diesen Kurs nicht aktiviert. Eine Person mit Wartungsrechten für Arbeitsumgebungen kann sie im Verwaltungsbereich für Arbeitsumgebungen aktivieren.',
    noTemplates: 'Diesem Kurs sind noch keine Arbeitsumgebungs-Vorlagen zugewiesen. Eine Person mit Wartungsrechten für Arbeitsumgebungen kann sie im Verwaltungsbereich für Arbeitsumgebungen zuweisen.',
    rootInternetFor: (name: string) => `Root und Internet für ${name}`,
    policyIntro: 'Was die Arbeitsumgebungen dieses Kurses mit dieser Vorlage erhalten. Ein Kurs kann nur Zugriff wegnehmen, eine Option ist gesperrt, wenn die Vorlage sie bereits verweigert. Neue Arbeitsumgebungen übernehmen das sofort, bestehende behalten, womit sie erstellt wurden, bis du es anwendest oder sie das nächste Mal starten.',
    root: 'Root (sudo)',
    internet: 'Internet',
    templateDenies: 'Die Vorlage verweigert das, ein Kurs kann es nicht gewähren.',
    offForTemplate: '(für diese Vorlage aus)',
    applying: 'Wird angewendet …',
    applyRunning: 'Auf laufende Arbeitsumgebungen anwenden',
    applyHint: 'Startet sie neu, damit die Änderung sofort gilt. Laufende Prozesse werden beendet, Dateien bleiben unberührt. Gestoppte Arbeitsumgebungen übernehmen sie beim nächsten Start.',
    provisionTitle: 'Für Studierende bereitstellen',
    provisionIntro: 'Erstellt eine Arbeitsumgebung pro ausgewählter studierender Person. Die Studierenden können diese öffnen und starten, aber keine neuen bereitstellen. Eine temporäre Arbeitsumgebung nutzt ein eigenes temporäres Home-Volume, das zusammen mit der Arbeitsumgebung gelöscht wird. Die regulären Dateien der Studierenden bleiben unberührt.',
    template: 'Vorlage',
    notSetUp: ' — auf diesem Server nicht eingerichtet',
    notDeployable: 'Dieser Arbeitsumgebungstyp ist auf diesem Server noch nicht eingerichtet, daher kann nichts darauf bereitgestellt werden. Eine Person mit Wartungsrechten für Arbeitsumgebungen richtet ihn in der Verwaltung der Arbeitsumgebungen ein.',
    studentsGet: 'Studierende erhalten',
    withRoot: 'Root',
    noRoot: 'kein Root',
    and: 'und',
    withInternet: 'Internet',
    noInternet: 'kein Internet',
    home: 'Home-Verzeichnis',
    homeScratch: 'Temporär (wird mit der Arbeitsumgebung gelöscht)',
    homeShared: 'Übliches Home (von allen Arbeitsumgebungen gemeinsam genutzt)',
    label: 'Bezeichnung',
    labelHint: 'Namenssuffix (z. B. „exam1“), damit sie sich von den eigenen Arbeitsumgebungen der Studierenden unterscheiden.',
    selectAll: 'Alle Mitglieder auswählen',
    member: 'Mitglied',
    role: 'Rolle',
    lastRun: 'Letzter Lauf',
    select: (name: string) => `${name} auswählen`,
    provisionedName: (name: string) => `${name} bereitgestellt`,
    noMembers: 'Keine Kursmitglieder.',
    provisioning: 'Wird bereitgestellt …',
    provisionSelected: (n: number) => `Für ${n} Ausgewählte bereitstellen`,
    provisionHint: 'Läuft nacheinander, Fehler werden pro Person gemeldet und brechen den Stapel nie ab.',
    existingTitle: 'Vorhandene Arbeitsumgebungen der Studierenden',
    existingIntro: 'Für diesen Kurs bereitgestellte Arbeitsumgebungen. Die eigene Arbeitsumgebung eines Mitglieds wird hier nicht aufgeführt, auch wenn sie eine dieser Vorlagen nutzt. Sie gehört der Person, nicht dem Kurs, und wird in der Verwaltung der Arbeitsumgebungen verwaltet.',
    student: 'Studierende(r)',
    workspace: 'Arbeitsumgebung',
    homeCol: 'Home',
    status: 'Status',
    actions: 'Aktionen',
    throwaway: 'Temporär',
    shared: 'Gemeinsam',
    confirmDelete: 'Löschen bestätigen',
    delete: 'Löschen',
    noStudentWorkspaces: 'Keine Arbeitsumgebungen der Studierenden mit den Vorlagen dieses Kurses.',
    forbidden: 'Die Arbeitsumgebungs-Konsole erfordert die Lehrenden-Rolle in diesem Kurs.',
    backToCourse: 'Zurück zum Kurs',
  },
  en: {
    workspaces: 'Workspaces',
    policySaved: 'Policy saved. New workspaces get it immediately.',
    policySaveFailed: 'Failed to save the policy',
    applied: (n: number) => `${n} workspace(s) restarted under the current policy`,
    appliedSkipped: (n: number) => `; ${n} left alone (see the list)`,
    applyFailed: 'Failed to apply the policy',
    provisioned: (n: number) => `${n} workspace(s) provisioned`,
    provisionedFailed: (n: number) => `, ${n} failed`,
    provisionFailed: 'Provisioning failed',
    deleted: 'Workspace deleted',
    deleteFailed: 'Failed to delete workspace',
    title: 'Student workspaces',
    subtitle: 'Provision (throwaway) workspaces for your students and manage the ones that exist',
    loading: 'Loading…',
    notEnabled: 'Lecturer provisioning is not enabled for this course. A workspace maintainer can enable it in the workspace administration area.',
    noTemplates: 'This course has no workspace templates yet. A workspace maintainer can assign templates in the workspace administration area.',
    rootInternetFor: (name: string) => `Root & internet for ${name}`,
    policyIntro: "What this course's workspaces of this template get. A course can only take access away — a control is locked when the template itself already denies it. New workspaces get this immediately; existing ones keep what they were created with until you apply it or they next start.",
    root: 'Root (sudo)',
    internet: 'Internet',
    templateDenies: 'The template denies this; a course cannot grant it.',
    offForTemplate: '(off for this template)',
    applying: 'Applying…',
    applyRunning: 'Apply to running workspaces',
    applyHint: 'Restarts them so the change takes effect now — running processes end, files are untouched. Stopped workspaces pick it up when they next start.',
    provisionTitle: 'Provision for students',
    provisionIntro: "Creates one workspace per selected student. Students can open and start these, but not provision new ones. A throwaway workspace uses its own scratch home volume that is deleted together with the workspace — the student's regular files stay untouched.",
    template: 'Template',
    notSetUp: ' — not set up on this server',
    notDeployable: 'This workspace type is not set up on this server yet, so nothing can be provisioned onto it. A workspace maintainer deploys it under workspace administration.',
    studentsGet: 'Students get',
    withRoot: 'root',
    noRoot: 'no root',
    and: 'and',
    withInternet: 'internet',
    noInternet: 'no internet',
    home: 'Home directory',
    homeScratch: 'Throwaway (deleted with the workspace)',
    homeShared: 'Usual home (shared across workspaces)',
    label: 'Label',
    labelHint: 'Name suffix (e.g. "exam1") — keeps these apart from the students\' own workspaces.',
    selectAll: 'Select all members',
    member: 'Member',
    role: 'Role',
    lastRun: 'Last run',
    select: (name: string) => `Select ${name}`,
    provisionedName: (name: string) => `Provisioned ${name}`,
    noMembers: 'No course members.',
    provisioning: 'Provisioning…',
    provisionSelected: (n: number) => `Provision for ${n} selected`,
    provisionHint: 'Runs one at a time; failures are reported per student and never abort the batch.',
    existingTitle: 'Existing student workspaces',
    existingIntro: "Workspaces provisioned for this course. A member's own workspace is not listed here even when it uses one of these templates — it belongs to them, not to the course, and is managed under workspace administration.",
    student: 'Student',
    workspace: 'Workspace',
    homeCol: 'Home',
    status: 'Status',
    actions: 'Actions',
    throwaway: 'Throwaway',
    shared: 'Shared',
    confirmDelete: 'Confirm delete',
    delete: 'Delete',
    noStudentWorkspaces: "No student workspaces on this course's templates.",
    forbidden: 'The workspace console requires the lecturer role for this course.',
    backToCourse: 'Back to course',
  },
};

function LecturerWorkspacesContent() {
  const courseId = useParams().id as string;
  const t = COPY[useUiLanguage()];
  const crumbs = useCourseCrumbs(courseId, t.workspaces);
  const notify = useNotify();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [template, setTemplate] = useState('');
  const [homeMode, setHomeMode] = useState<'scratch' | 'shared'>('scratch');
  const [label, setLabel] = useState('');
  const [provisioning, setProvisioning] = useState(false);
  const [outcomes, setOutcomes] = useState<StudentWorkspaceProvisionOutcome[] | null>(null);
  // Two-step delete: first click arms, second click deletes.
  const [armedDelete, setArmedDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [applying, setApplying] = useState(false);

  const { data, loading, error, reload } = useResource(
    async () => {
      const [settings, members, studentWorkspaces] = await Promise.all([
        courseWorkspacesClient.getSettings({ courseId }),
        membersClient.listCourseMembersCourseMembersGet({ courseId, limit: 500 }),
        courseWorkspacesClient.listStudentWorkspaces({ courseId }).catch(() => null),
      ]);
      return { settings, members, studentWorkspaces };
    },
    [courseId],
  );

  const settings = data?.settings ?? null;
  const members = useMemo(
    () =>
      (data?.members ?? [])
        .slice()
        .sort((a, b) => userName(a.user).localeCompare(userName(b.user))),
    [data],
  );
  const templates = (settings?.templates ?? []).filter((tpl) => tpl.enabled);
  // A course keeps its templates by name, so it can offer one Coder does not
  // have — never deployed, or deleted since. Provisioning onto it fails per
  // student, which here means one failure per person in the selection.
  // (`exists_in_coder` is null when Coder was unreachable: claim nothing then.)
  const deployable = templates.filter((tpl) => tpl.exists_in_coder !== false);
  const provisionAllowed = (settings?.lecturer_provision_enabled ?? false) || (settings?.can_manage ?? false);
  const effectiveTemplate = template || deployable[0]?.template_name || '';
  const selectedTemplate = templates.find((tpl) => tpl.template_name === effectiveTemplate);
  const selectedIsDeployable = selectedTemplate ? selectedTemplate.exists_in_coder !== false : false;
  // Editing the policy stays a workspace-maintainer job; a lecturer sees the
  // effective values read-only next to the template picker.
  const canManage = settings?.can_manage ?? false;

  function toggleMember(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) =>
      prev.size === members.length ? new Set() : new Set(members.map((m) => m.id)),
    );
  }

  /** The course can only narrow, so "allowed" is stored as null (inherit)
   *  rather than true — see the backend's _narrowing. */
  async function savePolicy(key: 'allow_root' | 'allow_internet', allowed: boolean) {
    if (!settings || !selectedTemplate) return;
    setSavingPolicy(true);
    try {
      await courseWorkspacesClient.updateSettings({
        courseId,
        body: {
          template_names: settings.templates.map((tpl) => tpl.template_name),
          lecturer_provision_enabled: settings.lecturer_provision_enabled,
          template_policies: Object.fromEntries(
            settings.templates.map((tpl) => [
              tpl.template_name,
              tpl.template_name === selectedTemplate.template_name
                ? {
                    allow_root: tpl.allow_root ?? null,
                    allow_internet: tpl.allow_internet ?? null,
                    [key]: allowed ? null : false,
                  }
                : { allow_root: tpl.allow_root ?? null, allow_internet: tpl.allow_internet ?? null },
            ]),
          ),
        },
      });
      notify(t.policySaved, 'success');
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.policySaveFailed, 'error');
    } finally {
      setSavingPolicy(false);
    }
  }

  async function applyPolicy() {
    setApplying(true);
    try {
      const result = await courseWorkspacesClient.applyPolicy({ courseId });
      const skipped = result.outcomes.filter((o) => !o.success).length;
      notify(
        t.applied(result.succeeded) + (skipped ? t.appliedSkipped(skipped) : ''),
        'success',
      );
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.applyFailed, 'error');
    } finally {
      setApplying(false);
    }
  }

  async function provision() {
    if (!effectiveTemplate || selected.size === 0) return;
    setProvisioning(true);
    setOutcomes(null);
    try {
      const result = await courseWorkspacesClient.provisionStudents({
        courseId,
        body: {
          template_name: effectiveTemplate,
          course_member_ids: [...selected],
          home_mode: homeMode,
          label: label.trim() || null,
        },
      });
      setOutcomes(result.outcomes);
      notify(
        t.provisioned(result.succeeded) + (result.failed > 0 ? t.provisionedFailed(result.failed) : ''),
        result.failed > 0 ? 'error' : 'success',
      );
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.provisionFailed, 'error');
    } finally {
      setProvisioning(false);
    }
  }

  async function deleteWorkspace(username: string | null | undefined, workspaceName: string, key: string) {
    if (!username) return;
    if (armedDelete !== key) {
      setArmedDelete(key);
      return;
    }
    setArmedDelete(null);
    setDeleting(key);
    try {
      await courseWorkspacesClient.deleteStudentWorkspace({ courseId, username, workspaceName });
      notify(t.deleted, 'success');
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : t.deleteFailed, 'error');
    } finally {
      setDeleting(null);
    }
  }

  const outcomeByMember = useMemo(
    () => new Map((outcomes ?? []).map((o) => [o.course_member_id, o])),
    [outcomes],
  );

  return (
    <ListPageLayout>
      <PageHeader
        breadcrumbs={crumbs}
        title={t.title}
        subtitle={t.subtitle}
      />

      <ErrorBanner>{error}</ErrorBanner>

      {loading ? (
        <ListLoading>{t.loading}</ListLoading>
      ) : (
        <ScrollArea>
          {!provisionAllowed ? (
            <div className="rounded-lg border border-warn-line bg-warn-wash p-4 text-sm text-warn-text">
              {t.notEnabled}
            </div>
          ) : templates.length === 0 ? (
            <div className="rounded-lg border border-warn-line bg-warn-wash p-4 text-sm text-warn-text">
              {t.noTemplates}
            </div>
          ) : (
            <>
            {canManage && selectedTemplate && (
              <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
                <div>
                  <h2 className="text-lg font-semibold text-fg">
                    {t.rootInternetFor(selectedTemplate.display_name || selectedTemplate.template_name)}
                  </h2>
                  <p className="text-sm text-muted mt-1">
                    {t.policyIntro}
                  </p>
                </div>

                <div className="flex flex-wrap gap-x-6 gap-y-2">
                  {([
                    ['allow_root', t.root, selectedTemplate.template_allow_root, selectedTemplate.allow_root],
                    ['allow_internet', t.internet, selectedTemplate.template_allow_internet, selectedTemplate.allow_internet],
                  ] as const).map(([key, label, ceiling, courseValue]) => (
                    <label
                      key={key}
                      className={`flex items-center gap-2 text-sm ${ceiling ? 'text-body' : 'text-subtle'}`}
                      title={ceiling ? undefined : t.templateDenies}
                    >
                      <input
                        type="checkbox"
                        disabled={!ceiling || savingPolicy}
                        checked={ceiling && courseValue !== false}
                        onChange={(event) => savePolicy(key, event.target.checked)}
                      />
                      {label}
                      {!ceiling && <span className="text-xs">{t.offForTemplate}</span>}
                    </label>
                  ))}
                </div>

                <div className="flex items-center gap-3">
                  <Button variant="secondary" onClick={applyPolicy} loading={applying}
                          loadingLabel={t.applying}>
                    {t.applyRunning}
                  </Button>
                  <span className="text-xs text-muted">
                    {t.applyHint}
                  </span>
                </div>
              </div>
            )}

            <div className="bg-surface rounded-lg border border-rule p-5 space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-fg">{t.provisionTitle}</h2>
                <p className="text-sm text-muted mt-1">
                  {t.provisionIntro}
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label htmlFor="sw-template" className="block text-xs font-medium text-body mb-1">
                    {t.template}
                  </label>
                  <select
                    id="sw-template"
                    value={effectiveTemplate}
                    onChange={(event) => setTemplate(event.target.value)}
                    className={inputCls}
                  >
                    {templates.map((tpl) => (
                      <option
                        key={tpl.template_name}
                        value={tpl.template_name}
                        // Listed but unpickable: the course asks for it, so
                        // hiding it would look like the course lost a template.
                        disabled={tpl.exists_in_coder === false}
                      >
                        {tpl.display_name || tpl.template_name}
                        {tpl.exists_in_coder === false ? t.notSetUp : ''}
                      </option>
                    ))}
                  </select>
                  {selectedTemplate && !selectedIsDeployable && (
                    <p className="mt-1 text-xs text-warn-text">
                      {t.notDeployable}
                    </p>
                  )}
                  {selectedTemplate && (
                    // Read-only: the policy is set by a workspace maintainer,
                    // per template and per course. Shown here so a lecturer
                    // knows what the students they provision for will get.
                    <p className="mt-1 text-xs text-muted">
                      {t.studentsGet}{' '}
                      <span className="font-medium">
                        {selectedTemplate.effective_allow_root ? t.withRoot : t.noRoot}
                      </span>{' '}
                      {t.and}{' '}
                      <span className="font-medium">
                        {selectedTemplate.effective_allow_internet ? t.withInternet : t.noInternet}
                      </span>
                      .
                    </p>
                  )}
                </div>
                <div>
                  <span className="block text-xs font-medium text-body mb-1">{t.home}</span>
                  <div className="space-y-1 text-sm text-body">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="home-mode"
                        checked={homeMode === 'scratch'}
                        onChange={() => setHomeMode('scratch')}
                      />
                      {t.homeScratch}
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="home-mode"
                        checked={homeMode === 'shared'}
                        onChange={() => setHomeMode('shared')}
                      />
                      {t.homeShared}
                    </label>
                  </div>
                </div>
                <div>
                  <label htmlFor="sw-label" className="block text-xs font-medium text-body mb-1">
                    {t.label}
                  </label>
                  <input
                    id="sw-label"
                    value={label}
                    onChange={(event) => setLabel(event.target.value)}
                    placeholder="tmp"
                    maxLength={32}
                    className={inputCls}
                  />
                  <p className="text-xs text-muted mt-1">
                    {t.labelHint}
                  </p>
                </div>
              </div>

              <div className="max-h-80 overflow-y-auto scroll-slim rounded-lg border border-rule">
                <Table>
                  <Thead>
                    <tr>
                      <Th className="w-10">
                        <input
                          type="checkbox"
                          aria-label={t.selectAll}
                          checked={members.length > 0 && selected.size === members.length}
                          onChange={toggleAll}
                        />
                      </Th>
                      <Th>{t.member}</Th>
                      <Th>{t.role}</Th>
                      <Th>{t.lastRun}</Th>
                    </tr>
                  </Thead>
                  <Tbody>
                    {members.map((member) => {
                      const outcome = outcomeByMember.get(member.id);
                      return (
                        <Tr key={member.id} className="hover:bg-canvas">
                          <Td>
                            <input
                              type="checkbox"
                              aria-label={t.select(userName(member.user))}
                              checked={selected.has(member.id)}
                              onChange={() => toggleMember(member.id)}
                            />
                          </Td>
                          <Td className="text-sm text-fg">{userName(member.user)}</Td>
                          <Td className="text-xs text-muted">{member.course_role_id}</Td>
                          <Td className="text-xs">
                            {outcome ? (
                              outcome.success ? (
                                <span className="text-success-text">
                                  {t.provisionedName(outcome.workspace_name ?? '')}
                                </span>
                              ) : (
                                <span className="text-danger-text">{outcome.error}</span>
                              )
                            ) : (
                              <span className="text-subtle">—</span>
                            )}
                          </Td>
                        </Tr>
                      );
                    })}
                    {members.length === 0 && (
                      <Tr>
                        <Td colSpan={4} className="py-6 text-center text-sm text-muted">
                          {t.noMembers}
                        </Td>
                      </Tr>
                    )}
                  </Tbody>
                </Table>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  onClick={provision}
                  loading={provisioning}
                  loadingLabel={t.provisioning}
                  disabled={selected.size === 0 || !effectiveTemplate || !selectedIsDeployable}
                >
                  {t.provisionSelected(selected.size)}
                </Button>
                <span className="text-xs text-muted">
                  {t.provisionHint}
                </span>
              </div>
            </div>
            </>
          )}

          <div className="bg-surface rounded-lg border border-rule p-5 space-y-3">
            <div>
              <h2 className="text-lg font-semibold text-fg">{t.existingTitle}</h2>
              <p className="text-sm text-muted mt-1">
                {t.existingIntro}
              </p>
            </div>
            <Table>
              <Thead>
                <tr>
                  <Th>{t.student}</Th>
                  <Th>{t.workspace}</Th>
                  <Th>{t.template}</Th>
                  <Th>{t.homeCol}</Th>
                  <Th>{t.status}</Th>
                  <Th className="text-right">{t.actions}</Th>
                </tr>
              </Thead>
              <Tbody>
                {(data?.studentWorkspaces?.students ?? []).flatMap((entry) =>
                  entry.workspaces.map((w) => {
                    const key = `${w.owner_name}/${w.name}`;
                    const scratch = w.home_mode === 'scratch';
                    const canDelete = scratch || (settings?.can_manage ?? false);
                    return (
                      <Tr key={key} className="hover:bg-canvas">
                        <Td className="text-sm text-fg">{entry.full_name || entry.user_id}</Td>
                        <Td className="text-sm font-mono text-body">{w.name}</Td>
                        <Td className="text-sm text-body">
                          {w.template_display_name || w.template_name}
                        </Td>
                        <Td>
                          {scratch ? (
                            <span className="inline-flex items-center rounded bg-warn-wash px-2 py-0.5 text-xs font-medium text-warn-text">
                              {t.throwaway}
                            </span>
                          ) : (
                            <span className="text-xs text-muted">
                              {w.home_mode === 'shared' ? t.shared : '—'}
                            </span>
                          )}
                        </Td>
                        <Td>
                          <WorkspaceStatusBadge
                            status={w.latest_build_status}
                            transition={w.latest_build_transition}
                          />
                        </Td>
                        <Td>
                          <div className="flex justify-end">
                            {canDelete && (
                              <Button
                                size="xs"
                                variant={armedDelete === key ? 'danger' : 'dangerGhost'}
                                disabled={deleting !== null}
                                loading={deleting === key}
                                onClick={() => deleteWorkspace(w.owner_name, w.name, key)}
                              >
                                {armedDelete === key ? t.confirmDelete : t.delete}
                              </Button>
                            )}
                          </div>
                        </Td>
                      </Tr>
                    );
                  }),
                )}
                {(data?.studentWorkspaces?.students ?? []).length === 0 && (
                  <Tr>
                    <Td colSpan={6} className="py-6 text-center text-sm text-muted">
                      {t.noStudentWorkspaces}
                    </Td>
                  </Tr>
                )}
              </Tbody>
            </Table>
          </div>
        </ScrollArea>
      )}
    </ListPageLayout>
  );
}

export default function LecturerWorkspacesPage() {
  const courseId = useParams().id as string;
  const t = COPY[useUiLanguage()];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { courseHasAtLeast } = usePermissions();

  if (!authLoading && isAuthenticated && !courseHasAtLeast(courseId, '_lecturer')) {
    return (
      <Forbidden
        message={t.forbidden}
        backLink={`/courses/${courseId}`}
        backText={t.backToCourse}
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <LecturerWorkspacesContent />
    </AuthenticatedLayout>
  );
}
