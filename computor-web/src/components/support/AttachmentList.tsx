'use client';

import { useState } from 'react';
import type { TicketAttachment } from '@/src/clients/SupportClient';
import { supportClient } from '@/src/clients/SupportClient';
import { useNotify } from '@/src/contexts/NotificationContext';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatSize } from '@/src/utils/support';

const COPY = {
  de: { downloadFailed: 'Download fehlgeschlagen', tooLarge: 'zu groß, im Postfach-Archiv' },
  en: { downloadFailed: 'Download failed', tooLarge: 'too large, in the mailbox archive' },
};

/**
 * Attachments are download-only: fetched through the authenticated client as an
 * opaque blob and saved via a download link, never opened or rendered inline.
 */
export default function AttachmentList({
  ticketId,
  attachments,
}: {
  ticketId: string;
  attachments: TicketAttachment[];
}) {
  const notify = useNotify();
  const t = COPY[useUiLanguage()];
  const [busy, setBusy] = useState<string | null>(null);

  if (attachments.length === 0) return null;

  const download = async (a: TicketAttachment) => {
    setBusy(a.id);
    try {
      const blob = await supportClient.downloadAttachment(ticketId, a.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = a.filename;
      link.rel = 'noopener noreferrer';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (e) {
      notify(e instanceof Error ? e.message : t.downloadFailed, 'error');
    } finally {
      setBusy(null);
    }
  };

  return (
    <ul className="mt-3 space-y-1 border-t border-rule pt-2 text-sm">
      {attachments.map((a) => (
        <li key={a.id} className="flex items-center gap-2">
          {a.stored ? (
            <button
              type="button"
              disabled={busy === a.id}
              onClick={() => download(a)}
              className="text-accent-text hover:underline disabled:opacity-50"
            >
              {a.filename}
            </button>
          ) : (
            <span className="text-body">{a.filename}</span>
          )}
          <span className="text-xs text-muted">({formatSize(a.size)})</span>
          {!a.stored && <span className="text-xs text-warn-text">{t.tooLarge}</span>}
        </li>
      ))}
    </ul>
  );
}
