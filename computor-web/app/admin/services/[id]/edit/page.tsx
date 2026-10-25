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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const servicesClient = new ServicesClient();

const COPY = {
  de: {
    saveFailed: 'Speichern fehlgeschlagen',
    forbidden: 'Admin- oder Dienstverwalter-Rechte erforderlich.',
    breadcrumb: 'Dienste',
    fallbackName: 'Dienst',
    crumbEdit: 'Bearbeiten',
    title: 'Dienstkonto bearbeiten',
    description:
      'Slug und Diensttyp sind unveränderlich – beide sind Verknüpfungsschlüssel, auf die andere Datensätze bereits verweisen.',
    submit: 'Speichern',
    slugHint: 'Unveränderlich: Beispiele binden sich über die meta.yaml an diese Zeichenkette.',
    serviceType: 'Diensttyp',
    serviceTypeHint: 'Unveränderlich: Er bestimmt die Standard-Token-Berechtigungen und die Zuweisungsregeln.',
    name: 'Name',
    description_: 'Beschreibung',
    language: 'Sprache',
    languageHint: 'Wählt den Test-Runner aus. Wird als config.language gespeichert.',
    taskQueue: 'Temporal-Task-Queue',
    taskQueueHint: 'Muss dem Wert --queues= des Worker-Containers entsprechen.',
    enabled: 'Aktiviert (bei Deaktivierung wird der Dienst für neue Tests nicht mehr aufgelöst)',
  },
  en: {
    saveFailed: 'Save failed',
    forbidden: 'Admin or service-manager access is required.',
    breadcrumb: 'Services',
    fallbackName: 'Service',
    crumbEdit: 'Edit',
    title: 'Edit service account',
    description: 'Slug and service type are immutable — both are join keys other records already point at.',
    submit: 'Save',
    slugHint: 'Immutable: examples bind to this string via meta.yaml.',
    serviceType: 'Service type',
    serviceTypeHint: 'Immutable: it determines default token scopes and dispatch rules.',
    name: 'Name',
    description_: 'Description',
    language: 'Language',
    languageHint: 'Selects the test runner. Stored as config.language.',
    taskQueue: 'Temporal task queue',
    taskQueueHint: "Must equal the worker container's --queues= value.",
    enabled: 'Enabled (disabling stops it resolving for new tests)',
  },
} as const;

export default function ServiceEditPage() {
  const serviceId = useParams().id as string;
  const router = useRouter();
  const t = COPY[useUiLanguage()];
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
      setError(e instanceof Error ? e.message : t.saveFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[
          { label: t.breadcrumb, href: '/admin/services' },
          { label: service?.name || t.fallbackName, href: `/admin/services/${serviceId}` },
          { label: t.crumbEdit },
        ]}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving || loading}
        disabled={!name.trim()}
        submitLabel={t.submit}
        onCancel={() => router.push(`/admin/services/${serviceId}`)}
        onSubmit={save}
      >
        <Field label="Slug" hint={t.slugHint}>
          <input value={service?.slug ?? ''} disabled className={`${inputCls} bg-canvas text-muted`} />
        </Field>
        <Field label={t.serviceType} hint={t.serviceTypeHint}>
          <input value={service?.service_type_path ?? ''} disabled className={`${inputCls} bg-canvas text-muted`} />
        </Field>
        <Field label={t.name} required>
          <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} />
        </Field>
        <Field label={t.description_}>
          <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} />
        </Field>
        {language !== '' && (
          <Field label={t.language} hint={t.languageHint}>
            <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>
              {TESTING_LANGUAGES.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </Field>
        )}
        <Field label={t.taskQueue} hint={t.taskQueueHint}>
          <input value={taskQueue} onChange={(e) => setTaskQueue(e.target.value)} className={inputCls} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-body">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          {t.enabled}
        </label>
      </FormPanel>
    </AuthenticatedLayout>
  );
}
