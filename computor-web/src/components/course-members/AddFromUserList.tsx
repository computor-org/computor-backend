'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useResource } from '@/src/hooks/useResource';
import ErrorBanner from '@/src/components/ErrorBanner';
import RoleSelect from '@/src/components/course-members/RoleSelect';
import GroupSelect from '@/src/components/course-members/GroupSelect';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { CourseGroupList, UserList } from 'types/generated';
import type { CourseRoleId } from '@/src/utils/courseRoles';
import { Table, Tbody, Th } from '@/src/components/ui/Table';

const PAGE_SIZE = 10;
const membersClient = new CourseMembersClient();
const usersClient = new UsersClient();

function userName(u: UserList): string {
  const name = `${u.given_name ?? ''} ${u.family_name ?? ''}`.trim();
  return name || u.email || u.id;
}

export default function AddFromUserList({
  courseId,
  roleOptions,
  defaultRole,
  groups,
  canManage,
}: {
  courseId: string;
  roleOptions: CourseRoleId[];
  defaultRole: string;
  groups: CourseGroupList[];
  canManage: boolean;
}) {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [rowRole, setRowRole] = useState<Record<string, string>>({});
  const [rowGroup, setRowGroup] = useState<Record<string, string>>({});
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
    const groupId = rowGroup[u.id] || '';
    // Students must belong to a group (enforced by a DB check constraint). Catch
    // it here with a clear message instead of surfacing the raw constraint error.
    if (role === '_student' && !groupId) {
      setRowError((prev) => ({
        ...prev,
        [u.id]: groups.length
          ? 'Pick a group — students must be assigned to one.'
          : 'Create a course group first — students must be assigned to one.',
      }));
      return;
    }
    setAddingId(u.id);
    setRowError((prev) => ({ ...prev, [u.id]: '' }));
    try {
      await membersClient.createCourseMembersCourseMembersPost({
        body: {
          user_id: u.id,
          course_id: courseId,
          course_role_id: role,
          course_group_id: groupId || null,
        },
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

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">
        You can only see users your permissions allow. Users already in the course are hidden — pick a
        role and add them. Students must be assigned to a group.
      </p>
      {groups.length === 0 && (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          This course has no groups yet, so students cannot be added.{' '}
          <Link
            href={`/courses/${courseId}/management/groups/create`}
            className="font-medium text-amber-800 underline hover:no-underline"
          >
            Create a group
          </Link>{' '}
          first.
        </p>
      )}
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
          <Table>
            <thead className="bg-gray-50">
              <tr>
                <Th>User</Th>
                <Th>Role</Th>
                <Th>Group</Th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <Tbody>
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
                      <RoleSelect
                        value={rowRole[u.id] ?? defaultRole}
                        disabled={isAdded}
                        onChange={(value) => setRowRole((prev) => ({ ...prev, [u.id]: value }))}
                        options={roleOptions}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <GroupSelect
                        value={rowGroup[u.id] ?? ''}
                        disabled={isAdded}
                        onChange={(value) => setRowGroup((prev) => ({ ...prev, [u.id]: value }))}
                        groups={groups}
                      />
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
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                    No users to add.
                  </td>
                </tr>
              )}
            </Tbody>
          </Table>
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
  );
}
