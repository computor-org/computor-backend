'use client';

import { useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading, PageLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import EmptyState from '@/src/components/EmptyState';
import Forbidden from '@/src/components/Forbidden';
import Tabs from '@/src/components/ui/Tabs';
import Toolbar from '@/src/components/ui/Toolbar';
import Button from '@/src/components/ui/Button';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import { inputCls } from '@/src/components/ui/tokens';
import { useResource } from '@/src/hooks/useResource';
import { useSupportCapabilities } from '@/src/hooks/useSupportCapabilities';
import { useNotify } from '@/src/contexts/NotificationContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { supportClient, type TicketScope, type TicketStatus } from '@/src/clients/SupportClient';
import { STATUS_TONE, userLabel } from '@/src/utils/support';

const PAGE_SIZE = 50;

const SCOPES: TicketScope[] = ['unassigned', 'mine', 'all'];
const STATUSES: TicketStatus[] = ['open', 'in_progress', 'waiting', 'done'];

function formatDateTime(iso: string | null | undefined, locale: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString(locale);
}

const COPY = {
  de: {
    forbidden: 'Du hast keinen Zugriff auf Support-Anfragen.',
    importStarted: 'Mail-Import gestartet',
    importFailed: 'Der Mail-Import konnte nicht gestartet werden',
    title: 'Support',
    subtitle: 'Team-Mails und Problemmeldungen.',
    checking: 'Wird geprüft …',
    checkMail: 'Jetzt Mails abrufen',
    tabs: { unassigned: 'Nicht zugewiesen', mine: 'Meine', all: 'Alle' } as Record<TicketScope, string>,
    count: (n: number) => (n === 1 ? '1 Anfrage' : `${n} Anfragen`),
    statusFilter: 'Statusfilter',
    anyStatus: 'Beliebiger Status',
    status: { open: 'Offen', in_progress: 'In Bearbeitung', waiting: 'Wartet', done: 'Erledigt' } as Record<TicketStatus, string>,
    searchLabel: 'Anfragen suchen',
    searchPlaceholder: 'Betreff, Absender suchen …',
    search: 'Suchen',
    loading: 'Wird geladen …',
    empty: 'Keine passenden Anfragen.',
    subject: 'Betreff',
    reporter: 'Absender',
    teamAddress: 'Team-Adresse',
    statusCol: 'Status',
    assignee: 'Zugewiesen an',
    lastActivity: 'Letzte Aktivität',
    noSubject: '(kein Betreff)',
    restrictedTitle: 'Eingeschränkte Anfrage',
    restricted: 'eingeschränkt',
    page: (n: number, total: number) => `Seite ${n} von ${total}`,
    previous: 'Zurück',
    next: 'Weiter',
  },
  en: {
    forbidden: 'You do not have access to support tickets.',
    importStarted: 'Mail import started',
    importFailed: 'Could not start the mail import',
    title: 'Support',
    subtitle: 'Team mail and problem reports.',
    checking: 'Checking…',
    checkMail: 'Check mail now',
    tabs: { unassigned: 'Unassigned', mine: 'Mine', all: 'All' } as Record<TicketScope, string>,
    count: (n: number) => `${n} ticket${n === 1 ? '' : 's'}`,
    statusFilter: 'Status filter',
    anyStatus: 'Any status',
    status: { open: 'Open', in_progress: 'In progress', waiting: 'Waiting', done: 'Done' } as Record<TicketStatus, string>,
    searchLabel: 'Search tickets',
    searchPlaceholder: 'Search subject, reporter…',
    search: 'Search',
    loading: 'Loading…',
    empty: 'No tickets match.',
    subject: 'Subject',
    reporter: 'Reporter',
    teamAddress: 'Team address',
    statusCol: 'Status',
    assignee: 'Assignee',
    lastActivity: 'Last activity',
    noSubject: '(no subject)',
    restrictedTitle: 'Restricted ticket',
    restricted: 'restricted',
    page: (n: number, total: number) => `Page ${n} of ${total}`,
    previous: 'Previous',
    next: 'Next',
  },
};

export default function SupportPage() {
  const { capabilities, loading: capsLoading } = useSupportCapabilities();
  const notify = useNotify();
  const language = useUiLanguage();
  const t = COPY[language];
  const locale = language === 'de' ? 'de-AT' : undefined;
  const canView = !!capabilities?.can_view;

  const [scope, setScope] = useState<TicketScope>('unassigned');
  const [status, setStatus] = useState<TicketStatus | ''>('');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [importing, setImporting] = useState(false);

  const { data, loading, error, refresh } = useResource(
    () => supportClient.list({ scope, status, search, skip: page * PAGE_SIZE, limit: PAGE_SIZE }),
    [scope, status, search, page],
    { enabled: canView },
  );
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  if (capsLoading) return <PageLoading width="wide" />;
  if (!canView) {
    return <Forbidden message={t.forbidden} />;
  }

  const checkMail = async () => {
    setImporting(true);
    try {
      await supportClient.importNow();
      notify(t.importStarted, 'info');
      setTimeout(() => {
        void refresh();
        setImporting(false);
      }, 4000);
    } catch (e) {
      notify(e instanceof Error ? e.message : t.importFailed, 'error');
      setImporting(false);
    }
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.title }]}
          title={t.title}
          subtitle={t.subtitle}
          actions={
            capabilities?.can_manage ? (
              <Button variant="secondary" onClick={checkMail} loading={importing} loadingLabel={t.checking}>
                {t.checkMail}
              </Button>
            ) : undefined
          }
        />

        <Tabs
          tabs={SCOPES.map((id) => ({ id, label: t.tabs[id] }))}
          active={scope}
          onSelect={(id) => {
            setScope(id);
            setPage(0);
          }}
        />

        <Toolbar
          end={<span className="text-sm text-muted">{t.count(total)}</span>}
        >
          <select
            aria-label={t.statusFilter}
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as TicketStatus | '');
              setPage(0);
            }}
            className={`${inputCls} !w-auto`}
          >
            <option value="">{t.anyStatus}</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {t.status[s]}
              </option>
            ))}
          </select>
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setSearch(searchInput.trim());
              setPage(0);
            }}
          >
            <input
              type="search"
              aria-label={t.searchLabel}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={t.searchPlaceholder}
              maxLength={200}
              className={`${inputCls} !w-64`}
            />
            <Button type="submit" variant="secondary">
              {t.search}
            </Button>
          </form>
        </Toolbar>

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : items.length === 0 ? (
          <EmptyState compact title={t.empty} />
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>{t.subject}</Th>
                  <Th>{t.reporter}</Th>
                  <Th>{t.teamAddress}</Th>
                  <Th>{t.statusCol}</Th>
                  <Th>{t.assignee}</Th>
                  <Th>{t.lastActivity}</Th>
                </Tr>
              </Thead>
              <Tbody>
                {items.map((row) => (
                  <Tr key={row.id}>
                    <Td>
                      <span className="font-mono text-xs">{row.number}</span>
                    </Td>
                    <Td>
                      <Link href={`/support/${row.id}`} className="font-medium text-accent-text hover:underline">
                        {row.subject || t.noSubject}
                      </Link>
                      {row.restricted && (
                        <Badge tone="warning" className="ml-2" title={t.restrictedTitle}>
                          {t.restricted}
                        </Badge>
                      )}
                    </Td>
                    <Td>
                      <div>{row.reporter_name || row.reporter_email || '—'}</div>
                      {row.reporter_name && row.reporter_email && (
                        <div className="text-xs text-muted">{row.reporter_email}</div>
                      )}
                    </Td>
                    <Td>
                      <span className="text-xs text-muted">{row.mailbox_address ?? '—'}</span>
                    </Td>
                    <Td>
                      <Badge tone={STATUS_TONE[row.status]} pill>
                        {t.status[row.status]}
                      </Badge>
                    </Td>
                    <Td>{row.assignee ? userLabel(row.assignee) : <span className="text-subtle">—</span>}</Td>
                    <Td>
                      <span className="text-xs text-muted">{formatDateTime(row.last_message_at ?? row.updated_at, locale)}</span>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </ScrollPanel>
        )}

        {total > PAGE_SIZE && (
          <div className="shrink-0 flex items-center justify-between text-sm text-muted">
            <span>
              {t.page(page + 1, pageCount)}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
                {t.previous}
              </Button>
              <Button variant="secondary" size="sm" disabled={page + 1 >= pageCount} onClick={() => setPage(page + 1)}>
                {t.next}
              </Button>
            </div>
          </div>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
