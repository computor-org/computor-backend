'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { UserList } from 'types/generated';

const usersClient = new UsersClient();

export default function UsersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isUserManager } = usePermissions();
  const canManage = isAdmin || isUserManager;

  const [users, setUsers] = useState<UserList[]>([]);
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await usersClient.listUsersUsersGet({ archived: showArchived ? true : undefined, limit: 200 });
      setUsers(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [showArchived]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    fetchUsers();
  }, [authLoading, isAuthenticated, canManage, fetchUsers]);

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <div className="p-8 text-red-600 font-medium">Access denied. Requires admin or _user_manager role.</div>
      </AuthenticatedLayout>
    );
  }

  const filtered = users.filter((u) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (u.email?.toLowerCase().includes(q) ?? false) || `${u.given_name ?? ''} ${u.family_name ?? ''}`.toLowerCase().includes(q);
  });

  return (
    <AuthenticatedLayout>
      <div className="p-6">
        <Breadcrumbs items={[{ label: 'Users' }]} />
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Users</h1>
            <p className="text-sm text-gray-500 mt-1">{users.length} total</p>
          </div>
          <Link href="/admin/users/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            New User
          </Link>
        </div>

        <div className="mb-4 flex items-center gap-3">
          <input
            type="text"
            placeholder="Search by email or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none whitespace-nowrap">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} className="rounded" />
            Show archived
          </label>
        </div>

        {loading ? (
          <div className="text-gray-500 py-8 text-center">Loading users…</div>
        ) : error ? (
          <div className="text-red-600 py-8 text-center">{error}</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((u) => (
                  <tr key={u.id} className={`hover:bg-gray-50 ${u.archived_at ? 'opacity-50' : ''}`}>
                    <td className="px-4 py-3">
                      <Link href={`/admin/users/${u.id}`} className="block group">
                        <div className="font-medium text-gray-900 text-sm group-hover:text-blue-600">{u.email ?? '—'}</div>
                        <div className="text-xs text-gray-500">{u.given_name} {u.family_name}</div>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${u.archived_at ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-800'}`}>
                        {u.archived_at ? 'Archived' : 'Active'}
                      </span>
                      {u.is_service && <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">Service</span>}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/admin/users/${u.id}`} className="text-sm text-blue-600 hover:underline">Manage →</Link>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">No users found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
