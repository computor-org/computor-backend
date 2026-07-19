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
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import { useNotify } from '@/src/contexts/NotificationContext';
import { inputCls } from '@/src/components/ui/tokens';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CourseWorkspacesClient } from '@/src/clients/CourseWorkspacesClient';
import type { StudentWorkspaceProvisionOutcome } from '@/src/types/workspaces';

const membersClient = new CourseMembersClient();
const courseWorkspacesClient = new CourseWorkspacesClient();

function memberName(user?: { given_name?: string | null; family_name?: string | null; email?: string | null } | null): string {
  const name = [user?.given_name, user?.family_name].filter(Boolean).join(' ');
  return name || user?.email || 'Unknown';
}

function LecturerWorkspacesContent() {
  const courseId = useParams().id as string;
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
        .sort((a, b) => memberName(a.user).localeCompare(memberName(b.user))),
    [data],
  );
  const templates = (settings?.templates ?? []).filter((t) => t.enabled);
  const provisionAllowed = (settings?.lecturer_provision_enabled ?? false) || (settings?.can_manage ?? false);
  const effectiveTemplate = template || templates[0]?.template_name || '';

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
        `${result.succeeded} workspace(s) provisioned` +
          (result.failed > 0 ? `, ${result.failed} failed` : ''),
        result.failed > 0 ? 'error' : 'success',
      );
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Provisioning failed', 'error');
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
      notify('Workspace deleted', 'success');
      await reload();
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Failed to delete workspace', 'error');
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
        breadcrumbs={[
          { label: 'Courses', href: '/courses' },
          { label: 'Course', href: `/courses/${courseId}` },
          { label: 'Lecturer View', href: `/courses/${courseId}/lecturer` },
          { label: 'Workspaces' },
        ]}
        title="Student workspaces"
        subtitle="Provision (throwaway) workspaces for your students and manage the ones that exist"
      />

      <ErrorBanner>{error}</ErrorBanner>

      {loading ? (
        <ListLoading>Loading…</ListLoading>
      ) : (
        <ScrollArea className="space-y-6 pr-1">
          {!provisionAllowed ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              Lecturer provisioning is not enabled for this course. A workspace maintainer can
              enable it in the workspace administration area.
            </div>
          ) : templates.length === 0 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              This course has no workspace templates yet. A workspace maintainer can assign
              templates in the workspace administration area.
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Provision for students</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Creates one workspace per selected student. Students can open and start these,
                  but not provision new ones. A throwaway workspace uses its own scratch home
                  volume that is deleted together with the workspace — the student&apos;s regular
                  files stay untouched.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label htmlFor="sw-template" className="block text-xs font-medium text-gray-700 mb-1">
                    Template
                  </label>
                  <select
                    id="sw-template"
                    value={effectiveTemplate}
                    onChange={(event) => setTemplate(event.target.value)}
                    className={inputCls}
                  >
                    {templates.map((t) => (
                      <option key={t.template_name} value={t.template_name}>
                        {t.display_name || t.template_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <span className="block text-xs font-medium text-gray-700 mb-1">Home directory</span>
                  <div className="space-y-1 text-sm text-gray-700">
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="home-mode"
                        checked={homeMode === 'scratch'}
                        onChange={() => setHomeMode('scratch')}
                      />
                      Throwaway (deleted with the workspace)
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="home-mode"
                        checked={homeMode === 'shared'}
                        onChange={() => setHomeMode('shared')}
                      />
                      Usual home (shared across workspaces)
                    </label>
                  </div>
                </div>
                <div>
                  <label htmlFor="sw-label" className="block text-xs font-medium text-gray-700 mb-1">
                    Label
                  </label>
                  <input
                    id="sw-label"
                    value={label}
                    onChange={(event) => setLabel(event.target.value)}
                    placeholder="tmp"
                    maxLength={32}
                    className={inputCls}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Name suffix (e.g. &quot;exam1&quot;) — keeps these apart from the students&apos;
                    own workspaces.
                  </p>
                </div>
              </div>

              <div className="max-h-80 overflow-y-auto rounded-lg border border-gray-200">
                <Table>
                  <Thead>
                    <tr>
                      <Th className="w-10">
                        <input
                          type="checkbox"
                          aria-label="Select all members"
                          checked={members.length > 0 && selected.size === members.length}
                          onChange={toggleAll}
                        />
                      </Th>
                      <Th>Member</Th>
                      <Th>Role</Th>
                      <Th>Last run</Th>
                    </tr>
                  </Thead>
                  <Tbody>
                    {members.map((member) => {
                      const outcome = outcomeByMember.get(member.id);
                      return (
                        <Tr key={member.id} className="hover:bg-gray-50">
                          <Td>
                            <input
                              type="checkbox"
                              aria-label={`Select ${memberName(member.user)}`}
                              checked={selected.has(member.id)}
                              onChange={() => toggleMember(member.id)}
                            />
                          </Td>
                          <Td className="text-sm text-gray-900">{memberName(member.user)}</Td>
                          <Td className="text-xs text-gray-500">{member.course_role_id}</Td>
                          <Td className="text-xs">
                            {outcome ? (
                              outcome.success ? (
                                <span className="text-green-700">
                                  Provisioned {outcome.workspace_name}
                                </span>
                              ) : (
                                <span className="text-red-700">{outcome.error}</span>
                              )
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </Td>
                        </Tr>
                      );
                    })}
                    {members.length === 0 && (
                      <Tr>
                        <Td colSpan={4} className="py-6 text-center text-sm text-gray-500">
                          No course members.
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
                  loadingLabel="Provisioning…"
                  disabled={selected.size === 0 || !effectiveTemplate}
                >
                  Provision for {selected.size} selected
                </Button>
                <span className="text-xs text-gray-500">
                  Runs one at a time; failures are reported per student and never abort the batch.
                </span>
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Existing student workspaces</h2>
              <p className="text-sm text-gray-500 mt-1">
                Workspaces of course members on this course&apos;s templates. Throwaway
                (scratch-home) workspaces can be deleted here; shared-home workspaces are managed
                by workspace maintainers.
              </p>
            </div>
            <Table>
              <Thead>
                <tr>
                  <Th>Student</Th>
                  <Th>Workspace</Th>
                  <Th>Template</Th>
                  <Th>Home</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </Thead>
              <Tbody>
                {(data?.studentWorkspaces?.students ?? []).flatMap((entry) =>
                  entry.workspaces.map((w) => {
                    const key = `${w.owner_name}/${w.name}`;
                    const scratch = w.home_mode === 'scratch';
                    const canDelete = scratch || (settings?.can_manage ?? false);
                    return (
                      <Tr key={key} className="hover:bg-gray-50">
                        <Td className="text-sm text-gray-900">{entry.full_name || entry.user_id}</Td>
                        <Td className="text-sm font-mono text-gray-700">{w.name}</Td>
                        <Td className="text-sm text-gray-700">
                          {w.template_display_name || w.template_name}
                        </Td>
                        <Td>
                          {scratch ? (
                            <span className="inline-flex items-center rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                              Throwaway
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">
                              {w.home_mode === 'shared' ? 'Shared' : '—'}
                            </span>
                          )}
                        </Td>
                        <Td>
                          <WorkspaceStatusBadge
                            status={
                              w.latest_build_transition === 'stop'
                                ? 'stopped'
                                : w.latest_build_status
                            }
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
                                {armedDelete === key ? 'Confirm delete' : 'Delete'}
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
                    <Td colSpan={6} className="py-6 text-center text-sm text-gray-500">
                      No student workspaces on this course&apos;s templates.
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
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { courseHasAtLeast } = usePermissions();

  if (!authLoading && isAuthenticated && !courseHasAtLeast(courseId, '_lecturer')) {
    return (
      <Forbidden
        message="The workspace console requires the lecturer role for this course."
        backLink={`/courses/${courseId}`}
        backText="Back to course"
      />
    );
  }

  return (
    <AuthenticatedLayout>
      <LecturerWorkspacesContent />
    </AuthenticatedLayout>
  );
}
