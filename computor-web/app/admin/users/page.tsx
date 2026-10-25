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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDate } from '@/src/utils/locale';

const PAGE_SIZE = 50;
const usersClient = new UsersClient();

const COPY = {
  de: {
    forbidden: 'Zugriff verweigert. Erfordert die Rolle admin oder _user_manager.',
    title: 'Benutzer',
    newUser: 'Neuer Benutzer',
    searchPlaceholder: 'Nach E-Mail oder Name suchen…',
    showArchived: 'Archivierte anzeigen',
    loading: 'Benutzer werden geladen…',
    user: 'Benutzer',
    status: 'Status',
    created: 'Erstellt',
    banned: 'Gesperrt',
    archived: 'Archiviert',
    active: 'Aktiv',
    service: 'Dienst',
    manage: 'Verwalten →',
    empty: 'Keine Benutzer gefunden',
    page: (n: number) => `Seite ${n}`,
    previous: 'Zurück',
    next: 'Weiter',
  },
  en: {
    forbidden: 'Access denied. Requires admin or _user_manager role.',
    title: 'Users',
    newUser: 'New User',
    searchPlaceholder: 'Search by email or name…',
    showArchived: 'Show archived',
    loading: 'Loading users…',
    user: 'User',
    status: 'Status',
    created: 'Created',
    banned: 'Banned',
    archived: 'Archived',
    active: 'Active',
    service: 'Service',
    manage: 'Manage →',
    empty: 'No users found',
    page: (n: number) => `Page ${n}`,
    previous: 'Previous',
    next: 'Next',
  },
};

export default function UsersPage() {
  const language = useUiLanguage();
  const t = COPY[language];
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
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.title }]}
          title={t.title}
          actions={
            <Link href="/admin/users/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
              {t.newUser}
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder={t.searchPlaceholder}
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
            {t.showArchived}
          </label>
        </div>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <tr>
                  <Th>{t.user}</Th>
                  <Th>{t.status}</Th>
                  <Th>{t.created}</Th>
                  <th className="px-4 py-3" />
                </tr>
              </Thead>
              <Tbody>
                {users.map((u) => (
                  // Archived rows read quieter through the muted address, not
                  // `opacity` on the <tr>: opacity composites the whole subtree,
                  // so it also faded the row's "Manage" link — the one action an
                  // archived user's row is there for. The Archived badge already
                  // carries the state.
                  <tr key={u.id} className="hover:bg-canvas">
                    <td className="px-4 py-3">
                      <Link href={`/admin/users/${u.id}`} className="block group">
                        <div className={`font-medium text-sm group-hover:text-accent-text ${u.archived_at ? 'text-muted' : 'text-fg'}`}>{u.email ?? '—'}</div>
                        <div className="text-xs text-muted">{u.given_name} {u.family_name}</div>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Badge color={u.banned_at ? 'red' : u.archived_at ? 'gray' : 'green'}>
                        {u.banned_at ? t.banned : u.archived_at ? t.archived : t.active}
                      </Badge>
                      {u.is_service && <Badge color="yellow" className="ml-1">{t.service}</Badge>}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted">{formatDate(u.created_at, language)}</td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/admin/users/${u.id}`} className="text-sm text-accent-text hover:underline">{t.manage}</Link>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted">{t.empty}</td>
                  </tr>
                )}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}

        {/* Pager — total count isn't exposed via the client, so Next is
            enabled whenever a full page came back. */}
        <div className="shrink-0 flex items-center justify-between">
          <span className="text-sm text-muted">{t.page(page + 1)}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="px-3 py-1.5 text-sm border border-rule-strong rounded-lg hover:bg-canvas disabled:opacity-50"
            >
              {t.previous}
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext || loading}
              className="px-3 py-1.5 text-sm border border-rule-strong rounded-lg hover:bg-canvas disabled:opacity-50"
            >
              {t.next}
            </button>
          </div>
        </div>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
