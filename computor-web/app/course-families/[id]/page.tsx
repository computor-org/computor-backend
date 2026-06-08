'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import type { CourseFamilyGet, CourseList } from '@/src/generated/types/courses';

export default function CourseFamilyDetailPage() {
  const familyId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, canCreateCourse } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [family, setFamily] = useState<CourseFamilyGet | null>(null);
  const [courses, setCourses] = useState<CourseList[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [famRes, courseRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/course-families/${familyId}`),
        apiFetch(`${API_BASE_URL}/courses?course_family_id=${familyId}`),
      ]);
      if (!famRes.ok) throw new Error('Failed to load course family');
      setFamily(await famRes.json());
      if (courseRes.ok) setCourses(await courseRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [familyId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  const mayCreateCourse = family ? canCreateCourse(family.organization_id, familyId) : false;

  async function doDelete() {
    const res = await apiFetch(`${API_BASE_URL}/course-families/${familyId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error((await res.text()) || `Delete failed (${res.status})`);
    router.push('/course-families');
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Course Families', href: '/course-families' }, { label: family?.title || family?.path || 'Course Family' }]} />

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{family?.title || family?.path || 'Course Family'}</h1>
            {family && <p className="mt-1 text-sm text-gray-500 font-mono">{family.path}</p>}
          </div>
          <div className="flex items-center gap-2">
            {mayCreateCourse && (
              <Link href={`/courses/create?familyId=${familyId}`} className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                New Course
              </Link>
            )}
            {canManage && (
              <>
                <Link href={`/course-families/${familyId}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  Edit
                </Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
                  Delete
                </button>
              </>
            )}
          </div>
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {family?.description && (
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            <p className="text-gray-700">{family.description}</p>
          </div>
        )}

        <h2 className="text-xl font-semibold text-gray-900">
          Courses {!loading && <span className="text-gray-400 font-normal">({courses.length})</span>}
        </h2>
        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : courses.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">No courses in this family yet.</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {courses.map((c) => (
              <Link key={c.id} href={`/courses/${c.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{c.title || c.path}</div>
                  <div className="text-xs text-gray-500 font-mono">{c.path}</div>
                </div>
                <span className="text-gray-300">›</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      {confirmDelete && family && (
        <ConfirmDeleteDialog
          title={`Delete course family “${family.title || family.path}”?`}
          message="This permanently deletes the course family and is irreversible. It must have no courses first."
          confirmWord={family.path}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
