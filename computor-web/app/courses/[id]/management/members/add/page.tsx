'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import { Field, inputCls } from '@/src/components/FormPanel';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { CourseMemberImportClient } from '@/src/generated/clients/CourseMemberImportClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { CourseMemberImportRow, UserList } from 'types/generated';
import { assignableRoles, courseRoleLabel, highestCourseRole, maxAssignableRole } from '@/src/utils/courseRoles';

const PAGE_SIZE = 10;
const membersClient = new CourseMembersClient();
const importClient = new CourseMemberImportClient();
const usersClient = new UsersClient();
const coursesClient = new CoursesClient();

type AddTab = 'list' | 'email' | 'file';

function userName(u: UserList): string {
  const name = `${u.given_name ?? ''} ${u.family_name ?? ''}`.trim();
  return name || u.email || u.id;
}

export default function AddCourseMembersPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseRoles, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');
  const ceiling = isAdmin || isOrganizationManager ? '_owner' : highestCourseRole(courseRoles[courseId]);
  // Roles this user may grant when adding/importing members. Lecturers (and
  // below) are capped at _student; only maintainers/owners/org-managers may
  // grant a higher role. Mirrors the backend assignment ceiling.
  const roleOptions = assignableRoles(maxAssignableRole(ceiling));
  const defaultRole = roleOptions[0] ?? '_student';

  const [tab, setTab] = useState<AddTab>('list');

  // ---- users table (pick an existing user) -------------------------------
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [rowRole, setRowRole] = useState<Record<string, string>>({});
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [rowError, setRowError] = useState<Record<string, string>>({});
  const [addingId, setAddingId] = useState<string | null>(null);

  // Debounce the search box; reset to the first page on a new query.
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data: courseData } = useResource(
    () => coursesClient.getCoursesCoursesIdGet({ id: courseId }).catch(() => null),
    [courseId],
    { enabled: canManage },
  );
  const courseLabel = courseData?.title || courseData?.path || 'Course';

  const { data: usersData, loading: usersLoading, error: usersError } = useResource(
    () =>
      usersClient.listUsersUsersGet({
        search: search || undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    [search, page],
    { enabled: canManage },
  );
  const users = usersData ?? [];
  const hasNext = users.length === PAGE_SIZE;

  // Current members are shown on the roster page, so hide them from the picker.
  // Fetched once from the course-member API (this is the members feature — no
  // need to leak course concerns into the generic /users endpoint).
  const { data: memberData } = useResource(
    () => membersClient.listCourseMembersCourseMembersGet({ courseId, limit: 2000 }),
    [courseId],
    { enabled: canManage },
  );
  const memberIds = useMemo(
    () => new Set((memberData ?? []).map((m) => m.user_id)),
    [memberData],
  );
  // Keep users added in this session visible (with "Added ✓") — memberData
  // isn't refetched after an add.
  const visibleUsers = users.filter((u) => added.has(u.id) || !memberIds.has(u.id));

  async function addUser(u: UserList) {
    const role = rowRole[u.id] ?? defaultRole;
    setAddingId(u.id);
    setRowError((prev) => ({ ...prev, [u.id]: '' }));
    try {
      await membersClient.createCourseMembersCourseMembersPost({
        body: { user_id: u.id, course_id: courseId, course_role_id: role },
      });
      setAdded((prev) => new Set(prev).add(u.id));
    } catch (e) {
      setRowError((prev) => ({
        ...prev,
        [u.id]: e instanceof Error ? e.message : 'Failed to add',
      }));
    } finally {
      setAddingId(null);
    }
  }

  // ---- add by email (creates the user if unknown) ------------------------
  const [email, setEmail] = useState('');
  const [givenName, setGivenName] = useState('');
  const [familyName, setFamilyName] = useState('');
  const [emailRole, setEmailRole] = useState<string>(defaultRole);
  const [groupTitle, setGroupTitle] = useState('');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importMsg, setImportMsg] = useState<string | null>(null);

  async function importByEmail() {
    setImporting(true);
    setImportError(null);
    setImportMsg(null);
    try {
      const res = await importClient.importMemberCourseMemberImportCourseIdPost({
        courseId,
        body: {
          email: email.trim(),
          given_name: givenName.trim() || undefined,
          family_name: familyName.trim() || undefined,
          course_role_id: emailRole,
          course_group_title: groupTitle.trim() || undefined,
          create_missing_group: true,
        },
      });
      if (res.success) {
        setImportMsg(
          res.workflow_id
            ? `${email.trim()} added — repository provisioning started.`
            : `${email.trim()} added to the course.`,
        );
        setEmail('');
        setGivenName('');
        setFamilyName('');
        setGroupTitle('');
      } else {
        setImportError(res.message || 'Import failed.');
      }
    } catch (e) {
      setImportError(e instanceof Error ? e.message : 'Import failed.');
    } finally {
      setImporting(false);
    }
  }

  // ---- import from a file (server parses → review/edit → import per row) --
  const [fileParsing, setFileParsing] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [parsedRows, setParsedRows] = useState<CourseMemberImportRow[]>([]);
  const [rowSel, setRowSel] = useState<Record<number, boolean>>({});
  const [rowRoleFile, setRowRoleFile] = useState<Record<number, string>>({});
  const [rowGroupFile, setRowGroupFile] = useState<Record<number, string>>({});
  const [fileResults, setFileResults] = useState<Record<number, { ok: boolean; message?: string }>>({});
  const [fileImporting, setFileImporting] = useState(false);
  const [fileSummary, setFileSummary] = useState<string | null>(null);

  async function fileToBase64(file: File): Promise<string> {
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }

  async function handleFile(file: File) {
    setFileError(null);
    setFileSummary(null);
    setParsedRows([]);
    setFileResults({});
    setFileParsing(true);
    try {
      const res = await importClient.parseMemberFileCourseMemberImportParseCourseIdPost({
        courseId,
        body: { filename: file.name, content_base64: await fileToBase64(file) },
      });
      const rows = res.rows ?? [];
      const sel: Record<number, boolean> = {};
      const roles: Record<number, string> = {};
      const groups: Record<number, string> = {};
      rows.forEach((r, i) => {
        sel[i] = true;
        roles[i] =
          r.course_role_id && roleOptions.includes(r.course_role_id as never)
            ? r.course_role_id
            : defaultRole;
        groups[i] = r.course_group_title ?? '';
      });
      setParsedRows(rows);
      setRowSel(sel);
      setRowRoleFile(roles);
      setRowGroupFile(groups);
      if (!rows.length) setFileError('No members with an email address were found in the file.');
    } catch (e) {
      setFileError(e instanceof Error ? e.message : 'Failed to parse file.');
    } finally {
      setFileParsing(false);
    }
  }

  async function importParsed() {
    setFileImporting(true);
    setFileSummary(null);
    const results: Record<number, { ok: boolean; message?: string }> = {};
    let ok = 0;
    let fail = 0;
    for (let i = 0; i < parsedRows.length; i++) {
      if (!rowSel[i]) continue;
      const r = parsedRows[i];
      try {
        const res = await importClient.importMemberCourseMemberImportCourseIdPost({
          courseId,
          body: {
            email: r.email,
            given_name: r.given_name ?? undefined,
            family_name: r.family_name ?? undefined,
            course_role_id: rowRoleFile[i] ?? defaultRole,
            course_group_title: rowGroupFile[i]?.trim() || undefined,
            create_missing_group: true,
          },
        });
        if (res.success) {
          results[i] = { ok: true };
          ok++;
        } else {
          results[i] = { ok: false, message: res.message ?? 'Failed' };
          fail++;
        }
      } catch (e) {
        results[i] = { ok: false, message: e instanceof Error ? e.message : 'Failed' };
        fail++;
      }
      setFileResults({ ...results });
    }
    setFileImporting(false);
    setFileSummary(`Imported ${ok}${fail ? `, ${fail} failed` : ''}.`);
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden
        message="You need lecturer access (or higher) on this course to add members."
        backLink={`/courses/${courseId}`}
        backText="Back to course"
      />
    );
  }

  const tabClass = (active: boolean) =>
    `py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
      active ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
    }`;

  const selectedFileCount = parsedRows.filter((_, i) => rowSel[i]).length;

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: courseLabel, href: `/courses/${courseId}` },
            { label: 'Course Members', href: `/courses/${courseId}/management/members` },
            { label: 'Add' },
          ]}
          title="Add members"
          subtitle="Add existing users from the list, or invite someone new by email."
        />

        {/* Tabs: the two add flows are mutually exclusive, so show one at a time. */}
        <div className="border-b border-gray-200">
          <nav className="flex gap-6">
            <button type="button" onClick={() => setTab('list')} className={tabClass(tab === 'list')}>
              From user list
            </button>
            <button type="button" onClick={() => setTab('email')} className={tabClass(tab === 'email')}>
              By email
            </button>
            <button type="button" onClick={() => setTab('file')} className={tabClass(tab === 'file')}>
              Import file
            </button>
          </nav>
        </div>

        {tab === 'list' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              You can only see users your permissions allow. Users already in the course are hidden — pick a
              role and add them.
            </p>
            <input
              type="text"
              placeholder="Search by name or email…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />

            <ErrorBanner>{usersError}</ErrorBanner>

            {usersLoading ? (
              <div className="text-gray-500 py-8 text-center">Loading users…</div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {visibleUsers.map((u) => {
                      const isAdded = added.has(u.id);
                      return (
                        <tr key={u.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <div className="font-medium text-gray-900 text-sm">{userName(u)}</div>
                            <div className="text-xs text-gray-500">{u.email ?? '—'}</div>
                            {rowError[u.id] && (
                              <div className="text-xs text-red-600 mt-1">{rowError[u.id]}</div>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <select
                              value={rowRole[u.id] ?? defaultRole}
                              disabled={isAdded}
                              onChange={(e) => setRowRole((prev) => ({ ...prev, [u.id]: e.target.value }))}
                              className="px-2 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
                            >
                              {roleOptions.map((r) => (
                                <option key={r} value={r}>
                                  {courseRoleLabel(r)}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="px-4 py-3 text-right">
                            {isAdded ? (
                              <span className="text-sm text-green-700">Added ✓</span>
                            ) : (
                              <button
                                onClick={() => addUser(u)}
                                disabled={addingId === u.id}
                                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                              >
                                {addingId === u.id ? 'Adding…' : 'Add'}
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                    {visibleUsers.length === 0 && (
                      <tr>
                        <td colSpan={3} className="px-4 py-8 text-center text-sm text-gray-500">
                          No users to add.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Page {page + 1}</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0 || usersLoading}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!hasNext || usersLoading}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}

        {tab === 'email' && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              importByEmail();
            }}
            className="bg-white border border-gray-200 rounded-lg p-6 space-y-4 max-w-lg"
          >
            <p className="text-sm text-gray-500">
              Adds the user with this email, creating the account if it does not exist yet. Use this for people
              not yet in the system.
            </p>

            <ErrorBanner>{importError}</ErrorBanner>
            {importMsg && (
              <div className="p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">{importMsg}</div>
            )}

            <Field label="Email" required>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputCls}
                placeholder="person@example.org"
              />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Given name">
                <input value={givenName} onChange={(e) => setGivenName(e.target.value)} className={inputCls} />
              </Field>
              <Field label="Family name">
                <input value={familyName} onChange={(e) => setFamilyName(e.target.value)} className={inputCls} />
              </Field>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Role" required>
                <select value={emailRole} onChange={(e) => setEmailRole(e.target.value)} className={inputCls}>
                  {roleOptions.map((r) => (
                    <option key={r} value={r}>
                      {courseRoleLabel(r)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Group" hint="Optional. Created if it does not exist yet.">
                <input value={groupTitle} onChange={(e) => setGroupTitle(e.target.value)} className={inputCls} />
              </Field>
            </div>

            <button
              type="submit"
              disabled={importing || !email.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {importing ? 'Adding…' : 'Add by email'}
            </button>
          </form>
        )}

        {tab === 'file' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Upload a CSV, JSON, Excel (.xlsx) or Excel-XML student list. Review and adjust the rows, then
              import the ones you want. Existing members are updated rather than duplicated.
            </p>
            <input
              type="file"
              accept=".csv,.tsv,.txt,.json,.xlsx,.xls,.xml"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
                e.target.value = '';
              }}
              className="block text-sm text-gray-500 file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-blue-700"
            />

            <ErrorBanner>{fileError}</ErrorBanner>

            {fileParsing ? (
              <div className="text-gray-500 py-8 text-center">Parsing file…</div>
            ) : parsedRows.length > 0 ? (
              <>
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-3 w-8" />
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Group</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {parsedRows.map((r, i) => {
                        const res = fileResults[i];
                        const name = `${r.given_name ?? ''} ${r.family_name ?? ''}`.trim() || r.email;
                        return (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="px-3 py-3">
                              <input
                                type="checkbox"
                                checked={!!rowSel[i]}
                                onChange={(e) => setRowSel((p) => ({ ...p, [i]: e.target.checked }))}
                              />
                            </td>
                            <td className="px-4 py-3">
                              <div className="font-medium text-gray-900 text-sm">{name}</div>
                              <div className="text-xs text-gray-500">{r.email}</div>
                            </td>
                            <td className="px-4 py-3">
                              <select
                                value={rowRoleFile[i] ?? defaultRole}
                                onChange={(e) => setRowRoleFile((p) => ({ ...p, [i]: e.target.value }))}
                                className="px-2 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              >
                                {roleOptions.map((role) => (
                                  <option key={role} value={role}>
                                    {courseRoleLabel(role)}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td className="px-4 py-3">
                              <input
                                value={rowGroupFile[i] ?? ''}
                                onChange={(e) => setRowGroupFile((p) => ({ ...p, [i]: e.target.value }))}
                                placeholder="—"
                                className="w-32 px-2 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm">
                              {res ? (
                                res.ok ? (
                                  <span className="text-green-700">Added ✓</span>
                                ) : (
                                  <span className="text-red-600" title={res.message}>Failed</span>
                                )
                              ) : (
                                <span className="text-gray-400">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={importParsed}
                    disabled={fileImporting || selectedFileCount === 0}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {fileImporting ? 'Importing…' : `Import ${selectedFileCount} selected`}
                  </button>
                  {fileSummary && <span className="text-sm text-gray-600">{fileSummary}</span>}
                </div>
              </>
            ) : null}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
