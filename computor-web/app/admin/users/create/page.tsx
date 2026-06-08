'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import type { UserCreate } from 'types/generated';

const SYSTEM_ROLES = ['_admin', '_user_manager', '_organization_manager', '_workspace_user', '_workspace_maintainer'];
const usersClient = new UsersClient();

export default function UserCreatePage() {
  const router = useRouter();
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
        await api.post('/user-roles', { user_id: created.id, role_id: roleId }).catch(() => {});
      }
      router.push(`/admin/users/${created.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Failed to create user');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Requires admin or _user_manager role." />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Users', href: '/admin/users' }, { label: 'New' }]}
        title="Create User"
        description="The user will have no password — send them an invite link to set one."
        error={error}
        submitting={saving}
        disabled={!email.trim()}
        submitLabel="Create"
        onCancel={() => router.push('/admin/users')}
        onSubmit={save}
      >
        <Field label="Email" required>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="john@example.com" className={inputCls} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Given name">
            <input value={givenName} onChange={(e) => setGivenName(e.target.value)} placeholder="John" className={inputCls} />
          </Field>
          <Field label="Family name">
            <input value={familyName} onChange={(e) => setFamilyName(e.target.value)} placeholder="Doe" className={inputCls} />
          </Field>
        </div>
        <Field label="System roles">
          <div className="flex flex-wrap gap-3">
            {SYSTEM_ROLES.map((r) => (
              <label key={r} className="flex items-center gap-1.5 text-sm text-gray-700">
                <input type="checkbox" checked={roles.includes(r)} onChange={() => toggleRole(r)} />
                {r}
              </label>
            ))}
          </div>
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
