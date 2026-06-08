'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import FormPanel, { Field, inputCls } from '@/src/components/FormPanel';

type GitServerType = 'forgejo' | 'gitlab';

export default function GitServerCreatePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [type, setType] = useState<GitServerType>('forgejo');
  const [baseUrl, setBaseUrl] = useState('');
  const [name, setName] = useState('');
  const [managed, setManaged] = useState(true);
  const [token, setToken] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/git-servers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type,
          base_url: baseUrl.trim(),
          name: name.trim() || null,
          managed,
          token: token.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      const server = await res.json();
      router.push(`/admin/git-servers/${server.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="Admin or organization-manager access is required." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Git Servers', href: '/admin/git-servers' }, { label: 'Register' }]}
        title="Register Git Server"
        error={error}
        submitting={saving}
        disabled={!baseUrl.trim()}
        submitLabel="Register"
        onCancel={() => router.push('/admin/git-servers')}
        onSubmit={save}
      >
        <Field label="Type">
          <select value={type} onChange={(e) => setType(e.target.value as GitServerType)} className={inputCls}>
            <option value="forgejo">forgejo</option>
            <option value="gitlab">gitlab</option>
          </select>
        </Field>
        <Field label="Base URL" required>
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://localhost:3030" className={inputCls} />
        </Field>
        <Field label="Name">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Our Forgejo" className={inputCls} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={managed} onChange={(e) => setManaged(e.target.checked)} />
          Managed (Computor operates it and holds a service token)
        </label>
        <Field label="Service token" hint={managed ? 'Needed for babysat provisioning. Stored encrypted, never returned.' : 'Stored encrypted, never returned.'}>
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="paste a service token" className={inputCls} />
        </Field>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
