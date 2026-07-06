'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
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
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    let cancelled = false;
    groupsClient
      .getCourseGroupsCourseGroupsIdGet({ id: groupId })
      .then((g) => {
        if (cancelled) return;
        setTitle(g.title || '');
        setDescription(g.description || '');
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'An error occurred'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [groupId, authLoading, isAuthenticated, canManage]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await groupsClient.updateCourseGroupsCourseGroupsIdPatch({
        id: groupId,
        body: { title: title.trim(), description: description.trim() || null },
      });
      router.push(`/courses/${courseId}/management/groups`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
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
            { label: 'Course Groups', href: `/courses/${courseId}/management/groups` },
            { label: title || 'Group' },
          ]}
          title={`Edit ${title || 'group'}`}
          error={error}
          submitting={saving}
          disabled={!title.trim()}
          onCancel={() => router.push(`/courses/${courseId}/management/groups`)}
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
