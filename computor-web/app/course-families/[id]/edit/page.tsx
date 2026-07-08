'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';

const courseFamiliesClient = new CourseFamiliesClient();

export default function CourseFamilyEditPage() {
  const familyId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: family, loading, error: loadError } = useResource(
    () => courseFamiliesClient.getCourseFamiliesCourseFamiliesIdGet({ id: familyId }),
    [familyId],
    { enabled: canManage },
  );

  // Seed the form once the course family loads.
  useEffect(() => {
    if (!family) return;
    setTitle(family.title || '');
    setDescription(family.description || '');
  }, [family]);

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await courseFamiliesClient.updateCourseFamiliesCourseFamiliesIdPatch({
        id: familyId,
        body: { title: title.trim() || null, description: description.trim() || null },
      });
      router.push(`/course-families/${familyId}`);
    } catch (e) {
      setSaving(false);
      setSaveError(e instanceof Error ? e.message : 'Save failed');
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
          error={loadError ?? saveError}
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
