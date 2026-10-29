'use client';

import { useResource } from '@/src/hooks/useResource';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import { MessagesClient } from '@/src/generated/clients/MessagesClient';
import type { MessageList } from 'types/generated';
import { localeFor } from '@/src/utils/locale';

const messagesClient = new MessagesClient();

const COPY = {
  de: {
    title: 'Mitteilungen',
    subtitle: 'Ankündigungen an alle Nutzenden dieser Computor-Instanz.',
    loading: 'Wird geladen …',
    empty: 'Keine Mitteilungen.',
    new: 'neu',
    system: 'System',
  },
  en: {
    title: 'Notifications',
    subtitle: 'Announcements broadcast to everyone on this Computor instance.',
    loading: 'Loading…',
    empty: 'No notifications.',
    new: 'new',
    system: 'System',
  },
};

function authorName(m: MessageList, fallback: string): string {
  const n = [m.author?.given_name, m.author?.family_name].filter(Boolean).join(' ');
  return n || fallback;
}

// `level` is a severity hint; map it to a left-accent color (default: info).
function levelAccent(level: number): string {
  if (level >= 3) return 'border-l-red-400';
  if (level === 2) return 'border-l-amber-400';
  return 'border-l-blue-400';
}

function fmtWhen(s: string | null | undefined, locale: string | undefined): string {
  return s ? new Date(s).toLocaleString(locale) : '';
}

export default function NotificationsPage() {
  const language = useUiLanguage();
  const t = COPY[language];
  const { data, loading, error } = useResource(async () => {
    const items = await messagesClient.listMessagesMessagesGet({ scope: 'global', limit: 100 });
    items.sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''));
    // Snapshot which were unread so this view keeps the "new" accent, then mark
    // them read so the bell badge clears on next navigation.
    const unread = items.filter((m) => !m.is_read);
    const seenUnread = new Set(unread.map((m) => m.id));
    if (unread.length > 0) {
      await Promise.allSettled(unread.map((m) => messagesClient.markMessageReadMessagesIdReadsPost({ id: m.id })));
    }
    return { messages: items, seenUnread };
  }, []);
  const messages = data?.messages ?? [];
  const seenUnread = data?.seenUnread ?? new Set<string>();

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: t.title }]}
          title={t.title}
          subtitle={t.subtitle}
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>{t.loading}</ListLoading>
        ) : messages.length === 0 ? (
          <ScrollArea>
            <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
              {t.empty}
            </div>
          </ScrollArea>
        ) : (
          <ScrollArea spacing="rows">
            {messages.map((m) => {
              const isNew = seenUnread.has(m.id);
              return (
                <div
                  key={m.id}
                  className={`bg-surface border border-rule border-l-4 ${levelAccent(m.level)} rounded-lg p-4 ${isNew ? 'ring-1 ring-accent-line' : ''}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      {m.title && <div className="text-sm font-semibold text-fg">{m.title}</div>}
                      <div className="text-sm text-body whitespace-pre-wrap">{m.content}</div>
                    </div>
                    {isNew && <Badge color="blue" className="shrink-0 mt-0.5">{t.new}</Badge>}
                  </div>
                  <div className="mt-2 text-xs text-subtle">
                    {authorName(m, t.system)} · {fmtWhen(m.created_at, localeFor(language))}
                  </div>
                </div>
              );
            })}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
