'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import { MessagesClient } from '@/src/generated/clients/MessagesClient';
import type { MessageList } from 'types/generated';

const messagesClient = new MessagesClient();

function authorName(m: MessageList): string {
  const n = [m.author?.given_name, m.author?.family_name].filter(Boolean).join(' ');
  return n || 'System';
}

// `level` is a severity hint; map it to a left-accent color (default: info).
function levelAccent(level: number): string {
  if (level >= 3) return 'border-l-red-400';
  if (level === 2) return 'border-l-amber-400';
  return 'border-l-blue-400';
}

function fmtWhen(s?: string | null): string {
  return s ? new Date(s).toLocaleString() : '';
}

export default function NotificationsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [messages, setMessages] = useState<MessageList[]>([]);
  const [seenUnread, setSeenUnread] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const items = await messagesClient.listMessagesMessagesGet({ scope: 'global', limit: 100 });
        if (cancelled) return;
        items.sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''));
        setMessages(items);
        // Snapshot which were unread so this view keeps the "new" accent,
        // then mark them read so the bell badge clears on next navigation.
        const unread = items.filter((m) => !m.is_read);
        setSeenUnread(new Set(unread.map((m) => m.id)));
        if (unread.length > 0) {
          await Promise.allSettled(unread.map((m) => messagesClient.markMessageReadMessagesIdReadsPost({ id: m.id })));
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load notifications');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated]);

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Notifications' }]}
          title="Notifications"
          subtitle="Announcements broadcast to everyone on this Computor instance."
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : messages.length === 0 ? (
          <ScrollArea>
            <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
              No notifications.
            </div>
          </ScrollArea>
        ) : (
          <ScrollArea className="space-y-3">
            {messages.map((m) => {
              const isNew = seenUnread.has(m.id);
              return (
                <div
                  key={m.id}
                  className={`bg-white border border-gray-200 border-l-4 ${levelAccent(m.level)} rounded-lg p-4 ${isNew ? 'ring-1 ring-blue-100' : ''}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      {m.title && <div className="text-sm font-semibold text-gray-900">{m.title}</div>}
                      <div className="text-sm text-gray-700 whitespace-pre-wrap">{m.content}</div>
                    </div>
                    {isNew && <Badge color="blue" className="shrink-0 mt-0.5">new</Badge>}
                  </div>
                  <div className="mt-2 text-xs text-gray-400">
                    {authorName(m)} · {fmtWhen(m.created_at)}
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
