'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import ServiceTokensSection from '@/src/components/services/ServiceTokensSection';
import ServiceCoursesSection from '@/src/components/services/ServiceCoursesSection';
import { ServicesClient } from '@/src/generated/clients/ServicesClient';
import { configLanguage, configTaskQueue, lastSeenLabel } from '@/src/utils/services';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';

const servicesClient = new ServicesClient();

const COPY = {
  de: {
    archiveFailed: 'Archivieren fehlgeschlagen',
    forbidden: 'Admin- oder Dienstverwalter-Rechte erforderlich.',
    back: 'Zurück',
    breadcrumb: 'Dienste',
    fallbackName: 'Dienst',
    noType: 'kein Typ',
    edit: 'Bearbeiten',
    archive: 'Archivieren',
    loading: 'Wird geladen …',
    archiveAnyway: 'Trotzdem archivieren',
    status: 'Status',
    enabled: 'aktiviert',
    disabled: 'deaktiviert',
    lastSeen: 'Zuletzt gesehen',
    neverCheckedIn: 'Worker hat sich noch nie gemeldet',
    language: 'Sprache',
    selectsRunner: 'wählt den Test-Runner aus',
    taskQueue: 'Temporal-Task-Queue',
    serviceUser: 'Dienstbenutzer',
    created: 'Erstellt',
    description: 'Beschreibung',
    configuration: 'Konfiguration',
    archiveTitle: (name: string) => `Dienst „${name}“ archivieren?`,
    archiveMessage:
      'Der Dienst wird für neue Tests nicht mehr aufgelöst. Sein Benutzerkonto und seine Tokens bleiben erhalten, und der Slug bleibt vergeben – Archivieren ist kein Weg, einen Slug zur Wiederverwendung freizugeben. Nicht möglich, solange Kursinhalte oder Beispielversionen noch von ihm abhängen.',
  },
  en: {
    archiveFailed: 'Archive failed',
    forbidden: 'Admin or service-manager access is required.',
    back: 'Back',
    breadcrumb: 'Services',
    fallbackName: 'Service',
    noType: 'no type',
    edit: 'Edit',
    archive: 'Archive',
    loading: 'Loading…',
    archiveAnyway: 'Archive anyway',
    status: 'Status',
    enabled: 'enabled',
    disabled: 'disabled',
    lastSeen: 'Last seen',
    neverCheckedIn: 'worker has never checked in',
    language: 'Language',
    selectsRunner: 'selects the test runner',
    taskQueue: 'Temporal task queue',
    serviceUser: 'Service user',
    created: 'Created',
    description: 'Description',
    configuration: 'Configuration',
    archiveTitle: (name: string) => `Archive service “${name}”?`,
    archiveMessage:
      'The service stops resolving for new tests. Its user and tokens are kept, and the slug stays taken — archiving is not a way to free a slug for reuse. Blocked if course contents or example versions still depend on it.',
  },
} as const;

