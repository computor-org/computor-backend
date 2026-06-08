'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { OrganizationType } from '@/src/generated/types/organizations';

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
      const res = await apiFetch(`${API_BASE_URL}/organizations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: path.trim(),
          organization_type: orgType,
          title: title.trim() || null,
          description: description.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      const org = await res.json();
      router.push(`/organizations/${org.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canCreateOrganization) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have permission to create organizations." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Organizations', href: '/organizations' }, { label: 'New' }]}
        title="New Organization"
        error={error}
        submitting={saving}
        disabled={!path.trim()}
        submitLabel="Create"
        onCancel={() => router.push('/organizations')}
        onSubmit={save}
      >
        <Field label="Path (slug)" required>
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="acme" className={inputCls} />
        </Field>
        <Field label="Type">
          <select value={orgType} onChange={(e) => setOrgType(e.target.value as OrganizationType)} className={inputCls}>
            {ORG_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </Field>
        <Field label="Title">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Acme University" className={inputCls} />
        </Field>
        <Field label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
