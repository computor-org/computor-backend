'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, PageLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import Forbidden from '@/src/components/Forbidden';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Button from '@/src/components/ui/Button';
import Tabs from '@/src/components/ui/Tabs';
import MessageBody from '@/src/components/support/MessageBody';
import AttachmentList from '@/src/components/support/AttachmentList';
import { inputCls } from '@/src/components/ui/tokens';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { useResource } from '@/src/hooks/useResource';
import { useSupportCapabilities } from '@/src/hooks/useSupportCapabilities';
import {
  supportClient,
  type TicketGet,
  type TicketMessage,
  type TicketPriority,
  type TicketStatus,
  type TicketUpdate,
} from '@/src/clients/SupportClient';
import {
  PRIORITY_LABEL,
  STATUS_LABEL,
  STATUS_TONE,
  formatDateTime,
  userLabel,
} from '@/src/utils/support';

type ComposerMode = 'reply' | 'note';

export default function SupportTicketPage() {
  const id = useParams().id as string;
  const { user } = useAuth();
  const notify = useNotify();
  const { capabilities, loading: capsLoading } = useSupportCapabilities();
  const canView = !!capabilities?.can_view;
  const canManage = !!capabilities?.can_manage;

  const { data: ticket, loading, error, setData } = useResource(() => supportClient.get(id), [id], {
    enabled: canView,
  });
  const { data: agents } = useResource(() => supportClient.agents(), [], { enabled: canManage });

  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (capsLoading || (canView && loading && !ticket)) return <PageLoading />;
  if (!canView) return <Forbidden message="You do not have access to support tickets." />;
  if (!ticket) {
    return (
      <AuthenticatedLayout>
        <ListPageLayout>
          <PageHeader breadcrumbs={[{ label: 'Support', href: '/support' }, { label: 'Ticket' }]} title="Ticket" />
          <ErrorBanner>{error ?? 'Ticket not found.'}</ErrorBanner>
        </ListPageLayout>
      </AuthenticatedLayout>
    );
  }

  /** Run a mutation that returns the updated ticket. */
  const act = async (fn: () => Promise<TicketGet>): Promise<boolean> => {
    setBusy(true);
    setActionError(null);
    try {
      setData(await fn());
      return true;
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Action failed');
      return false;
    } finally {
      setBusy(false);
    }
  };
  const update = (body: TicketUpdate) => act(() => supportClient.update(ticket.id, body));

  const assignedToMe = !!user && ticket.assignee?.id === user.id;
  const events = ticket.events ?? [];

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Support', href: '/support' }, { label: `#${ticket.number}` }]}
          title={ticket.subject || '(no subject)'}
          subtitle={
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span className="font-mono">#{ticket.number}</span>
              <Badge tone={STATUS_TONE[ticket.status]} pill>
                {STATUS_LABEL[ticket.status]}
              </Badge>
              <span>Priority: {PRIORITY_LABEL[ticket.priority]}</span>
              <span>
                Reporter: {ticket.reporter_name || ticket.reporter_email || '—'}
                {ticket.reporter_name && ticket.reporter_email ? ` <${ticket.reporter_email}>` : ''}
              </span>
              <span>Team address: {ticket.mailbox_address ?? '—'}</span>
              <span>Assignee: {ticket.assignee ? userLabel(ticket.assignee) : 'unassigned'}</span>
              {ticket.restricted && <Badge tone="warning">restricted</Badge>}
            </div>
          }
        />

        <ErrorBanner>{actionError}</ErrorBanner>

        <ScrollArea>
          {canManage && (
            <div className="flex flex-wrap items-end gap-4 rounded-lg border border-rule bg-surface p-4">
              {!assignedToMe && (
                <Button disabled={busy} onClick={() => act(() => supportClient.claim(ticket.id))}>
                  Claim
                </Button>
              )}
              <label className="text-sm text-muted">
                Assignee
                <select
                  className={`${inputCls} mt-1 !w-56`}
                  disabled={busy}
                  value={ticket.assignee?.id ?? ''}
                  onChange={(e) =>
                    update(e.target.value ? { assignee_id: e.target.value } : { unassign: true })
                  }
                >
                  <option value="">Unassigned</option>
                  {(agents ?? []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {userLabel(a)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-muted">
                Status
                <select
                  className={`${inputCls} mt-1 !w-40`}
                  disabled={busy}
                  value={ticket.status}
                  onChange={(e) => update({ status: e.target.value as TicketStatus })}
                >
                  {(Object.keys(STATUS_LABEL) as TicketStatus[]).map((s) => (
                    <option key={s} value={s}>
                      {STATUS_LABEL[s]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-muted">
                Priority
                <select
                  className={`${inputCls} mt-1 !w-32`}
                  disabled={busy}
                  value={ticket.priority}
                  onChange={(e) => update({ priority: e.target.value as TicketPriority })}
                >
                  {(Object.keys(PRIORITY_LABEL) as TicketPriority[]).map((p) => (
                    <option key={p} value={p}>
                      {PRIORITY_LABEL[p]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          <section aria-label="Conversation" className="space-y-3">
            {ticket.messages.map((m) => (
              <MessageCard
                key={m.id}
                ticketId={ticket.id}
                message={m}
                busy={busy}
                canRetry={!!capabilities?.can_reply}
                onRetry={() => act(() => supportClient.retryMessage(ticket.id, m.id))}
              />
            ))}
          </section>

          <Composer
            ticket={ticket}
            canReply={!!capabilities?.can_reply}
            canNote={!!capabilities?.can_write_internal}
            teamAddresses={capabilities?.team_addresses ?? []}
            onSend={async (content, internal, fromAddress) => {
              const ok = await act(() =>
                supportClient.addMessage(ticket.id, {
                  content,
                  internal,
                  from_address: internal ? undefined : fromAddress || undefined,
                }),
              );
              if (ok) notify(internal ? 'Note added' : 'Reply queued for sending', 'success');
              return ok;
            }}
          />

          <details className="rounded-lg border border-rule bg-surface p-4">
            <summary className="cursor-pointer text-sm font-medium text-fg">
              Events ({events.length})
            </summary>
            <ul className="mt-3 space-y-1 text-sm text-muted">
              {events.map((ev) => (
                <li key={ev.id}>
                  <span className="text-xs">{formatDateTime(ev.created_at)}</span> — {ev.kind}
                  {ev.actor ? ` by ${userLabel(ev.actor)}` : ''}
                  {Object.keys(ev.data ?? {}).length > 0 && (
                    <span className="ml-1 font-mono text-xs">{JSON.stringify(ev.data)}</span>
                  )}
                </li>
              ))}
            </ul>
          </details>
        </ScrollArea>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}

function MessageCard({
  ticketId,
  message: m,
  busy,
  canRetry,
  onRetry,
}: {
  ticketId: string;
  message: TicketMessage;
  busy: boolean;
  canRetry: boolean;
  onRetry: () => void;
}) {
  const internal = m.visibility === 'internal' || m.direction === 'note';
  const outgoing = m.direction === 'out';
  const sender =
    userLabel(m.author) || m.from_name || m.from_address || (outgoing ? 'Support team' : 'Unknown sender');

  return (
    <article
      className={`rounded-lg border p-4 ${
        internal
          ? 'border-warn-line bg-warn-wash'
          : outgoing
            ? 'border-accent-line bg-accent-wash/40'
            : 'border-rule bg-surface'
      }`}
    >
      {internal && (
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-warn-text">
          Internal note - not visible to the reporter
        </p>
      )}
      <header className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="font-medium text-fg">{sender}</span>
        {!internal && m.from_address && <span className="text-xs text-muted">&lt;{m.from_address}&gt;</span>}
        {!internal && !outgoing && <Badge tone="muted">received</Badge>}
        {outgoing && <Badge tone="info">reply</Badge>}
        {outgoing && m.delivery_state && (
          <Badge
            tone={m.delivery_state === 'failed' ? 'error' : m.delivery_state === 'sent' ? 'success' : 'muted'}
          >
            {m.delivery_state}
          </Badge>
        )}
        <span className="ml-auto text-xs text-muted">{formatDateTime(m.created_at)}</span>
      </header>
      {!internal && m.to.length > 0 && <p className="mb-2 text-xs text-muted">To: {m.to.join(', ')}</p>}
      {outgoing && m.delivery_state === 'failed' && (
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <ErrorBanner>{m.delivery_error || 'Delivery failed.'}</ErrorBanner>
          {canRetry && (
            <Button size="sm" variant="secondary" disabled={busy} onClick={onRetry}>
              Retry
            </Button>
          )}
        </div>
      )}
      <MessageBody text={m.text} html={m.html} />
      <AttachmentList ticketId={ticketId} attachments={m.attachments} />
    </article>
  );
}

function Composer({
  ticket,
  canReply,
  canNote,
  teamAddresses,
  onSend,
}: {
  ticket: TicketGet;
  canReply: boolean;
  canNote: boolean;
  teamAddresses: string[];
  onSend: (content: string, internal: boolean, fromAddress: string) => Promise<boolean>;
}) {
  const [mode, setMode] = useState<ComposerMode>(canReply ? 'reply' : 'note');
  const [content, setContent] = useState('');
  const [from, setFrom] = useState(ticket.mailbox_address ?? '');
  const [confirming, setConfirming] = useState(false);
  const [sending, setSending] = useState(false);

  const tabs = [
    ...(canReply ? [{ id: 'reply' as const, label: 'Reply by mail' }] : []),
    ...(canNote ? [{ id: 'note' as const, label: 'Internal note' }] : []),
  ];
  if (tabs.length === 0) return null;

  const effectiveFrom = teamAddresses.includes(from) ? from : (teamAddresses[0] ?? '');
  const internal = mode === 'note';
  const empty = content.trim().length === 0;

  const send = async () => {
    setConfirming(false);
    setSending(true);
    const ok = await onSend(content, internal, effectiveFrom);
    setSending(false);
    if (ok) setContent('');
  };

  return (
    <section aria-label="Compose" className="space-y-3 rounded-lg border border-rule bg-surface p-4">
      <Tabs tabs={tabs} active={mode} onSelect={setMode} />
      {internal ? (
        <p className="text-sm text-warn-text">Internal note - not visible to the reporter.</p>
      ) : (
        <div className="flex flex-wrap items-end gap-4 text-sm text-muted">
          <label>
            From
            <select
              className={`${inputCls} mt-1 !w-64`}
              value={effectiveFrom}
              onChange={(e) => setFrom(e.target.value)}
            >
              {teamAddresses.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
          <label>
            To
            <input
              className={`${inputCls} mt-1 !w-64`}
              readOnly
              value={ticket.reporter_email ?? ''}
              aria-readonly="true"
            />
          </label>
        </div>
      )}
      <textarea
        className={`${inputCls} min-h-32`}
        value={content}
        maxLength={100_000}
        onChange={(e) => setContent(e.target.value)}
        aria-label={internal ? 'Internal note' : 'Reply text'}
        placeholder={internal ? 'Write an internal note…' : 'Write a reply to the reporter…'}
      />
      <div className="flex justify-end">
        <Button
          disabled={empty || (!internal && (!effectiveFrom || !ticket.reporter_email))}
          loading={sending}
          loadingLabel="Sending…"
          onClick={() => (internal ? void send() : setConfirming(true))}
        >
          {internal ? 'Add note' : 'Send reply'}
        </Button>
      </div>
      <ConfirmDialog
        open={confirming}
        title="Send reply by mail?"
        message={`This sends an email from ${effectiveFrom} to ${ticket.reporter_email ?? ''}. It cannot be recalled.`}
        confirmLabel="Send"
        onConfirm={() => void send()}
        onCancel={() => setConfirming(false)}
      />
    </section>
  );
}
