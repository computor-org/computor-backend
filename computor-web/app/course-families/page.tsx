'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import type { CourseFamilyList } from '@/src/generated/types/courses';
import type { OrganizationList } from '@/src/generated/types/organizations';

export default function CourseFamiliesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canCreateCourseFamily } = usePermissions();
  const [families, setFamilies] = useState<CourseFamilyList[]>([]);
  const [orgs, setOrgs] = useState<OrganizationList[]>([]);
  const [courseCounts, setCourseCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fRes, oRes, cRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/course-families`),
        apiFetch(`${API_BASE_URL}/organizations`),
        apiFetch(`${API_BASE_URL}/courses`),
      ]);
      if (!fRes.ok) throw new Error('Failed to load course families');
      setFamilies(await fRes.json());
      if (oRes.ok) setOrgs(await oRes.json());
      if (cRes.ok) {
        const courses: Array<{ course_family_id?: string | null }> = await cRes.json();
        const counts: Record<string, number> = {};
        for (const c of courses) {
          if (c.course_family_id) counts[c.course_family_id] = (counts[c.course_family_id] ?? 0) + 1;
        }
        setCourseCounts(counts);
      }
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

  const orgLabel = (id: string) => {
    const o = orgs.find((x) => x.id === id);
    return o ? o.title || o.path : id;
  };

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Course Families' }]} />
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Course Families</h1>
            <p className="mt-2 text-gray-600">A course family groups related courses within an organization.</p>
          </div>
          {canCreateCourseFamily() && (
            <Link href="/course-families/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              New Course Family
            </Link>
          )}
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : families.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">No course families yet.</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {families.map((f) => (
              <Link key={f.id} href={`/course-families/${f.id}`} className="block px-4 py-3 hover:bg-gray-50">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-gray-900">{f.title || f.path}</div>
                  <span className="shrink-0 text-xs text-gray-500">
                    {courseCounts[f.id] ?? 0} {(courseCounts[f.id] ?? 0) === 1 ? 'course' : 'courses'}
                  </span>
                </div>
                <div className="text-xs text-gray-500">{f.path} · {orgLabel(f.organization_id)}</div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
