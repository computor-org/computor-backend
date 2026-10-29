'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import SystemRoleCheckboxes from '@/src/components/SystemRoleCheckboxes';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { UserRolesClient } from '@/src/generated/clients/UserRolesClient';
import type { UserCreate } from 'types/generated';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const usersClient = new UsersClient();
const userClient = new UserRolesClient();

const COPY = {
  de: {
    createFailed: 'Benutzer konnte nicht erstellt werden',
    forbidden: 'Erfordert die Rolle admin oder _user_manager.',
    users: 'Benutzer',
    new: 'Neu',
    title: 'Neuer Benutzer',
    description: 'Der Benutzer kann sich noch nicht anmelden. Erstelle anschließend einen Einladungslink und gib ihn selbst weiter, denn Computor versendet keine E-Mails.',
    create: 'Erstellen',
    email: 'E-Mail',
    givenName: 'Vorname',
    familyName: 'Nachname',
    emailExample: 'erika.musterfrau@example.com',
    givenNameExample: 'Erika',
    familyNameExample: 'Musterfrau',
    systemRoles: 'Systemrollen',
    rolesHint: 'Leer lassen für einen normalen Benutzer. Weise Rollen nur bei Bedarf zu.',
  },
  en: {
    createFailed: 'Failed to create user',
    forbidden: 'Requires admin or _user_manager role.',
    users: 'Users',
    new: 'New',
    title: 'New user',
    description: 'The user cannot sign in yet. Create an invite link afterwards and share it with them yourself — Computor does not send emails.',
    create: 'Create',
    email: 'Email',
    givenName: 'Given name',
    familyName: 'Family name',
    emailExample: 'john@example.com',
    givenNameExample: 'John',
    familyNameExample: 'Doe',
    systemRoles: 'System roles',
    rolesHint: 'Leave empty for a plain user. Assign roles only as needed.',
  },
};

export default function UserCreatePage() {
  const router = useRouter();
  const language = useUiLanguage();
  const t = COPY[language];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isUserManager } = usePermissions();
  const canManage = isAdmin || isUserManager;

  const [email, setEmail] = useState('');
  const [givenName, setGivenName] = useState('');
  const [familyName, setFamilyName] = useState('');
  const [roles, setRoles] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleRole = (r: string) => setRoles((rs) => (rs.includes(r) ? rs.filter((x) => x !== r) : [...rs, r]));

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const payload: UserCreate = {
        email: email.trim(),
        given_name: givenName.trim() || undefined,
        family_name: familyName.trim() || undefined,
      };
      const created = await usersClient.createUsersUsersPost({ body: payload });
      for (const roleId of roles) {
        await userClient.createUserRoleUserRolesPost({ body: { user_id: created.id, role_id: roleId } }).catch(() => {});
      }
      router.push(`/admin/users/${created.id}`);
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
        breadcrumbs={[{ label: t.users, href: '/admin/users' }, { label: t.new }]}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving}
        disabled={!email.trim()}
        submitLabel={t.create}
        onCancel={() => router.push('/admin/users')}
        onSubmit={save}
      >
        <Field label={t.email} required>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t.emailExample} className={inputCls} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={t.givenName}>
            <input value={givenName} onChange={(e) => setGivenName(e.target.value)} placeholder={t.givenNameExample} className={inputCls} />
          </Field>
          <Field label={t.familyName}>
            <input value={familyName} onChange={(e) => setFamilyName(e.target.value)} placeholder={t.familyNameExample} className={inputCls} />
          </Field>
        </div>
        <Field label={t.systemRoles} hint={t.rolesHint}>
          <SystemRoleCheckboxes selected={roles} onToggle={toggleRole} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
