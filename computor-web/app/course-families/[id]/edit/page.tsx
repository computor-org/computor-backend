'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { CourseFamilyGet } from '@/src/generated/types/courses';

export default function CourseFamilyEditPage() {
  const familyId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const [family, setFamily] = useState<CourseFamilyGet | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    let cancelled = false;
    api
      .get<CourseFamilyGet>(`/course-families/${familyId}`)
      .then((f) => {
        if (cancelled) return;
        setFamily(f);
        setTitle(f.title || '');
        setDescription(f.description || '');
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'An error occurred'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [familyId, authLoading, isAuthenticated, canManage]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/course-families/${familyId}`, { title: title.trim() || null, description: description.trim() || null });
      router.push(`/course-families/${familyId}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You do not have permission to edit course families." />;
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <div className="p-6 text-gray-500">Loading…</div>
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: 'Course Families', href: '/course-families' },
            { label: family?.title || family?.path || 'Course Family', href: `/course-families/${familyId}` },
            { label: 'Edit' },
          ]}
          title={`Edit ${family?.title || family?.path || 'course family'}`}
          error={error}
          submitting={saving}
          onCancel={() => router.push(`/course-families/${familyId}`)}
          onSubmit={save}
        >
          <Field label="Title">
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Description">
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className={inputCls} />
          </Field>
          <Field label="Path (immutable)" hint="The hierarchical path is fixed after creation.">
            <input value={family?.path || ''} readOnly className={`${inputCls} bg-gray-50 text-gray-500`} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
