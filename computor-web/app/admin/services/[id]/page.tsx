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

const servicesClient = new ServicesClient();

export default function ServiceDetailPage() {
  const serviceId = useParams().id as string;
  const router = useRouter();
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
      setArchiveError(e instanceof Error ? e.message : 'Archive failed');
      setNeedsForce(true);
      setConfirmArchive(false);
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <Forbidden
        message="Admin or service-manager access is required."
        backLink="/admin/services"
        backText="Back"
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
          breadcrumbs={[{ label: 'Services', href: '/admin/services' }, { label: service?.name || 'Service' }]}
          title={service?.name || 'Service'}
          subtitle={
            service ? (
              <span className="font-mono text-sm text-gray-500">
                {service.slug} · {service.service_type_path ?? 'no type'}
              </span>
            ) : undefined
          }
          actions={
            service ? (
              <>
                <Link
                  href={`/admin/services/${service.id}/edit`}
                  className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Edit
                </Link>
                <button
                  onClick={() => setConfirmArchive(true)}
                  className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50"
                >
                  Archive
                </button>
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : service ? (
          <ScrollArea className="space-y-6">
            {archiveError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                <p>{archiveError}</p>
                {needsForce && (
                  <button
                    onClick={() => void doArchive(true)}
                    className="mt-3 px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700"
                  >
                    Archive anyway
                  </button>
                )}
              </div>
            )}

            <div className="bg-white border border-gray-200 rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Status</dt>
                <dd>{service.enabled ? <Badge color="green">enabled</Badge> : <Badge color="gray">disabled</Badge>}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Last seen</dt>
                <dd className="text-gray-900">
                  {lastSeenLabel(service.last_seen_at)}
                  {!service.last_seen_at && (
                    <span className="ml-2 text-xs text-amber-700">worker has never checked in</span>
                  )}
                </dd>
              </div>
              {language && (
                <div>
                  <dt className="text-gray-500">Language</dt>
                  <dd className="text-gray-900">
                    <Badge color="blue">{language}</Badge>
                    <span className="ml-2 text-xs text-gray-400">selects the test runner</span>
                  </dd>
                </div>
              )}
              {taskQueue && (
                <div>
                  <dt className="text-gray-500">Temporal task queue</dt>
                  <dd className="font-mono text-gray-900">{taskQueue}</dd>
                </div>
              )}
              <div>
                <dt className="text-gray-500">Service user</dt>
                <dd className="font-mono text-xs text-gray-900">{service.user_id}</dd>
              </div>
              {service.created_at && (
                <div>
                  <dt className="text-gray-500">Created</dt>
                  <dd className="text-gray-900">{new Date(service.created_at).toLocaleString()}</dd>
                </div>
              )}
              {service.description && (
                <div className="sm:col-span-2">
                  <dt className="text-gray-500">Description</dt>
                  <dd className="text-gray-900">{service.description}</dd>
                </div>
              )}
              <div className="sm:col-span-2">
                <dt className="text-gray-500 mb-1">Configuration</dt>
                <dd>
                  <pre className="bg-gray-50 border border-gray-200 rounded p-3 text-xs overflow-x-auto">
                    {JSON.stringify(service.config ?? {}, null, 2)}
                  </pre>
                </dd>
              </div>
            </div>

            <p className="text-xs text-gray-400">
              The slug <span className="font-mono">{service.slug}</span> is the binding to your examples: an
              assignment runs on this service when its <span className="font-mono">meta.yaml</span> declares{' '}
              <span className="font-mono">properties.executionBackend.slug: {service.slug}</span>. It is immutable
              because changing it would silently orphan every assignment already bound to it.
            </p>

            <ServiceTokensSection userId={service.user_id} serviceName={service.name} />

            {isAgent && <ServiceCoursesSection userId={service.user_id} />}
          </ScrollArea>
        ) : null}
      </ListPageLayout>

      {confirmArchive && service && (
        <ConfirmDeleteDialog
          title={`Archive service “${service.name}”?`}
          message="The service stops resolving for new tests. Its user and tokens are kept, and the slug stays taken — archiving is not a way to free a slug for reuse. Blocked if course contents or example versions still depend on it."
          confirmWord={service.slug}
          onConfirm={() => doArchive(false)}
          onClose={() => setConfirmArchive(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
