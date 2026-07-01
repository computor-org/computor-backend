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
import type { UserList } from 'types/generated';
import { assignableRoles, courseRoleLabel, highestCourseRole } from '@/src/utils/courseRoles';

const PAGE_SIZE = 10;
const membersClient = new CourseMembersClient();
const importClient = new CourseMemberImportClient();
const usersClient = new UsersClient();
const coursesClient = new CoursesClient();

type AddTab = 'list' | 'email';

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
  const roleOptions = assignableRoles(ceiling);
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

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: courseLabel, href: `/courses/${courseId}` },
            { label: 'Members', href: `/courses/${courseId}/members` },
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
          </nav>
        </div>

        {tab === 'list' ? (
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
        ) : (
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

            {importError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{importError}</div>
            )}
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
      </div>
    </AuthenticatedLayout>
  );
}
