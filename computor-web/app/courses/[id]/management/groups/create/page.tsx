'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';

const groupsClient = new CourseGroupsClient();
const coursesClient = new CoursesClient();

export default function CourseGroupCreatePage() {
  const courseId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: course } = useResource(
    () => coursesClient.getCoursesCoursesIdGet({ id: courseId }).catch(() => null),
    [courseId],
    { enabled: canManage },
  );
  const courseLabel = course?.title || course?.path || 'Course';

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await groupsClient.createCourseGroupsCourseGroupsPost({
        body: {
          course_id: courseId,
          title: title.trim(),
          description: description.trim() || null,
        },
      });
      router.push(`/courses/${courseId}/management/groups`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You need lecturer access (or higher) on this course to manage its groups." />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[
          { label: 'Courses', href: '/courses' },
          { label: courseLabel, href: `/courses/${courseId}` },
          { label: 'Course Groups', href: `/courses/${courseId}/management/groups` },
          { label: 'New' },
        ]}
        title="New group"
        description="A group students are assigned to (e.g. a lab section or tutorial cohort). Every student in the course must belong to a group."
        error={error}
        submitting={saving}
        disabled={!title.trim()}
        submitLabel="Create"
        onCancel={() => router.push(`/courses/${courseId}/management/groups`)}
        onSubmit={save}
      >
        <Field label="Title" required>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Group A"
            className={inputCls}
          />
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
    </AuthenticatedLayout>
  );
}
