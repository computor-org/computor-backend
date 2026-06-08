'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { OrganizationGet, OrganizationType } from '@/src/generated/types/organizations';

const ORG_TYPES: OrganizationType[] = ['organization', 'community', 'user'];

export default function OrganizationEditPage() {
  const orgId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [org, setOrg] = useState<OrganizationGet | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [orgType, setOrgType] = useState<OrganizationType>('organization');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`${API_BASE_URL}/organizations/${orgId}`);
        if (!res.ok) throw new Error('Failed to load organization');
        const o: OrganizationGet = await res.json();
        if (cancelled) return;
        setOrg(o);
        setTitle(o.title || '');
        setDescription(o.description || '');
        setOrgType((o.organization_type as OrganizationType) || 'organization');
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'An error occurred');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orgId, authLoading, isAuthenticated, canManage]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/organizations/${orgId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim() || null,
          description: description.trim() || null,
          organization_type: orgType,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Save failed (${res.status})`);
      router.push(`/organizations/${orgId}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have permission to edit organizations." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <div className="p-6 text-gray-500">Loading…</div>
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: 'Organizations', href: '/organizations' },
            { label: org?.title || org?.path || 'Organization', href: `/organizations/${orgId}` },
            { label: 'Edit' },
          ]}
          title={`Edit ${org?.title || org?.path || 'organization'}`}
          error={error}
          submitting={saving}
          onCancel={() => router.push(`/organizations/${orgId}`)}
          onSubmit={save}
        >
          <Field label="Title">
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label="Type">
            <select value={orgType} onChange={(e) => setOrgType(e.target.value as OrganizationType)} className={inputCls}>
              {ORG_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </Field>
          <Field label="Description">
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className={inputCls} />
          </Field>
          <Field label="Path (immutable)" hint="The hierarchical path is fixed after creation.">
            <input value={org?.path || ''} readOnly className={`${inputCls} bg-gray-50 text-gray-500`} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
