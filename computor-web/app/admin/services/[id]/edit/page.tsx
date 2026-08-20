'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Forbidden from '@/src/components/Forbidden';
import FormPanel, { Field } from '@/src/components/FormPanel';
import { inputCls } from '@/src/components/ui/tokens';
import { ServicesClient } from '@/src/generated/clients/ServicesClient';
import { TESTING_LANGUAGES, configLanguage, configTaskQueue } from '@/src/utils/services';

const servicesClient = new ServicesClient();

export default function ServiceEditPage() {
  const serviceId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isServiceManager: canManage } = usePermissions();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('');
  const [taskQueue, setTaskQueue] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: service, loading } = useResource(
    () => servicesClient.getServiceEndpointServiceAccountsServiceIdGet({ serviceId }),
    [serviceId],
    { enabled: canManage },
  );

  // Seed the form once service loads. Adjusting state during render (instead of in
  // an effect) is React's documented way to derive state from changed data: it
  // re-renders before committing, so there is no cascading render.
  const [seeded, setSeeded] = useState(service);
  if (service && service !== seeded) {
    setSeeded(service);
    setName(service.name);
    setDescription(service.description ?? '');
    setLanguage(configLanguage(service.config));
    setTaskQueue(configTaskQueue(service.config));
    setEnabled(service.enabled);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      // Rebuild config rather than patching it: `language` is not a column,
      // and sending a partial config would drop the other keys.
      const config: Record<string, unknown> = { ...(service?.config ?? {}) };
      if (taskQueue.trim()) config.temporal = { task_queue: taskQueue.trim() };
      else delete config.temporal;

      await servicesClient.updateServiceEndpointServiceAccountsServiceIdPatch({
        serviceId,
        body: {
          name: name.trim(),
          description: description.trim() || null,
          language: language || null,
          config,
          enabled,
        },
      });
      router.push(`/admin/services/${serviceId}`);
    } catch (e) {
      setSaving(false);
      setError(e instanceof Error ? e.message : 'Save failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or service-manager access is required." />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[
          { label: 'Services', href: '/admin/services' },
          { label: service?.name || 'Service', href: `/admin/services/${serviceId}` },
          { label: 'Edit' },
        ]}
        title="Edit service account"
        description="Slug and service type are immutable — both are join keys other records already point at."
        error={error}
        submitting={saving || loading}
        disabled={!name.trim()}
        submitLabel="Save"
        onCancel={() => router.push(`/admin/services/${serviceId}`)}
        onSubmit={save}
      >
        <Field label="Slug" hint="Immutable: examples bind to this string via meta.yaml.">
          <input value={service?.slug ?? ''} disabled className={`${inputCls} bg-gray-50 text-gray-500`} />
        </Field>
        <Field label="Service type" hint="Immutable: it determines default token scopes and dispatch rules.">
          <input value={service?.service_type_path ?? ''} disabled className={`${inputCls} bg-gray-50 text-gray-500`} />
        </Field>
        <Field label="Name" required>
          <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
        </Field>
        <Field label="Description">
          <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} />
        </Field>
        {language !== '' && (
          <Field label="Language" hint="Selects the test runner. Stored as config.language.">
            <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>
              {TESTING_LANGUAGES.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Temporal task queue" hint="Must equal the worker container's --queues= value.">
          <input value={taskQueue} onChange={(e) => setTaskQueue(e.target.value)} className={inputCls} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Enabled (disabling stops it resolving for new tests)
        </label>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
