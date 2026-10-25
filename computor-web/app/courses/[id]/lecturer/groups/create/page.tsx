'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCourseCrumbs } from '@/src/hooks/useCourseCrumbs';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { CourseGroupsClient } from '@/src/generated/clients/CourseGroupsClient';

const groupsClient = new CourseGroupsClient();

const COPY = {
  de: {
    courseGroups: 'Kursgruppen',
    new: 'Neu',
    createFailed: 'Erstellen fehlgeschlagen',
    forbidden: 'Zum Verwalten der Gruppen brauchst du mindestens Lehrenden-Zugriff auf diesen Kurs.',
    title: 'Neue Gruppe',
    description: 'Eine Gruppe, der Studierende zugeordnet werden (z. B. eine Übungsgruppe oder ein Tutorium). Jede studierende Person im Kurs muss einer Gruppe angehören.',
    create: 'Erstellen',
    titleField: 'Titel',
    descriptionField: 'Beschreibung',
    placeholder: 'Gruppe A',
  },
  en: {
    courseGroups: 'Course groups',
    new: 'New',
    createFailed: 'Create failed',
    forbidden: 'You need lecturer access (or higher) on this course to manage its groups.',
    title: 'New group',
    description: 'A group students are assigned to (e.g. a lab section or tutorial cohort). Every student in the course must belong to a group.',
    create: 'Create',
    titleField: 'Title',
    descriptionField: 'Description',
    placeholder: 'Group A',
  },
};

export default function CourseGroupCreatePage() {
  const courseId = useParams().id as string;
  const t = COPY[useUiLanguage()];
  const crumbs = useCourseCrumbs(courseId, { label: t.courseGroups, href: `/courses/${courseId}/lecturer/groups` }, t.new);
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, courseHasAtLeast } = usePermissions();

  const canManage = isAdmin || isOrganizationManager || courseHasAtLeast(courseId, '_lecturer');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      router.push(`/courses/${courseId}/lecturer/groups`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : t.createFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={crumbs}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving}
        disabled={!title.trim()}
        submitLabel={t.create}
        onCancel={() => router.push(`/courses/${courseId}/lecturer/groups`)}
        onSubmit={save}
      >
        <Field label={t.titleField} required>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t.placeholder}
            className={inputCls}
          />
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
    </AuthenticatedLayout>
  );
}
