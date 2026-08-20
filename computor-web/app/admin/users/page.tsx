'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { Table, Thead, Tbody, Th } from '@/src/components/ui/Table';

const PAGE_SIZE = 50;
const usersClient = new UsersClient();

export default function UsersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isUserManager } = usePermissions();
  const canManage = isAdmin || isUserManager;

  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [page, setPage] = useState(0);

  // Debounce the search box; reset to the first page on a new query.
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data, loading, error } = useResource(
    () =>
      usersClient.listUsersUsersGet({
        archived: showArchived ? true : undefined,
        search: search || undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    [showArchived, search, page],
    { enabled: canManage },
  );
  const users = data ?? [];
  const hasNext = users.length === PAGE_SIZE;

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Access denied. Requires admin or _user_manager role." />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Users' }]}
          title="Users"
          actions={
            <Link href="/admin/users/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
              New User
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Search by email or name…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full max-w-md px-3 py-2 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent"
          />
          <label className="flex items-center gap-2 text-sm text-muted cursor-pointer select-none whitespace-nowrap">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => {
                setShowArchived(e.target.checked);
                setPage(0);
              }}
              className="rounded"
            />
            Show archived
          </label>
        </div>

        {loading ? (
          <ListLoading>Loading users…</ListLoading>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <tr>
                  <Th>User</Th>
                  <Th>Status</Th>
                  <Th>Created</Th>
                  <th className="px-4 py-3" />
                </tr>
              </Thead>
              <Tbody>
                {users.map((u) => (
                  <tr key={u.id} className={`hover:bg-canvas ${u.archived_at ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3">
                      <Link href={`/admin/users/${u.id}`} className="block group">
                        <div className="font-medium text-fg text-sm group-hover:text-accent-text">{u.email ?? '—'}</div>
                        <div className="text-xs text-muted">{u.given_name} {u.family_name}</div>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Badge color={u.banned_at ? 'red' : u.archived_at ? 'gray' : 'green'}>
                        {u.banned_at ? 'Banned' : u.archived_at ? 'Archived' : 'Active'}
                      </Badge>
                      {u.is_service && <Badge color="yellow" className="ml-1">Service</Badge>}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/admin/users/${u.id}`} className="text-sm text-accent-text hover:underline">Manage →</Link>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted">No users found</td>
                  </tr>
                )}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}

        {/* Pager — total count isn't exposed via the client, so Next is
            enabled whenever a full page came back. */}
        <div className="shrink-0 flex items-center justify-between">
          <span className="text-sm text-muted">Page {page + 1}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="px-3 py-1.5 text-sm border border-rule-strong rounded-lg hover:bg-canvas disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext || loading}
              className="px-3 py-1.5 text-sm border border-rule-strong rounded-lg hover:bg-canvas disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
