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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const servicesClient = new ServicesClient();
const serviceTypesClient = new ServiceTypesClient();

const COPY = {
  de: {
    createFailed: 'Erstellen fehlgeschlagen',
    forbidden: 'Admin- oder Dienstverwalter-Rechte erforderlich.',
    breadcrumb: 'Dienste',
    crumbNew: 'Neu',
    title: 'Neues Dienstkonto',
    description:
      'Legt ein nicht-menschliches Benutzerkonto an, das sich mit einem API-Token authentifiziert. Das Token erzeugst du im nächsten Schritt.',
    submit: 'Erstellen',
    slug: 'Kennung (Slug)',
    email: 'E-Mail',
    slugExample: 'beispiel.exec.py',
    nameExample: 'Beispiel-Python-Runner',
    emailExample: 'beispiel-runner@computor.local',
    slugHint:
      'Kleinbuchstaben, Ziffern, Punkte und Bindestriche. Bei einem Testdienst muss er mit properties.executionBackend.slug in der meta.yaml deiner Beispiele übereinstimmen – diese Zeichenkette bindet eine Aufgabe an diesen Dienst. Er ist nur ein Bezeichner und wählt nicht den Test-Runner aus.',
    name: 'Name',
    description_: 'Beschreibung',
    serviceType: 'Diensttyp',
    serviceTypeHint: 'Bestimmt die Standard-Token-Berechtigungen und ob dieser Dienst Tests ausführt.',
    selectType: 'Typ auswählen …',
    emailHint: 'Identifiziert den Dienstbenutzer. Üblicherweise ist der Standard <slug>@computor.local.',
    language: 'Sprache',
    languageHint: 'Wählt den Test-Runner aus. Wird als config.language gespeichert.',
    taskQueue: 'Temporal-Task-Queue',
    taskQueueHint:
      'Muss dem Wert --queues= des Worker-Containers entsprechen, sonst bleiben eingereichte Tests für immer in der Warteschlange.',
  },
  en: {
    createFailed: 'Create failed',
    forbidden: 'Admin or service-manager access is required.',
    breadcrumb: 'Services',
    crumbNew: 'New',
    title: 'New service account',
    description:
      'Creates a non-human user that authenticates with an API token. Mint the token on the next screen.',
    submit: 'Create',
    slug: 'Slug',
    email: 'Email',
    slugExample: 'acme.exec.py',
    nameExample: 'Acme Python Runner',
    emailExample: 'acme-runner@computor.local',
    slugHint:
      "Lowercase letters, digits, dots and hyphens. For a testing service this must match properties.executionBackend.slug in your examples' meta.yaml — that string is what binds an assignment to this service. It is an identifier only; it does not select the test runner.",
    name: 'Name',
    description_: 'Description',
    serviceType: 'Service type',
    serviceTypeHint: 'Determines the default token scopes and whether this service runs tests.',
    selectType: 'Select a type…',
    emailHint: 'Identifies the service user. Defaults are conventionally <slug>@computor.local.',
    language: 'Language',
    languageHint: 'Selects the test runner. Stored as config.language.',
    taskQueue: 'Temporal task queue',
    taskQueueHint:
      "Must equal the worker container's --queues= value, or submitted tests sit queued forever.",
  },
} as const;

export default function ServiceCreatePage() {
  const router = useRouter();
  const t = COPY[useUiLanguage()];
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
      setError(e instanceof Error ? e.message : t.createFailed);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <FormPanel
        breadcrumbs={[{ label: t.breadcrumb, href: '/admin/services' }, { label: t.crumbNew }]}
        title={t.title}
        description={t.description}
        error={error}
        submitting={saving}
        disabled={!slug.trim() || !name.trim() || !serviceTypePath}
        submitLabel={t.submit}
        onCancel={() => router.push('/admin/services')}
        onSubmit={save}
      >
        <Field
          label={t.slug}
          required
          hint={t.slugHint}
        >
          <input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder={t.slugExample} className={inputCls} />
        </Field>
        <Field label={t.name} required>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t.nameExample} className={inputCls} />
        </Field>
        <Field label={t.description_}>
          <input value={description} onChange={(e) => setDescription(e.target.value)} className={inputCls} />
        </Field>
        <Field label={t.serviceType} required hint={t.serviceTypeHint}>
          <select value={serviceTypePath} onChange={(e) => setServiceTypePath(e.target.value)} className={inputCls}>
            <option value="">{t.selectType}</option>
            {types.map((t) => (
              <option key={t.id} value={t.path}>{t.path} — {t.name}</option>
            ))}
          </select>
        </Field>
        <Field label={t.email} hint={t.emailHint}>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t.emailExample} className={inputCls} />
        </Field>

        {isTesting && (
          <>
            <Field label={t.language} required hint={t.languageHint}>
              <select value={language} onChange={(e) => setLanguage(e.target.value)} className={inputCls}>
                {TESTING_LANGUAGES.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </Field>
            <Field label={t.taskQueue} hint={t.taskQueueHint}>
              <input value={taskQueue} onChange={(e) => setTaskQueue(e.target.value)} placeholder="testing" className={inputCls} />
            </Field>
          </>
        )}
      </FormPanel>
    </AuthenticatedLayout>
  );
}
