'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';

const groupsClient = new CourseGroupsClient();

export default function CourseGroupEditPage() {
  const params = useParams();
  const courseId = params.id as string;
  const groupId = params.groupId as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: group, loading, error: loadError } = useResource(
    () => groupsClient.getCourseGroupsCourseGroupsIdGet({ id: groupId }),
    [groupId],
    { enabled: canManage },
  );

  // Seed the form once the group loads.
  useEffect(() => {
    if (!group) return;
    setTitle(group.title || '');
    setDescription(group.description || '');
  }, [group]);

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await groupsClient.updateCourseGroupsCourseGroupsIdPatch({
        id: groupId,
        body: { title: title.trim(), description: description.trim() || null },
      });
      router.push(`/courses/${courseId}/lecturer/groups`);
    } catch (e) {
      setSaving(false);
      setSaveError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You need lecturer access (or higher) on this course to manage its groups." />;
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <div className="p-6 text-gray-500">Loading…</div>
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: 'Course Groups', href: `/courses/${courseId}/lecturer/groups` },
            { label: title || 'Group' },
          ]}
          title={`Edit ${title || 'group'}`}
          error={loadError ?? saveError}
          submitting={saving}
          disabled={!title.trim()}
          onCancel={() => router.push(`/courses/${courseId}/lecturer/groups`)}
          onSubmit={save}
        >
          <Field label="Title" required>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className={inputCls}
            />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
