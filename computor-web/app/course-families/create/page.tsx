'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useSearchParam } from '@/src/hooks/useSearchParam';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { CourseFamilyGet } from '@/src/generated/types/courses';
import type { OrganizationList } from '@/src/generated/types/organizations';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';

const organizationsClient = new OrganizationsClient();
const courseFamiliesClient = new CourseFamiliesClient();

function CreateInner() {
  const router = useRouter();
  const organizationIdParam = useSearchParam('organization_id');
  const { isAuthenticated, isLoading: authLoading } = useAuth();
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
      router.push(`/course-families/${fam.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canCreateCourseFamily()) {
    return <Forbidden message="You do not have permission to create course families." />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Course Families', href: '/course-families' }, { label: 'New' }]}
        title="New Course Family"
        description="A course family is a lecture — a lecture type such as 'Introduction to Programming'. Each time it runs in a term, you add a course (one instance) under it."
        error={error}
        submitting={saving}
        disabled={!path.trim() || !organizationId}
        submitLabel="Create"
        onCancel={() => router.push('/course-families')}
        onSubmit={save}
      >
        <Field label="Organization" required hint="The faculty or institute this lecture belongs to.">
          <select value={organizationId} onChange={(e) => setOrganizationId(e.target.value)} className={inputCls}>
            <option value="">Select an organization…</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>{o.title || o.path}</option>
            ))}
          </select>
        </Field>
        <Field label="Path (slug)" required hint="Lowercase, URL-safe identifier, unique within the organization.">
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="intro-programming" className={inputCls} />
        </Field>
        <Field label="Title" hint="The lecture's name, e.g. 'Introduction to Programming'.">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Introduction to Programming" className={inputCls} />
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
