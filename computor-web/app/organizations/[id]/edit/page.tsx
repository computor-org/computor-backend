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
import type { OrganizationGet, OrganizationType } from '@/src/generated/types/organizations';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { organizationTypeLabel } from '@/src/utils/organizationType';

const organizationsClient = new OrganizationsClient();

const ORG_TYPES: OrganizationType[] = ['organization', 'community', 'user'];

const COPY = {
  de: {
    forbidden: 'Du hast keine Berechtigung, Organisationen zu bearbeiten.',
    saveFailed: 'Speichern fehlgeschlagen',
    crumb: 'Organisationen',
    organization: 'Organisation',
    organizationLower: 'Organisation',
    edit: 'Bearbeiten',
    titleLabel: 'Titel',
    type: 'Typ',
    description: 'Beschreibung',
    path: 'Pfad (unveränderlich)',
    pathHint: 'Der hierarchische Pfad steht nach dem Erstellen fest.',
    editTitle: (name: string) => `${name} bearbeiten`,
  },
  en: {
    forbidden: 'You do not have permission to edit organizations.',
    saveFailed: 'Save failed',
    crumb: 'Organizations',
    organization: 'Organization',
    organizationLower: 'organization',
    edit: 'Edit',
    titleLabel: 'Title',
    type: 'Type',
    description: 'Description',
    path: 'Path (immutable)',
    pathHint: 'The hierarchical path is fixed after creation.',
    editTitle: (name: string) => `Edit ${name}`,
  },
};

export default function OrganizationEditPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const orgId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [orgType, setOrgType] = useState<OrganizationType>('organization');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: org, loading, error: loadError } = useResource(
    () => organizationsClient.getOrganizationsOrganizationsIdGet({ id: orgId }),
    [orgId],
    { enabled: canManage },
  );

  // Seed the form once org loads. Adjusting state during render (instead of in
  // an effect) is React's documented way to derive state from changed data: it
  // re-renders before committing, so there is no cascading render.
  const [seeded, setSeeded] = useState(org);
  if (org && org !== seeded) {
    setSeeded(org);
    setTitle(org.title || '');
    setDescription(org.description || '');
    setOrgType((org.organization_type as OrganizationType) || 'organization');
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
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
            { label: t.crumb, href: '/organizations' },
            { label: org?.title || org?.path || t.organization, href: `/organizations/${orgId}` },
            { label: t.edit },
          ]}
          title={t.editTitle(org?.title || org?.path || t.organizationLower)}
          error={loadError ?? saveError}
          submitting={saving}
          onCancel={() => router.push(`/organizations/${orgId}`)}
          onSubmit={save}
        >
          <Field label={t.titleLabel}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
          </Field>
          <Field label={t.type}>
            <select value={orgType} onChange={(e) => setOrgType(e.target.value as OrganizationType)} className={inputCls}>
              {ORG_TYPES.map((type) => (
                <option key={type} value={type}>{organizationTypeLabel(type, language)}</option>
              ))}
            </select>
          </Field>
          <Field label={t.description}>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className={inputCls} />
          </Field>
          <Field label={t.path} hint={t.pathHint}>
            <input value={org?.path || ''} readOnly className={readOnlyInputCls} />
          </Field>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
