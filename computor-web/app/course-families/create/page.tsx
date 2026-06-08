'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { OrganizationList } from '@/src/generated/types/organizations';

function CreateInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canCreateCourseFamily } = usePermissions();

  const [orgs, setOrgs] = useState<OrganizationList[]>([]);
  const [organizationId, setOrganizationId] = useState(params.get('organization_id') || '');
  const [path, setPath] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    (async () => {
      const res = await apiFetch(`${API_BASE_URL}/organizations`);
      if (res.ok) {
        const all: OrganizationList[] = await res.json();
        const creatable = all.filter((o) => canCreateCourseFamily(o.id));
        setOrgs(creatable);
        if (!organizationId && creatable.length === 1) setOrganizationId(creatable[0].id);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated]);

  const mayCreate = useMemo(() => canCreateCourseFamily(), [canCreateCourseFamily]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/course-families`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: path.trim(),
          organization_id: organizationId,
          title: title.trim() || null,
          description: description.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      const fam = await res.json();
      router.push(`/course-families/${fam.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !mayCreate) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have permission to create course families." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Course Families', href: '/course-families' }, { label: 'New' }]}
        title="New Course Family"
        error={error}
        submitting={saving}
        disabled={!path.trim() || !organizationId}
        submitLabel="Create"
        onCancel={() => router.push('/course-families')}
        onSubmit={save}
      >
        <Field label="Organization" required>
          <select value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} className={inputCls}>
            <option value="">Select an organization…</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>{o.title || o.path}</option>
            ))}
          </select>
        </Field>
        <Field label="Path (slug)" required>
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="2026" className={inputCls} />
        </Field>
        <Field label="Title">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Winter Semester 2026" className={inputCls} />
        </Field>
        <Field label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}

export default function CourseFamilyCreatePage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><div className="p-6 text-gray-500">Loading…</div></AuthenticatedLayout>}>
      <CreateInner />
    </Suspense>
  );
}
