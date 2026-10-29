'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls, readOnlyInputCls } from '@/src/components/ui/tokens';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';

const courseFamiliesClient = new CourseFamiliesClient();

const COPY = {
  de: {
    forbidden: 'Du hast keine Berechtigung, Kursfamilien zu bearbeiten.',
    saveFailed: 'Speichern fehlgeschlagen',
    crumb: 'Kursfamilien',
    family: 'Kursfamilie',
    edit: 'Bearbeiten',
    editTitle: (name: string) => `${name} bearbeiten`,
    titleLabel: 'Titel',
    description: 'Beschreibung',
    path: 'Pfad (unveränderlich)',
    pathHint: 'Der hierarchische Pfad steht nach dem Erstellen fest.',
  },
  en: {
    forbidden: 'You do not have permission to edit course families.',
    saveFailed: 'Save failed',
    crumb: 'Course families',
    family: 'Course Family',
    edit: 'Edit',
    editTitle: (name: string) => `Edit ${name}`,
    titleLabel: 'Title',
    description: 'Description',
    path: 'Path (immutable)',
    pathHint: 'The hierarchical path is fixed after creation.',
  },
};

export default function CourseFamilyEditPage() {
  const language = useUiLanguage();
  const t = COPY[language];
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

  // Seed the form once family loads. Adjusting state during render (instead of in
  // an effect) is React's documented way to derive state from changed data: it
  // re-renders before committing, so there is no cascading render.
  const [seeded, setSeeded] = useState(family);
  if (family && family !== seeded) {
    setSeeded(family);
    setTitle(family.title || '');
    setDescription(family.description || '');
  }

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
          breadcrumbs={[
            { label: t.crumb, href: '/course-families' },
            { label: family?.title || family?.path || t.family, href: `/course-families/${familyId}` },
            { label: t.edit },
          ]}
          title={t.editTitle(family?.title || family?.path || (language === 'de' ? 'Kursfamilie' : 'course family'))}
          error={loadError ?? saveError}
          submitting={saving}
          onCancel={() => router.push(`/course-families/${familyId}`)}
          onSubmit={save}
        >
          <Field label={t.titleLabel}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label={t.description}>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className={inputCls} />
          </Field>
          <Field label={t.path} hint={t.pathHint}>
            <input value={family?.path || ''} readOnly className={readOnlyInputCls} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
