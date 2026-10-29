'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, PageLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import ConfirmDialog from '@/src/components/ConfirmDialog';
import Button from '@/src/components/ui/Button';
import Tabs from '@/src/components/ui/Tabs';
import MessageBody from '@/src/components/support/MessageBody';
import AttachmentList from '@/src/components/support/AttachmentList';
import { ReportContext, PublishPanel } from '@/src/components/support/ReportPanels';
import { inputCls } from '@/src/components/ui/tokens';
import { useAuth } from '@/src/contexts/AuthContext';
import { useNotify } from '@/src/contexts/NotificationContext';
import { useResource } from '@/src/hooks/useResource';
import { useUiLanguage, type UiLanguage } from '@/src/hooks/useUiLanguage';
import { useSupportCapabilities } from '@/src/hooks/useSupportCapabilities';
import {
  supportClient,
  type TicketGet,
  type TicketMessage,
  type TicketPriority,
  type TicketStatus,
  type TicketUpdate,
} from '@/src/clients/SupportClient';
import { STATUS_TONE, userLabel } from '@/src/utils/support';
import { localeFor } from '@/src/utils/locale';

type ComposerMode = 'reply' | 'note';

const STATUSES: TicketStatus[] = ['open', 'in_progress', 'waiting', 'done'];
const PRIORITIES: TicketPriority[] = ['low', 'normal', 'high'];

function formatDateTime(iso: string | null | undefined, locale: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString(locale);
}

const COPY: Record<UiLanguage, {
  support: string; ticket: string; notFound: string; actionFailed: string; noSubject: string;
  status: Record<TicketStatus, string>; priorities: Record<TicketPriority, string>;
  priority: string; reporter: string; teamAddress: string; assignee: string; unassignedLower: string; restricted: string;
  claim: string; unassigned: string; statusLabel: string; conversation: string; noteAdded: string; replyQueued: string;
  events: string; by: string; supportTeam: string; unknownSender: string; internalBanner: string; received: string;
  reply: string; delivery: Record<string, string>; to: string; deliveryFailed: string; retry: string;
  replyByMail: string; internalNote: string; compose: string; internalHint: string; from: string; replyText: string;
  notePlaceholder: string; replyPlaceholder: string; sending: string; addNote: string; sendReply: string;
  confirmTitle: string; confirmMessage: (from: string, to: string) => string; send: string;
  myReports: string; you: string; followUp: string; followUpPlaceholder: string; replyInApp: string;
  replyInAppPlaceholder: string; replySent: string; followUpSent: string; reportedBy: string;
}> = {
  de: {
    support: 'Support',
    ticket: 'Anfrage',
    notFound: 'Anfrage nicht gefunden.',
    actionFailed: 'Aktion fehlgeschlagen',
    noSubject: '(kein Betreff)',
    status: { open: 'Offen', in_progress: 'In Bearbeitung', waiting: 'Wartet', done: 'Erledigt' },
    priorities: { low: 'Niedrig', normal: 'Normal', high: 'Hoch' },
    priority: 'Priorität',
    reporter: 'Absender',
    teamAddress: 'Team-Adresse',
    assignee: 'Zugewiesen an',
    unassignedLower: 'nicht zugewiesen',
    restricted: 'eingeschränkt',
    claim: 'Übernehmen',
    unassigned: 'Nicht zugewiesen',
    statusLabel: 'Status',
    conversation: 'Unterhaltung',
    noteAdded: 'Notiz hinzugefügt',
    replyQueued: 'Antwort zum Versand eingereiht',
    events: 'Ereignisse',
    by: 'von',
    supportTeam: 'Support-Team',
    unknownSender: 'Unbekannter Absender',
    internalBanner: 'Interne Notiz, für den Absender nicht sichtbar',
    received: 'empfangen',
    reply: 'Antwort',
    delivery: { sent: 'gesendet', failed: 'fehlgeschlagen', queued: 'eingereiht', pending: 'ausstehend' },
    to: 'An',
    deliveryFailed: 'Zustellung fehlgeschlagen.',
    retry: 'Erneut versuchen',
    replyByMail: 'Per Mail antworten',
    internalNote: 'Interne Notiz',
    compose: 'Verfassen',
    internalHint: 'Interne Notiz, für den Absender nicht sichtbar.',
    from: 'Von',
    replyText: 'Antworttext',
    notePlaceholder: 'Interne Notiz schreiben …',
    replyPlaceholder: 'Antwort an den Absender schreiben …',
    sending: 'Wird gesendet …',
    addNote: 'Notiz hinzufügen',
    sendReply: 'Antwort senden',
    confirmTitle: 'Antwort per Mail senden?',
    confirmMessage: (from, to) => `Dies sendet eine E-Mail von ${from} an ${to}. Sie kann nicht zurückgeholt werden.`,
    send: 'Senden',
    myReports: 'Meine Meldungen',
    you: 'Du',
    followUp: 'Antworten',
    followUpPlaceholder: 'Ergänzung oder Antwort an das Support-Team schreiben …',
    replyInApp: 'In der App antworten',
    replyInAppPlaceholder: 'Antwort an die meldende Person schreiben (wird in der App angezeigt) …',
    replySent: 'Antwort gesendet',
    followUpSent: 'Nachricht gesendet',
    reportedBy: 'Gemeldet von',
  },
  en: {
    support: 'Support',
    ticket: 'Ticket',
    notFound: 'Ticket not found.',
    actionFailed: 'Action failed',
    noSubject: '(no subject)',
    status: { open: 'Open', in_progress: 'In progress', waiting: 'Waiting', done: 'Done' },
    priorities: { low: 'Low', normal: 'Normal', high: 'High' },
    priority: 'Priority',
    reporter: 'Reporter',
    teamAddress: 'Team address',
    assignee: 'Assignee',
    unassignedLower: 'unassigned',
    restricted: 'restricted',
    claim: 'Claim',
    unassigned: 'Unassigned',
    statusLabel: 'Status',
    conversation: 'Conversation',
    noteAdded: 'Note added',
    replyQueued: 'Reply queued for sending',
    events: 'Events',
    by: 'by',
    supportTeam: 'Support team',
    unknownSender: 'Unknown sender',
    internalBanner: 'Internal note - not visible to the reporter',
    received: 'received',
    reply: 'reply',
    delivery: {},
    to: 'To',
    deliveryFailed: 'Delivery failed.',
    retry: 'Retry',
    replyByMail: 'Reply by mail',
    internalNote: 'Internal note',
    compose: 'Compose',
    internalHint: 'Internal note - not visible to the reporter.',
    from: 'From',
    replyText: 'Reply text',
    notePlaceholder: 'Write an internal note…',
    replyPlaceholder: 'Write a reply to the reporter…',
    sending: 'Sending…',
    addNote: 'Add note',
    sendReply: 'Send reply',
    confirmTitle: 'Send reply by mail?',
    confirmMessage: (from, to) => `This sends an email from ${from} to ${to}. It cannot be recalled.`,
    send: 'Send',
    myReports: 'My reports',
    you: 'You',
    followUp: 'Reply',
    followUpPlaceholder: 'Write an addition or reply to the support team…',
    replyInApp: 'Reply in the app',
    replyInAppPlaceholder: 'Write a reply to the reporter (shown in the app)…',
    replySent: 'Reply sent',
    followUpSent: 'Message sent',
    reportedBy: 'Reported by',
  },
};

