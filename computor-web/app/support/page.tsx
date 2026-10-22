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
import { supportClient, type TicketScope, type TicketStatus } from '@/src/clients/SupportClient';
import { STATUS_LABEL, STATUS_TONE, formatDateTime, userLabel } from '@/src/utils/support';

const PAGE_SIZE = 50;

const SCOPE_TABS: { id: TicketScope; label: string }[] = [
  { id: 'unassigned', label: 'Unassigned' },
  { id: 'mine', label: 'Mine' },
  { id: 'all', label: 'All' },
];

export default function SupportPage() {
  const { capabilities, loading: capsLoading } = useSupportCapabilities();
  const notify = useNotify();
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
    return <Forbidden message="You do not have access to support tickets." />;
  }

  const checkMail = async () => {
    setImporting(true);
    try {
      await supportClient.importNow();
      notify('Mail import started', 'info');
      setTimeout(() => {
        void refresh();
        setImporting(false);
      }, 4000);
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Could not start the mail import', 'error');
      setImporting(false);
    }
  };

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Support' }]}
          title="Support"
          subtitle="Team mail and problem reports."
          actions={
            capabilities?.can_manage ? (
              <Button variant="secondary" onClick={checkMail} loading={importing} loadingLabel="Checking…">
                Check mail now
              </Button>
            ) : undefined
          }
        />

        <Tabs
          tabs={SCOPE_TABS}
          active={scope}
          onSelect={(id) => {
            setScope(id);
            setPage(0);
          }}
        />

        <Toolbar
          end={<span className="text-sm text-muted">{total} ticket{total === 1 ? '' : 's'}</span>}
        >
          <select
            aria-label="Status filter"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as TicketStatus | '');
              setPage(0);
            }}
            className={`${inputCls} !w-auto`}
          >
            <option value="">Any status</option>
            {(Object.keys(STATUS_LABEL) as TicketStatus[]).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
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
              aria-label="Search tickets"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search subject, reporter…"
              maxLength={200}
              className={`${inputCls} !w-64`}
            />
            <Button type="submit" variant="secondary">
              Search
            </Button>
          </form>
        </Toolbar>

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : items.length === 0 ? (
          <EmptyState compact title="No tickets match." />
        ) : (
          <ScrollPanel>
            <Table>
              <Thead>
                <Tr>
                  <Th>#</Th>
                  <Th>Subject</Th>
                  <Th>Reporter</Th>
                  <Th>Team address</Th>
                  <Th>Status</Th>
                  <Th>Assignee</Th>
                  <Th>Last activity</Th>
                </Tr>
              </Thead>
              <Tbody>
                {items.map((t) => (
                  <Tr key={t.id}>
                    <Td>
                      <span className="font-mono text-xs">{t.number}</span>
                    </Td>
                    <Td>
                      <Link href={`/support/${t.id}`} className="font-medium text-accent-text hover:underline">
                        {t.subject || '(no subject)'}
                      </Link>
                      {t.restricted && (
                        <Badge tone="warning" className="ml-2" title="Restricted ticket">
                          restricted
                        </Badge>
                      )}
                    </Td>
                    <Td>
                      <div>{t.reporter_name || t.reporter_email || '—'}</div>
                      {t.reporter_name && t.reporter_email && (
                        <div className="text-xs text-muted">{t.reporter_email}</div>
                      )}
                    </Td>
                    <Td>
                      <span className="text-xs text-muted">{t.mailbox_address ?? '—'}</span>
                    </Td>
                    <Td>
                      <Badge tone={STATUS_TONE[t.status]} pill>
                        {STATUS_LABEL[t.status]}
                      </Badge>
                    </Td>
                    <Td>{t.assignee ? userLabel(t.assignee) : <span className="text-subtle">—</span>}</Td>
                    <Td>
                      <span className="text-xs text-muted">{formatDateTime(t.last_message_at ?? t.updated_at)}</span>
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
              Page {page + 1} of {pageCount}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <Button variant="secondary" size="sm" disabled={page + 1 >= pageCount} onClick={() => setPage(page + 1)}>
                Next
              </Button>
            </div>
          </div>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
