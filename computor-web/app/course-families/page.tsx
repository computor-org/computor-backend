'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseFamilyList } from '@/src/generated/types/courses';
import type { OrganizationList } from '@/src/generated/types/organizations';

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

interface CreateState {
  open: boolean;
  saving: boolean;
  error: string | null;
  path: string;
  title: string;
  description: string;
  organization_id: string;
}

const emptyCreate: CreateState = {
  open: false,
  saving: false,
  error: null,
  path: '',
  title: '',
  description: '',
  organization_id: '',
};

export default function CourseFamiliesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canCreateCourseFamily } = usePermissions();
  const [families, setFamilies] = useState<CourseFamilyList[]>([]);
  const [orgs, setOrgs] = useState<OrganizationList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [create, setCreate] = useState<CreateState>(emptyCreate);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fRes, oRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/course-families`),
        apiFetch(`${API_BASE_URL}/organizations`),
      ]);
      if (!fRes.ok) throw new Error('Failed to load course families');
      setFamilies(await fRes.json());
      if (oRes.ok) setOrgs(await oRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  // Organizations the user may create a course family in.
  const creatableOrgs = useMemo(
    () => orgs.filter((o) => canCreateCourseFamily(o.id)),
    [orgs, canCreateCourseFamily],
  );
  const orgLabel = (id: string) => {
    const o = orgs.find((x) => x.id === id);
    return o ? o.title || o.path : id;
  };

  async function handleCreate() {
    setCreate((c) => ({ ...c, saving: true, error: null }));
    try {
      const res = await apiFetch(`${API_BASE_URL}/course-families`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: create.path.trim(),
          organization_id: create.organization_id,
          title: create.title.trim() || null,
          description: create.description.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      setCreate(emptyCreate);
      await load();
    } catch (e) {
      setCreate((c) => ({ ...c, saving: false, error: e instanceof Error ? e.message : 'Create failed' }));
    }
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Course Families</h1>
            <p className="mt-2 text-gray-600">A course family groups related courses within an organization.</p>
          </div>
          {canCreateCourseFamily() && (
            <button
              onClick={() =>
                setCreate({
                  ...emptyCreate,
                  open: true,
                  organization_id: creatableOrgs[0]?.id ?? '',
                })
              }
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              New Course Family
            </button>
          )}
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
        )}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : families.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No course families yet.
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {families.map((f) => (
              <Link key={f.id} href={`/course-families/${f.id}`} className="block px-4 py-3 hover:bg-gray-50">
                <div className="text-sm font-medium text-gray-900">{f.title || f.path}</div>
                <div className="text-xs text-gray-500">
                  {f.path} · {orgLabel(f.organization_id)}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {create.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">New Course Family</h2>
              {create.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{create.error}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Organization <span className="text-red-500">*</span>
                </label>
                <select
                  value={create.organization_id}
                  onChange={(e) => setCreate((c) => ({ ...c, organization_id: e.target.value }))}
                  className={inputCls}
                >
                  <option value="">Select an organization…</option>
                  {creatableOrgs.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.title || o.path}
                    </option>
                  ))}
                </select>
                {creatableOrgs.length === 0 && (
                  <p className="mt-1 text-xs text-amber-600">
                    You do not have permission to create a course family in any organization.
                  </p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Path (slug) <span className="text-red-500">*</span>
                </label>
                <input
                  value={create.path}
                  onChange={(e) => setCreate((c) => ({ ...c, path: e.target.value }))}
                  placeholder="2026"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Title</label>
                <input
                  value={create.title}
                  onChange={(e) => setCreate((c) => ({ ...c, title: e.target.value }))}
                  placeholder="Winter Semester 2026"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={create.description}
                  onChange={(e) => setCreate((c) => ({ ...c, description: e.target.value }))}
                  rows={2}
                  className={inputCls}
                />
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button
                onClick={() => setCreate(emptyCreate)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={create.saving || !create.path.trim() || !create.organization_id}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {create.saving ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}
