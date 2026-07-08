'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import type { OrganizationGet, OrganizationType } from '@/src/generated/types/organizations';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';

const organizationsClient = new OrganizationsClient();

const ORG_TYPES: OrganizationType[] = ['organization', 'community', 'user'];

export default function OrganizationEditPage() {
  const orgId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

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
    organizationsClient
      .getOrganizationsOrganizationsIdGet({ id: orgId })
      .then((o) => {
        if (cancelled) return;
        setOrg(o);
        setTitle(o.title || '');
        setDescription(o.description || '');
        setOrgType((o.organization_type as OrganizationType) || 'organization');
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : 'An error occurred'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [orgId, authLoading, isAuthenticated, canManage]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await organizationsClient.updateOrganizationsOrganizationsIdPatch({
        id: orgId,
        body: {
          title: title.trim() || null,
          description: description.trim() || null,
          organization_type: orgType,
        },
      });
      router.push(`/organizations/${orgId}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You do not have permission to edit organizations." />;
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
