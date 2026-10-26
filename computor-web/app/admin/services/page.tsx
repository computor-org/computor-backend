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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

const servicesClient = new ServicesClient();

const COPY = {
  de: {
    forbidden: 'Zum Verwalten von Dienstkonten sind Admin- oder Dienstverwalter-Rechte erforderlich.',
    breadcrumb: 'Dienste',
    title: 'Dienstkonten',
    subtitle:
      'Maschinenidentitäten – Testsysteme, Integrationen und KI-Agenten. Jedes ist ein Benutzerkonto ohne Anmeldung, das sich nur mit einem API-Token authentifiziert.',
    newService: 'Neuer Dienst',
    loading: 'Wird geladen …',
    empty: 'Noch keine Dienstkonten. Lege eines an, um ein Testsystem oder einen KI-Agenten zu registrieren.',
    name: 'Name',
    slug: 'Slug',
    type: 'Typ',
    language: 'Sprache',
    status: 'Status',
    lastSeen: 'Zuletzt gesehen',
    enabled: 'aktiviert',
    disabled: 'deaktiviert',
  },
  en: {
    forbidden: 'Admin or service-manager access is required to manage service accounts.',
    breadcrumb: 'Services',
    title: 'Service accounts',
    subtitle:
      'Machine identities — testing systems, integrations and AI agents. Each one is a user that cannot log in, authenticating only with an API token.',
    newService: 'New Service',
    loading: 'Loading…',
    empty: 'No service accounts yet. Create one to register a testing system or an AI agent.',
    name: 'Name',
    slug: 'Slug',
    type: 'Type',
    language: 'Language',
    status: 'Status',
    lastSeen: 'Last seen',
    enabled: 'enabled',
    disabled: 'disabled',
  },
} as const;

export default function ServicesPage() {
  const uiLanguage = useUiLanguage();
  const t = COPY[uiLanguage];
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isServiceManager: canManage } = usePermissions();

  const { data, loading, error } = useResource(
    () => servicesClient.listServicesEndpointServiceAccountsGet({}),
    [],
    { enabled: canManage },
  );
  const services = data ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message={t.forbidden} />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.breadcrumb }]}
          title={t.title}
          subtitle={t.subtitle}
          actions={
            <Link href="/admin/services/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
              {t.newService}
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : services.length === 0 ? (
          <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
            {t.empty}
          </div>
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <Tr>
                  <Th>{t.name}</Th>
                  <Th>{t.slug}</Th>
                  <Th>{t.type}</Th>
                  <Th>{t.language}</Th>
                  <Th>{t.status}</Th>
                  <Th>{t.lastSeen}</Th>
                </Tr>
              </Thead>
              <Tbody>
                {services.map((s) => {
                  const configLang = (s.config as Record<string, unknown> | undefined)?.language;
                  return (
                    <Tr key={s.id}>
                      <Td>
                        <Link href={`/admin/services/${s.id}`} className="font-medium text-accent-text hover:underline">
                          {s.name}
                        </Link>
                        {s.description && <div className="text-xs text-muted">{s.description}</div>}
                      </Td>
                      <Td><span className="font-mono text-xs">{s.slug}</span></Td>
                      <Td><span className="font-mono text-xs text-muted">{s.service_type_path ?? '—'}</span></Td>
                      <Td>{typeof configLang === 'string' ? <Badge color="blue">{configLang}</Badge> : <span className="text-subtle">—</span>}</Td>
                      <Td>{s.enabled ? <Badge color="green">{t.enabled}</Badge> : <Badge color="gray">{t.disabled}</Badge>}</Td>
                      <Td><span className="text-xs text-muted">{lastSeenLabel(s.last_seen_at, uiLanguage)}</span></Td>
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
