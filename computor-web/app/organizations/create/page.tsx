'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import type { OrganizationType } from '@/src/generated/types/organizations';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';

const organizationsClient = new OrganizationsClient();

const ORG_TYPES: OrganizationType[] = ['organization', 'community', 'user'];

const COPY = {
  de: {
    forbidden: 'Du hast keine Berechtigung, Organisationen zu erstellen.',
    createFailed: 'Erstellen fehlgeschlagen',
    crumb: 'Organisationen',
    crumbNew: 'Neu',
    title: 'Neue Organisation',
    pathExample: 'musterhochschule',
    description:
      'Eine Organisation ist eine Fakultät oder ein Institut – die oberste Ebene der Hierarchie. Sie besitzt die Kursfamilien (Lehrveranstaltungen), die darunter unterrichtet werden.',
    submit: 'Erstellen',
    path: 'Pfad (Slug)',
    pathHint: 'Kleingeschriebener, URL-tauglicher Bezeichner im Hierarchiepfad. Später nur schwer zu ändern.',
    type: 'Typ',
    typeHint: 'Verwende „organization“ für eine Fakultät oder ein Institut.',
    titleLabel: 'Titel',
    titleHint: 'Anzeigename in Listen, z. B. „Institut für Softwaretechnologie“.',
    titlePlaceholder: 'Institut für Softwaretechnologie',
    descriptionLabel: 'Beschreibung',
  },
  en: {
    forbidden: 'You do not have permission to create organizations.',
    createFailed: 'Create failed',
    crumb: 'Organizations',
    crumbNew: 'New',
    title: 'New organization',
    pathExample: 'acme',
    description:
      'An organization is a faculty or institute — the top of the hierarchy. It owns the course families (lectures) taught under it.',
    submit: 'Create',
    path: 'Path (slug)',
    pathHint: 'Lowercase, URL-safe identifier used in the hierarchy path. Hard to change later.',
    type: 'Type',
    typeHint: "Use 'organization' for a faculty or institute.",
    titleLabel: 'Title',
    titleHint: "Display name shown in lists, e.g. 'Institute of Software Technology'.",
    titlePlaceholder: 'Institute of Software Technology',
    descriptionLabel: 'Description',
  },
};

export default function OrganizationCreatePage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, refreshPermissions } = useAuth();
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
      const org = await organizationsClient.createOrganizationsOrganizationsPost({
        body: {
          path: path.trim(),
          organization_type: orgType,
          title: title.trim() || null,
          description: description.trim() || null,
        },
      });
      // Creating an organization enrols the creator as its `_owner`; re-pull
      // /user/scopes so the page we are about to open sees that role.
      await refreshPermissions();
      router.push(`/organizations/${org.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : t.createFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canCreateOrganization) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: t.crumb, href: '/organizations' }, { label: t.crumbNew }]}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving}
        disabled={!path.trim()}
        submitLabel={t.submit}
        onCancel={() => router.push('/organizations')}
        onSubmit={save}
      >
        <Field label={t.path} required hint={t.pathHint}>
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder={t.pathExample} className={inputCls} />
        </Field>
        <Field label={t.type} hint={t.typeHint}>
          <select value={orgType} onChange={(e) => setOrgType(e.target.value as OrganizationType)} className={inputCls}>
            {ORG_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
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
