'use client';

import Link from 'next/link';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import { ServicesClient } from '@/src/generated/clients/ServicesClient';
import { lastSeenLabel } from '@/src/utils/services';

const servicesClient = new ServicesClient();

export default function ServicesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isServiceManager: canManage } = usePermissions();

  const { data, loading, error } = useResource(
    () => servicesClient.listServicesEndpointServiceAccountsGet({}),
    [],
    { enabled: canManage },
  );
  const services = data ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="Admin or service-manager access is required to manage service accounts." />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Services' }]}
          title="Service accounts"
          subtitle="Machine identities — testing systems, integrations and AI agents. Each one is a user that cannot log in, authenticating only with an API token."
          actions={
            <Link href="/admin/services/create" className="px-4 py-2 bg-blue-600 text-on-accent rounded-lg text-sm font-medium hover:bg-blue-700">
              New Service
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : services.length === 0 ? (
          <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
            No service accounts yet. Create one to register a testing system or an AI agent.
          </div>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <Tr>
                  <Th>Name</Th>
                  <Th>Slug</Th>
                  <Th>Type</Th>
                  <Th>Language</Th>
                  <Th>Status</Th>
                  <Th>Last seen</Th>
                </Tr>
              </Thead>
              <Tbody>
                {services.map((s) => {
                  const language = (s.config as Record<string, unknown> | undefined)?.language;
                  return (
                    <Tr key={s.id}>
                      <Td>
                        <Link href={`/admin/services/${s.id}`} className="font-medium text-blue-600 hover:underline">
                          {s.name}
                        </Link>
                        {s.description && <div className="text-xs text-muted">{s.description}</div>}
                      </Td>
                      <Td><span className="font-mono text-xs">{s.slug}</span></Td>
                      <Td><span className="font-mono text-xs text-muted">{s.service_type_path ?? '—'}</span></Td>
                      <Td>{typeof language === 'string' ? <Badge color="blue">{language}</Badge> : <span className="text-subtle">—</span>}</Td>
                      <Td>{s.enabled ? <Badge color="green">enabled</Badge> : <Badge color="gray">disabled</Badge>}</Td>
                      <Td><span className="text-xs text-muted">{lastSeenLabel(s.last_seen_at)}</span></Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
