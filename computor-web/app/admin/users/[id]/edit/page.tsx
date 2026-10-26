'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useResource } from '@/src/hooks/useResource';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { PageLoading } from '@/src/components/ListPageLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { UsersClient } from '@/src/generated/clients/UsersClient';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const usersClient = new UsersClient();

const COPY = {
  de: {
    saveFailed: 'Speichern fehlgeschlagen',
    forbidden: 'Erfordert die Rolle admin oder _user_manager.',
    users: 'Benutzer',
    user: 'Benutzer',
    edit: 'Bearbeiten',
    title: (name: string) => `${name} bearbeiten`,
    userFallback: 'Benutzer',
    email: 'E-Mail',
    givenName: 'Vorname',
    familyName: 'Nachname',
  },
  en: {
    saveFailed: 'Save failed',
    forbidden: 'Requires admin or _user_manager role.',
    users: 'Users',
    user: 'User',
    edit: 'Edit',
    title: (name: string) => `Edit ${name}`,
    userFallback: 'user',
    email: 'Email',
    givenName: 'Given name',
    familyName: 'Family name',
  },
};

export default function UserEditPage() {
  const userId = useParams().id as string;
  const router = useRouter();
  const language = useUiLanguage();
  const t = COPY[language];
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

  // Seed the form once user loads. Adjusting state during render (instead of in
  // an effect) is React's documented way to derive state from changed data: it
  // re-renders before committing, so there is no cascading render.
  const [seeded, setSeeded] = useState(user);
  if (user && user !== seeded) {
    setSeeded(user);
    setEmail(user.email || '');
    setGivenName(user.given_name || '');
    setFamilyName(user.family_name || '');
  }

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
            { label: t.users, href: '/admin/users' },
            { label: user?.email || t.user, href: `/admin/users/${userId}` },
            { label: t.edit },
          ]}
          title={t.title(user?.email || t.userFallback)}
          error={loadError ?? saveError}
          submitting={saving}
          onCancel={() => router.push(`/admin/users/${userId}`)}
          onSubmit={save}
        >
          <Field label={t.email}>
            <input value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label={t.givenName}>
              <input value={givenName} onChange={(e) => setGivenName(e.target.value)} className={inputCls} />
            </Field>
            <Field label={t.familyName}>
              <input value={familyName} onChange={(e) => setFamilyName(e.target.value)} className={inputCls} />
            </Field>
          </div>
        </FormPanel>
      )}
    </AuthenticatedLayout>
  );
}
