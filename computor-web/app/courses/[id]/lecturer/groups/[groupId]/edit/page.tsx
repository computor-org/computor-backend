'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';

const groupsClient = new CourseGroupsClient();

const COPY = {
  de: {
    courseGroups: 'Kursgruppen',
    group: 'Gruppe',
    groupFallback: 'Gruppe',
    saveFailed: 'Speichern fehlgeschlagen',
    forbidden: 'Zum Verwalten der Gruppen brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    edit: (name: string) => `${name} bearbeiten`,
    titleField: 'Titel',
    descriptionField: 'Beschreibung',
  },
  en: {
    courseGroups: 'Course groups',
    group: 'Group',
    groupFallback: 'group',
    saveFailed: 'Save failed',
    forbidden: 'You need lecturer access (or higher) on this course to manage its groups.',
    edit: (name: string) => `Edit ${name}`,
    titleField: 'Title',
    descriptionField: 'Description',
  },
};

export default function CourseGroupEditPage() {
  const params = useParams();
  const courseId = params.id as string;
  const groupId = params.groupId as string;
  const router = useRouter();
  const t = COPY[useUiLanguage()];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [title, setTitle] = useState('');
  const crumbs = useCourseCrumbs(courseId, { label: t.courseGroups, href: `/courses/${courseId}/lecturer/groups` }, title || t.group);
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: group, loading, error: loadError } = useResource(
    () => groupsClient.getCourseGroupsCourseGroupsIdGet({ id: groupId }),
    [groupId],
    { enabled: canManage },
  );

  // Seed the form once group loads. Adjusting state during render (instead of in
  // an effect) is React's documented way to derive state from changed data: it
  // re-renders before committing, so there is no cascading render.
  const [seeded, setSeeded] = useState(group);
  if (group && group !== seeded) {
    setSeeded(group);
    setTitle(group.title || '');
    setDescription(group.description || '');
  }

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
      setSaveError(e instanceof Error ? e.message : t.saveFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <PageLoading />
      ) : (
        <FormPanel
          breadcrumbs={crumbs}
          title={t.edit(title || t.groupFallback)}
          error={loadError ?? saveError}
          submitting={saving}
          disabled={!title.trim()}
          onCancel={() => router.push(`/courses/${courseId}/lecturer/groups`)}
          onSubmit={save}
        >
          <Field label={t.titleField} required>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label={t.descriptionField}>
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
