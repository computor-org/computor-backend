'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { OrganizationGet, OrganizationType } from '@/src/generated/types/organizations';

const ORG_TYPES: OrganizationType[] = ['organization', 'community', 'user'];

export default function OrganizationCreatePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canCreateOrganization } = usePermissions();

  const [path, setPath] = useState('');
  const [orgType, setOrgType] = useState<OrganizationType>('organization');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const org = await api.post<OrganizationGet>('/organizations', {
        path: path.trim(),
        organization_type: orgType,
        title: title.trim() || null,
        description: description.trim() || null,
      });
      router.push(`/organizations/${org.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canCreateOrganization) {
    return <Forbidden message="You do not have permission to create organizations." />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Organizations', href: '/organizations' }, { label: 'New' }]}
        title="New Organization"
        description="An organization is a faculty or institute — the top of the hierarchy. It owns the course families (lectures) taught under it."
        error={error}
        submitting={saving}
        disabled={!path.trim()}
        submitLabel="Create"
        onCancel={() => router.push('/organizations')}
        onSubmit={save}
      >
        <Field label="Path (slug)" required hint="Lowercase, URL-safe identifier used in the hierarchy path. Hard to change later.">
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="acme" className={inputCls} />
        </Field>
        <Field label="Type" hint="Use 'organization' for a faculty or institute.">
          <select value={orgType} onChange={(e) => setOrgType(e.target.value as OrganizationType)} className={inputCls}>
            {ORG_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </Field>
        <Field label="Title" hint="Display name shown in lists, e.g. 'Institute of Software Technology'.">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Institute of Software Technology" className={inputCls} />
        </Field>
        <Field label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
