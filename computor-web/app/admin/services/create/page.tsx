'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { ServicesClient } from '@/src/generated/clients/ServicesClient';
import { ServiceTypesClient } from '@/src/generated/clients/ServiceTypesClient';
import { TESTING_LANGUAGES } from '@/src/utils/services';
import type { ServiceTypeList } from 'types/generated';

const servicesClient = new ServicesClient();
const serviceTypesClient = new ServiceTypesClient();

export default function ServiceCreatePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isServiceManager: canManage } = usePermissions();

  const [slug, setSlug] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [serviceTypePath, setServiceTypePath] = useState('');
  const [email, setEmail] = useState('');
  const [language, setLanguage] = useState('python');
  const [taskQueue, setTaskQueue] = useState('testing');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: typeData } = useResource(
    () => serviceTypesClient.listServiceTypesServiceTypesGet({ enabled: true }),
    [],
    { enabled: canManage },
  );
  const types: ServiceTypeList[] = useMemo(() => typeData ?? [], [typeData]);

  // Only `testing.*` types run tests, so only they need a language and a
  // Temporal queue. Everything else (agents, integrations) gets a plain form.
  const selected = types.find((t) => t.path === serviceTypePath);
  const isTesting = selected?.category === 'testing';

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const created = await servicesClient.createServiceEndpointServiceAccountsPost({
        body: {
          slug: slug.trim(),
          name: name.trim(),
          description: description.trim() || null,
          service_type: serviceTypePath,
          email: email.trim() || null,
          language: isTesting ? language : null,
          config: isTesting && taskQueue.trim() ? { temporal: { task_queue: taskQueue.trim() } } : {},
        },
      });
      router.push(`/admin/services/${created.id}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or service-manager access is required." />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: 'Services', href: '/admin/services' }, { label: 'New' }]}
        title="New service account"
        description="Creates a non-human user that authenticates with an API token. Mint the token on the next screen."
        error={error}
        submitting={saving}
        disabled={!slug.trim() || !name.trim() || !serviceTypePath}
        submitLabel="Create"
        onCancel={() => router.push('/admin/services')}
        onSubmit={save}
      >
        <Field
          label="Slug"
          required
          hint="Lowercase letters, digits, dots and hyphens. For a testing service this must match properties.executionBackend.slug in your examples' meta.yaml — that string is what binds an assignment to this service. It is an identifier only; it does not select the test runner."
        >
          <input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="acme.exec.py" className={inputCls} />
        </Field>
        <Field label="Name" required>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Python Runner" className={inputCls} />
        </Field>
        <Field label="Description">
          <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} />
        </Field>
        <Field label="Service type" required hint="Determines the default token scopes and whether this service runs tests.">
          <select value={serviceTypePath} onChange={(e) => setServiceTypePath(e.target.value)} className={inputCls}>
            <option value="">Select a type…</option>
            {types.map((t) => (
              <option key={t.id} value={t.path}>{t.path} — {t.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Email" hint="Identifies the service user. Defaults are conventionally <slug>@computor.local.">
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="acme-runner@computor.local" className={inputCls} />
        </Field>

        {isTesting && (
          <>
            <Field label="Language" required hint="Selects the test runner. Stored as config.language.">
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>
                {TESTING_LANGUAGES.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </Field>
            <Field label="Temporal task queue" hint="Must equal the worker container's --queues= value, or submitted tests sit queued forever.">
              <input value={taskQueue} onChange={(e) => setTaskQueue(e.target.value)} placeholder="testing" className={inputCls} />
            </Field>
          </>
        )}
      </FormPanel>
    </AuthenticatedLayout>
  );
}
