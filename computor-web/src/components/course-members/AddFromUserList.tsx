'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { useResource } from '@/src/hooks/useResource';
import ErrorBanner from '@/src/components/ErrorBanner';
import RoleSelect from '@/src/components/course-members/RoleSelect';
import GroupSelect from '@/src/components/course-members/GroupSelect';
import { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { CourseGroupList, UserList } from 'types/generated';
import type { CourseRoleId } from '@/src/utils/courseRoles';
import { Table, Tbody, Th } from '@/src/components/ui/Table';
import Button from '@/src/components/ui/Button';

const PAGE_SIZE = 10;
const membersClient = new CourseMembersClient();
const usersClient = new UsersClient();

const COPY = {
  de: {
    pickGroup: 'Wähle eine Gruppe aus, Studierende müssen einer Gruppe zugeordnet sein.',
    createGroupFirst: 'Lege zuerst eine Kursgruppe an, Studierende müssen einer Gruppe zugeordnet sein.',
    addFailed: 'Hinzufügen fehlgeschlagen',
    intro: 'Du siehst nur Nutzer, die deine Berechtigungen zulassen. Nutzer, die schon im Kurs sind, werden ausgeblendet. Wähle eine Rolle und füge sie hinzu. Studierende müssen einer Gruppe zugeordnet sein.',
    noGroups: 'Dieser Kurs hat noch keine Gruppen, daher können keine Studierenden hinzugefügt werden.',
    createGroup: 'Lege zuerst eine Gruppe an',
    createGroupSuffix: '.',
    search: 'Nach Name oder E-Mail suchen …',
    loading: 'Nutzer werden geladen …',
    user: 'Nutzer',
    role: 'Rolle',
    group: 'Gruppe',
    added: 'Hinzugefügt ✓',
    adding: 'Wird hinzugefügt …',
    add: 'Hinzufügen',
    empty: 'Keine Nutzer zum Hinzufügen.',
    page: (n: number) => `Seite ${n}`,
    previous: 'Zurück',
    next: 'Weiter',
  },
  en: {
    pickGroup: 'Pick a group — students must be assigned to one.',
    createGroupFirst: 'Create a course group first — students must be assigned to one.',
    addFailed: 'Failed to add',
    intro: 'You can only see users your permissions allow. Users already in the course are hidden — pick a role and add them. Students must be assigned to a group.',
    noGroups: 'This course has no groups yet, so students cannot be added.',
    createGroup: 'Create a group',
    createGroupSuffix: 'first.',
    search: 'Search by name or email…',
    loading: 'Loading users…',
    user: 'User',
    role: 'Role',
    group: 'Group',
    added: 'Added ✓',
    adding: 'Adding…',
    add: 'Add',
    empty: 'No users to add.',
    page: (n: number) => `Page ${n}`,
    previous: 'Previous',
    next: 'Next',
  },
};

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
  const t = COPY[useUiLanguage()];
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
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
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
          ? t.pickGroup
          : t.createGroupFirst,
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
        [u.id]: e instanceof Error ? e.message : t.addFailed,
      }));
    } finally {
      setAddingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        {t.intro}
      </p>
      {groups.length === 0 && (
        <p className="text-sm text-warn-text bg-warn-wash border border-warn-line rounded-lg px-3 py-2">
          {t.noGroups}{' '}
          <Link
            href={`/courses/${courseId}/lecturer/groups/create`}
            className="font-medium text-warn-text underline hover:no-underline"
          >
            {t.createGroup}
          </Link>{' '}
          {t.createGroupSuffix}
        </p>
      )}
      <input
        type="text"
        placeholder={t.search}
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        className="w-full max-w-md px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
      />

      <ErrorBanner>{usersError}</ErrorBanner>

      {usersLoading ? (
        <div className="text-muted py-8 text-center">{t.loading}</div>
      ) : (
        <div className="bg-surface border border-rule rounded-lg overflow-hidden">
          <Table>
            <thead className="bg-canvas">
              <tr>
                <Th>{t.user}</Th>
                <Th>{t.role}</Th>
                <Th>{t.group}</Th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <Tbody>
              {visibleUsers.map((u) => {
                const isAdded = added.has(u.id);
                return (
                  <tr key={u.id} className="hover:bg-canvas">
                    <td className="px-4 py-3">
                      <div className="font-medium text-fg text-sm">{userName(u)}</div>
                      <div className="text-xs text-muted">{u.email ?? '—'}</div>
                      {rowError[u.id] && (
                        <div className="text-xs text-danger-text mt-1">{rowError[u.id]}</div>
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
                        <span className="text-sm text-success-text">{t.added}</span>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() => addUser(u)}
                          loading={addingId === u.id}
                          loadingLabel={t.adding}
                        >
                          {t.add}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {visibleUsers.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted">
                    {t.empty}
                  </td>
                </tr>
              )}
            </Tbody>
          </Table>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">{t.page(page + 1)}</span>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || usersLoading}
          >
            {t.previous}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasNext || usersLoading}
          >
            {t.next}
          </Button>
        </div>
      </div>
    </div>
  );
}
