'use client';

import { useEffect, useState } from 'react';
import { useResource } from '@/src/hooks/useResource';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import Spinner from '@/src/components/ui/Spinner';
import { inputCls } from '@/src/components/ui/tokens';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { UserList } from 'types/generated';

const usersClient = new UsersClient();
const PAGE_SIZE = 8;

/** "Given Family", falling back to email, then id — same rule as the roster picker. */
export function userDisplayName(u: {
  id: string;
  given_name?: string | null;
  family_name?: string | null;
  email?: string | null;
}): string {
  const name = `${u.given_name ?? ''} ${u.family_name ?? ''}`.trim();
  return name || u.email || u.id;
}

/**
 * Compact debounced user search with a pick action per row.
 *
 * Follows the pattern of course-members/AddFromUserList but is selection-only:
 * type, find, pick — no course concerns, no paging chrome. The caller decides
 * what picking means (the button label says it) and can hold the list with
 * `busy` while it validates a pick.
 */
export default function UserSearchPicker({
  excludeId,
  onPick,
  busy = false,
  pickLabel = 'Select',
  placeholder = 'Search by name or email…',
}: {
  /** User hidden from the results (e.g. the user already on screen). */
  excludeId?: string;
  onPick: (user: UserList) => void;
  /** Disables picking while the caller is validating a previous pick. */
  busy?: boolean;
  pickLabel?: string;
  placeholder?: string;
}) {
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  // Debounce the search box.
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data, loading, error } = useResource(
    () =>
      usersClient.listUsersUsersGet({
        search: search || undefined,
        // One extra so filtering out excludeId doesn't shorten the page.
        limit: PAGE_SIZE + 1,
      }),
    [search],
  );
  const users = (data ?? []).filter((u) => u.id !== excludeId).slice(0, PAGE_SIZE);

  return (
    <div className="space-y-2">
      <input
        type="text"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        placeholder={placeholder}
        className={`${inputCls} max-w-md`}
      />
      <ErrorBanner>{error}</ErrorBanner>
      {loading ? (
        <div className="py-4 text-center">
          <Spinner size="sm" label="Searching users" />
        </div>
      ) : users.length === 0 ? (
        <p className="text-sm text-gray-400 italic">No matching users.</p>
      ) : (
        <ul className="bg-white border border-gray-200 rounded-md divide-y divide-gray-100">
          {users.map((u) => (
            <li key={u.id} className="flex items-center justify-between gap-3 px-3 py-2">
              <div className="min-w-0 text-sm">
                <div className="font-medium text-gray-900 truncate">{userDisplayName(u)}</div>
                <div className="text-xs text-gray-500 truncate">{u.email ?? '—'}</div>
              </div>
              <Button size="xs" variant="secondary" disabled={busy} onClick={() => onPick(u)}>
                {pickLabel}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
