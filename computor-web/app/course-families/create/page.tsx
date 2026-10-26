'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import type { CourseFamilyGet } from '@/src/generated/types/courses';
import { displayName } from '@/src/utils/displayName';
import type { OrganizationList } from '@/src/generated/types/organizations';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';

const organizationsClient = new OrganizationsClient();
const courseFamiliesClient = new CourseFamiliesClient();

const COPY = {
  de: {
    forbidden: 'Du hast keine Berechtigung, Kursfamilien zu erstellen.',
    createFailed: 'Erstellen fehlgeschlagen',
    crumb: 'Kursfamilien',
    crumbNew: 'Neu',
    title: 'Neue Kursfamilie',
    description:
      'Eine Kursfamilie ist eine Lehrveranstaltung – ein Veranstaltungstyp wie „Einführung in die Programmierung“. Jedes Mal, wenn sie in einem Semester stattfindet, legst du darunter einen Kurs (eine Instanz) an.',
    submit: 'Erstellen',
    organization: 'Organisation',
    organizationHint: 'Die Fakultät oder das Institut, zu dem diese Lehrveranstaltung gehört.',
    selectOrg: 'Organisation auswählen …',
    untitledOrg: 'Organisation ohne Titel',
    path: 'Pfad (Slug)',
    pathHint: 'Kleingeschriebener, URL-tauglicher Bezeichner, eindeutig innerhalb der Organisation.',
    pathPlaceholder: 'einfuehrung-programmierung',
    titleLabel: 'Titel',
    titleHint: 'Der Name der Lehrveranstaltung, z. B. „Einführung in die Programmierung“.',
    titlePlaceholder: 'Einführung in die Programmierung',
    descriptionLabel: 'Beschreibung',
  },
  en: {
    forbidden: 'You do not have permission to create course families.',
    createFailed: 'Create failed',
    crumb: 'Course families',
    crumbNew: 'New',
    title: 'New course family',
    description:
      "A course family is a lecture — a lecture type such as 'Introduction to Programming'. Each time it runs in a term, you add a course (one instance) under it.",
    submit: 'Create',
    organization: 'Organization',
    organizationHint: 'The faculty or institute this lecture belongs to.',
    selectOrg: 'Select an organization…',
    untitledOrg: 'Untitled Organization',
    path: 'Path (slug)',
    pathHint: 'Lowercase, URL-safe identifier, unique within the organization.',
    pathPlaceholder: 'intro-programming',
    titleLabel: 'Title',
    titleHint: "The lecture's name, e.g. 'Introduction to Programming'.",
    titlePlaceholder: 'Introduction to Programming',
    descriptionLabel: 'Description',
  },
};

function CreateInner() {
  const language = useUiLanguage();
  const t = COPY[language];
  const router = useRouter();
  const organizationIdParam = useSearchParam('organization_id');
  const { isAuthenticated, isLoading: authLoading, refreshPermissions } = useAuth();
  const { canCreateCourseFamily } = usePermissions();

  const [orgs, setOrgs] = useState<OrganizationList[]>([]);
  const [organizationId, setOrganizationId] = useState(organizationIdParam);
  const [path, setPath] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    organizationsClient
      .listOrganizationsOrganizationsGet({})
      .then((all) => {
        const creatable = all.filter((o) => canCreateCourseFamily(o.id));
        setOrgs(creatable);
        if (!organizationIdParam && creatable.length === 1) setOrganizationId(creatable[0].id);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const fam = await courseFamiliesClient.createCourseFamiliesCourseFamiliesPost({
        body: {
          path: path.trim(),
          organization_id: organizationId,
          title: title.trim() || null,
          description: description.trim() || null,
        },
      });
      // Creating a course family enrols the creator as its `_owner`; re-pull
      // /user/scopes so the page we are about to open sees that role.
      await refreshPermissions();
      router.push(`/course-families/${fam.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : t.createFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canCreateCourseFamily()) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: t.crumb, href: '/course-families' }, { label: t.crumbNew }]}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving}
        disabled={!path.trim() || !organizationId}
        submitLabel={t.submit}
        onCancel={() => router.push('/course-families')}
        onSubmit={save}
      >
        <Field label={t.organization} required hint={t.organizationHint}>
          <select value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} className={inputCls}>
            <option value="">{t.selectOrg}</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>{displayName(o, t.untitledOrg)}</option>
            ))}
          </select>
        </Field>
        <Field label={t.path} required hint={t.pathHint}>
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder={t.pathPlaceholder} className={inputCls} />
        </Field>
        <Field label={t.titleLabel} hint={t.titleHint}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t.titlePlaceholder} className={inputCls} />
        </Field>
        <Field label={t.descriptionLabel}>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}

export default function CourseFamilyCreatePage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><PageLoading /></AuthenticatedLayout>}>
      <CreateInner />
    </Suspense>
  );
}