export default function ServiceDetailPage() {
  const serviceId = useParams().id as string;
  const router = useRouter();
  const language_ = useUiLanguage();
  const t = COPY[language_];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isServiceManager: canManage } = usePermissions();

  const [confirmArchive, setConfirmArchive] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);
  const [needsForce, setNeedsForce] = useState(false);

  const { data: service, loading, error } = useResource(
    () => servicesClient.getServiceEndpointServiceAccountsServiceIdGet({ serviceId }),
    [serviceId],
    { enabled: canManage },
  );

  async function doArchive(force: boolean) {
    try {
      await servicesClient.deleteServiceEndpointServiceAccountsServiceIdDelete({ serviceId, force });
      router.push('/admin/services');
    } catch (e) {
      // A 409 SERVICE_HAS_DEPENDENTS means course contents or example
      // versions still point at this service; offer the override rather than
      // making the admin guess.
      setArchiveError(e instanceof Error ? e.message : t.archiveFailed);
      setNeedsForce(true);
      setConfirmArchive(false);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden
        message={t.forbidden}
        backLink="/admin/services"
        backText={t.back}
      />
    );
  }

  const language = configLanguage(service?.config);
  const taskQueue = configTaskQueue(service?.config);
  const isAgent = service?.service_type_path === 'agent';

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: t.breadcrumb, href: '/admin/services' }, { label: service?.name || t.fallbackName }]}
          title={service?.name || t.fallbackName}
          subtitle={
            service ? (
              <span className="font-mono text-sm text-muted">
                {service.slug} · {service.service_type_path ?? t.noType}
              </span>
            ) : undefined
          }
          actions={
            service ? (
              <>
                <Link
                  href={`/admin/services/${service.id}/edit`}
                  className="px-3 py-2 text-sm font-medium text-body border border-rule-strong rounded-lg hover:bg-canvas"
                >
                  {t.edit}
                </Link>
                <button
                  onClick={() => setConfirmArchive(true)}
                  className="px-3 py-2 text-sm font-medium text-danger-text border border-danger-line rounded-lg hover:bg-danger-wash"
                >
                  {t.archive}
                </button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : service ? (
          <ScrollArea>
            {archiveError && (
              <div className="rounded-lg border border-danger-line bg-danger-wash p-4 text-sm text-danger-text">
                <p>{archiveError}</p>
                {needsForce && (
                  <button
                    onClick={() => void doArchive(true)}
                    className="mt-3 px-3 py-1.5 text-xs font-medium text-on-accent bg-danger rounded hover:bg-danger-hover"
                  >
                    {t.archiveAnyway}
                  </button>
                )}
              </div>
            )}

            <div className="bg-surface border border-rule rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="text-muted">{t.status}</dt>
                <dd>{service.enabled ? <Badge color="green">{t.enabled}</Badge> : <Badge color="gray">{t.disabled}</Badge>}</dd>
              </div>
              <div>
                <dt className="text-muted">{t.lastSeen}</dt>
                <dd className="text-fg">
                  {lastSeenLabel(service.last_seen_at, language_)}
                  {!service.last_seen_at && (
                    <span className="ml-2 text-xs text-warn-text">{t.neverCheckedIn}</span>
                  )}
                </dd>
              </div>
              {language && (
                <div>
                  <dt className="text-muted">{t.language}</dt>
                  <dd className="text-fg">
                    <Badge color="blue">{language}</Badge>
                    <span className="ml-2 text-xs text-subtle">{t.selectsRunner}</span>
                  </dd>
                </div>
              )}
              {taskQueue && (
                <div>
                  <dt className="text-muted">{t.taskQueue}</dt>
                  <dd className="font-mono text-fg">{taskQueue}</dd>
                </div>
              )}
              <div>
                <dt className="text-muted">{t.serviceUser}</dt>
                <dd className="font-mono text-xs text-fg">{service.user_id}</dd>
              </div>
              {service.created_at && (
                <div>
                  <dt className="text-muted">{t.created}</dt>
                  <dd className="text-fg">{formatDateTime(service.created_at, language_)}</dd>
                </div>
              )}
              {service.description && (
                <div className="sm:col-span-2">
                  <dt className="text-muted">{t.description}</dt>
                  <dd className="text-fg">{service.description}</dd>
                </div>
              )}
              <div className="sm:col-span-2">
                <dt className="text-muted mb-1">{t.configuration}</dt>
                <dd>
                  <pre className="bg-canvas border border-rule rounded p-3 text-xs overflow-x-auto">
                    {JSON.stringify(service.config ?? {}, null, 2)}
                  </pre>
                </dd>
              </div>
            </div>

            <p className="text-xs text-subtle">
              {language_ === 'de' ? (
                <>
                  Der Slug <span className="font-mono">{service.slug}</span> ist die Bindung an deine Beispiele: Eine
                  Aufgabe läuft auf diesem Dienst, wenn ihre <span className="font-mono">meta.yaml</span>{' '}
                  <span className="font-mono">properties.executionBackend.slug: {service.slug}</span> angibt. Er ist
                  unveränderlich, weil eine Änderung stillschweigend alle bereits gebundenen Aufgaben verwaisen
                  ließe.
                </>
              ) : (
                <>
                  The slug <span className="font-mono">{service.slug}</span> is the binding to your examples: an
                  assignment runs on this service when its <span className="font-mono">meta.yaml</span> declares{' '}
                  <span className="font-mono">properties.executionBackend.slug: {service.slug}</span>. It is immutable
                  because changing it would silently orphan every assignment already bound to it.
                </>
              )}
            </p>

            <ServiceTokensSection userId={service.user_id} serviceName={service.name} />

            {isAgent && <ServiceCoursesSection userId={service.user_id} />}
          </ScrollArea>
        ) : null}
      </ListPageLayout>

      {confirmArchive && service && (
        <ConfirmDeleteDialog
          title={t.archiveTitle(service.name)}
          message={t.archiveMessage}
          confirmWord={service.slug}
          onConfirm={() => doArchive(false)}
          onClose={() => setConfirmArchive(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