export default function SupportTicketPage() {
  const id = useParams().id as string;
  const { user } = useAuth();
  const language = useUiLanguage();
  const t = COPY[language];
  const notify = useNotify();
  const { capabilities, loading: capsLoading } = useSupportCapabilities();
  const isTeam = !!capabilities?.can_view;
  const canManage = !!capabilities?.can_manage;

  const { data: ticket, loading, error, setData } = useResource(() => supportClient.get(id), [id], {
    enabled: !capsLoading,
  });
  const { data: agents } = useResource(() => supportClient.agents(), [], { enabled: canManage });

  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (capsLoading || (loading && !ticket)) return <PageLoading />;
  if (!ticket) {
    return (
      <AuthenticatedLayout>
        <ListPageLayout>
          <PageHeader breadcrumbs={[{ label: isTeam ? t.support : t.myReports, href: '/support' }, { label: t.ticket }]} title={t.ticket} />
          <ErrorBanner>{error ?? t.notFound}</ErrorBanner>
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
      setActionError(e instanceof Error ? e.message : t.actionFailed);
      return false;
    } finally {
      setBusy(false);
    }
  };
  const update = (body: TicketUpdate) => act(() => supportClient.update(ticket.id, body));

  const assignedToMe = !!user && ticket.assignee?.id === user.id;
  const events = ticket.events ?? [];
  const locale = localeFor(language);
  const inApp = ticket.channel !== 'mail';

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: isTeam ? t.support : t.myReports, href: '/support' }, { label: `#${ticket.number}` }]}
          title={ticket.subject || t.noSubject}
          subtitle={
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <span className="font-mono">#{ticket.number}</span>
              <Badge tone={STATUS_TONE[ticket.status]} pill>
                {t.status[ticket.status]}
              </Badge>
              {isTeam && (
                <>
                  <span>{t.priority}: {t.priorities[ticket.priority]}</span>
                  <span>
                    {t.reporter}: {ticket.reporter_name || ticket.reporter_email || '—'}
                    {ticket.reporter_name && ticket.reporter_email ? ` <${ticket.reporter_email}>` : ''}
                  </span>
                  {!inApp && <span>{t.teamAddress}: {ticket.mailbox_address ?? '—'}</span>}
                  <span>{t.assignee}: {ticket.assignee ? userLabel(ticket.assignee) : t.unassignedLower}</span>
                  {ticket.restricted && <Badge tone="warning">{t.restricted}</Badge>}
                </>
              )}
            </div>
          }
        />

        <ErrorBanner>{actionError}</ErrorBanner>

        <ScrollArea>
          {canManage && (
            <div className="flex flex-wrap items-end gap-4 rounded-lg border border-rule bg-surface p-4">
              {!assignedToMe && (
                <Button disabled={busy} onClick={() => act(() => supportClient.claim(ticket.id))}>
                  {t.claim}
                </Button>
              )}
              <label className="text-sm text-muted">
                {t.assignee}
                <select
                  className={`${inputCls} mt-1 !w-56`}
                  disabled={busy}
                  value={ticket.assignee?.id ?? ''}
                  onChange={(e) =>
                    update(e.target.value ? { assignee_id: e.target.value } : { unassign: true })
                  }
                >
                  <option value="">{t.unassigned}</option>
                  {(agents ?? []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {userLabel(a)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-muted">
                {t.statusLabel}
                <select
                  className={`${inputCls} mt-1 !w-40`}
                  disabled={busy}
                  value={ticket.status}
                  onChange={(e) => update({ status: e.target.value as TicketStatus })}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {t.status[s]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-muted">
                {t.priority}
                <select
                  className={`${inputCls} mt-1 !w-32`}
                  disabled={busy}
                  value={ticket.priority}
                  onChange={(e) => update({ priority: e.target.value as TicketPriority })}
                >
                  {PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {t.priorities[p]}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}

          {isTeam && ticket.report && <ReportContext report={ticket.report} />}
          {isTeam && (
            <PublishPanel ticket={ticket} canPublish={!!capabilities?.can_publish} onPublished={setData} />
          )}

          <section aria-label={t.conversation} className="space-y-3">
            {ticket.messages.map((m) => (
              <MessageCard
                key={m.id}
                ticketId={ticket.id}
                message={m}
                busy={busy}
                canRetry={!!capabilities?.can_reply}
                isTeam={isTeam}
                inApp={inApp}
                onRetry={() => act(() => supportClient.retryMessage(ticket.id, m.id))}
              />
            ))}
          </section>

          <Composer
            ticket={ticket}
            isTeam={isTeam}
            inApp={inApp}
            canReply={isTeam ? !!capabilities?.can_reply : true}
            canNote={isTeam && !!capabilities?.can_write_internal}
            teamAddresses={capabilities?.team_addresses ?? []}
            onSend={async (content, internal, fromAddress) => {
              const ok = await act(() =>
                supportClient.addMessage(ticket.id, {
                  content,
                  internal,
                  from_address: internal || inApp ? undefined : fromAddress || undefined,
                }),
              );
              if (ok) {
                notify(
                  internal ? t.noteAdded : !inApp ? t.replyQueued : isTeam ? t.replySent : t.followUpSent,
                  'success',
                );
              }
              return ok;
            }}
          />

          {isTeam && <details className="rounded-lg border border-rule bg-surface p-4">
            <summary className="cursor-pointer text-sm font-medium text-fg">
              {t.events} ({events.length})
            </summary>
            <ul className="mt-3 space-y-1 text-sm text-muted">
              {events.map((ev) => (
                <li key={ev.id}>
                  <span className="text-xs">{formatDateTime(ev.created_at, locale)}</span> — {ev.kind}
                  {ev.actor ? ` ${t.by} ${userLabel(ev.actor)}` : ''}
                  {Object.keys(ev.data ?? {}).length > 0 && (
                    <span className="ml-1 font-mono text-xs">{JSON.stringify(ev.data)}</span>
                  )}
                </li>
              ))}
            </ul>
          </details>}
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
  isTeam,
  inApp,
  onRetry,
}: {
  ticketId: string;
  message: TicketMessage;
  busy: boolean;
  canRetry: boolean;
  isTeam: boolean;
  inApp: boolean;
  onRetry: () => void;
}) {
  const language = useUiLanguage();
  const t = COPY[language];
  const internal = m.visibility === 'internal' || m.direction === 'note';
  const outgoing = m.direction === 'out';
  const ownMessage = !isTeam && !outgoing && !internal;
  const sender = ownMessage
    ? t.you
    : !isTeam && outgoing
      ? t.supportTeam
      : userLabel(m.author) || m.from_name || m.from_address || (outgoing ? t.supportTeam : t.unknownSender);

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
          {t.internalBanner}
        </p>
      )}
      <header className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="font-medium text-fg">{sender}</span>
        {isTeam && !internal && m.from_address && <span className="text-xs text-muted">&lt;{m.from_address}&gt;</span>}
        {isTeam && !inApp && !internal && !outgoing && <Badge tone="muted">{t.received}</Badge>}
        {isTeam && outgoing && <Badge tone="info">{t.reply}</Badge>}
        {isTeam && !inApp && outgoing && m.delivery_state && (
          <Badge
            tone={m.delivery_state === 'failed' ? 'error' : m.delivery_state === 'sent' ? 'success' : 'muted'}
          >
            {t.delivery[m.delivery_state] ?? m.delivery_state}
          </Badge>
        )}
        <span className="ml-auto text-xs text-muted">{formatDateTime(m.created_at, localeFor(language))}</span>
      </header>
      {isTeam && !inApp && !internal && m.to.length > 0 && <p className="mb-2 text-xs text-muted">{t.to}: {m.to.join(', ')}</p>}
      {isTeam && !inApp && outgoing && m.delivery_state === 'failed' && (
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <ErrorBanner>{m.delivery_error || t.deliveryFailed}</ErrorBanner>
          {canRetry && (
            <Button size="sm" variant="secondary" disabled={busy} onClick={onRetry}>
              {t.retry}
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
  isTeam,
  inApp,
  canReply,
  canNote,
  teamAddresses,
  onSend,
}: {
  ticket: TicketGet;
  isTeam: boolean;
  inApp: boolean;
  canReply: boolean;
  canNote: boolean;
  teamAddresses: string[];
  onSend: (content: string, internal: boolean, fromAddress: string) => Promise<boolean>;
}) {
  const t = COPY[useUiLanguage()];
  const [mode, setMode] = useState<ComposerMode>(canReply ? 'reply' : 'note');
  const [content, setContent] = useState('');
  const [from, setFrom] = useState(ticket.mailbox_address ?? '');
  const [confirming, setConfirming] = useState(false);
  const [sending, setSending] = useState(false);

  const tabs = [
    ...(canReply ? [{ id: 'reply' as const, label: !inApp ? t.replyByMail : isTeam ? t.replyInApp : t.followUp }] : []),
    ...(canNote ? [{ id: 'note' as const, label: t.internalNote }] : []),
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
    <section aria-label={t.compose} className="space-y-3 rounded-lg border border-rule bg-surface p-4">
      {tabs.length > 1 && <Tabs tabs={tabs} active={mode} onSelect={setMode} />}
      {internal ? (
        <p className="text-sm text-warn-text">{t.internalHint}</p>
      ) : inApp ? null : (
        <div className="flex flex-wrap items-end gap-4 text-sm text-muted">
          <label>
            {t.from}
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
            {t.to}
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
        aria-label={internal ? t.internalNote : inApp && !isTeam ? t.followUp : t.replyText}
        placeholder={internal ? t.notePlaceholder : !inApp ? t.replyPlaceholder : isTeam ? t.replyInAppPlaceholder : t.followUpPlaceholder}
      />
      <div className="flex justify-end">
        <Button
          disabled={empty || (!internal && !inApp && (!effectiveFrom || !ticket.reporter_email))}
          loading={sending}
          loadingLabel={t.sending}
          onClick={() => (internal || inApp ? void send() : setConfirming(true))}
        >
          {internal ? t.addNote : inApp && !isTeam ? t.send : t.sendReply}
        </Button>
      </div>
      <ConfirmDialog
        open={confirming}
        title={t.confirmTitle}
        message={t.confirmMessage(effectiveFrom, ticket.reporter_email ?? '')}
        confirmLabel={t.send}
        onConfirm={() => void send()}
        onCancel={() => setConfirming(false)}
      />
    </section>
  );
}
