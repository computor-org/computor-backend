'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';
import { UsersClient } from '@/src/generated/clients/UsersClient';

const usersClient = new UsersClient();

export default function UserEditPage() {
  const userId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isUserManager } = usePermissions();
  const canManage = isAdmin || isUserManager;

  const [email, setEmail] = useState('');
  const [givenName, setGivenName] = useState('');
  const [familyName, setFamilyName] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: user, loading, error: loadError } = useResource(
    () => usersClient.getUsersUsersIdGet({ id: userId }),
    [userId],
    { enabled: canManage },
  );

  // Seed the form once the user loads.
  useEffect(() => {
    if (!user) return;
    setEmail(user.email || '');
    setGivenName(user.given_name || '');
    setFamilyName(user.family_name || '');
  }, [user]);

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await usersClient.updateUsersUsersIdPatch({
        id: userId,
        body: { email: email.trim() || null, given_name: givenName.trim() || null, family_name: familyName.trim() || null },
      });
      router.push(`/admin/users/${userId}`);
    } catch (e) {
      setSaving(false);
      setSaveError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Requires admin or _user_manager role." />;
  }

  return (
    <AuthenticatedLayout>
      {loading ? (
        <div className="p-6 text-gray-500">Loading…</div>
      ) : (
        <FormPanel
          breadcrumbs={[
            { label: 'Users', href: '/admin/users' },
            { label: user?.email || 'User', href: `/admin/users/${userId}` },
            { label: 'Edit' },
          ]}
          title={`Edit ${user?.email || 'user'}`}
          error={loadError ?? saveError}
          submitting={saving}
          onCancel={() => router.push(`/admin/users/${userId}`)}
          onSubmit={save}
        >
          <Field label="Email">
            <input value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Given name">
              <input value={givenName} onChange={(e) => setGivenName(e.target.value)} className={inputCls} />
            </Field>
            <Field label="Family name">
              <input value={familyName} onChange={(e) => setFamilyName(e.target.value)} className={inputCls} />
            </Field>
          </div>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
