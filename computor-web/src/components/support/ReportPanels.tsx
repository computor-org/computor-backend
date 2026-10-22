'use client';

import { useState } from 'react';
import Modal from '@/src/components/Modal';
import ErrorBanner from '@/src/components/ErrorBanner';
import Button from '@/src/components/ui/Button';
import { inputCls } from '@/src/components/ui/tokens';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { supportClient, type TicketGet, type TicketReportInfo } from '@/src/clients/SupportClient';

const COPY = {
  de: {
    contextTitle: 'Meldungskontext',
    app: 'Anwendung',
    version: 'Version',
    page: 'Seite',
    command: 'Befehl',
    rawContext: 'Kontext (JSON)',
    published: 'Auf GitHub veröffentlicht',
    issue: (n: number) => `Issue #${n}`,
    publish: 'Auf GitHub veröffentlichen',
    editorTitle: 'Auf GitHub veröffentlichen',
    warning:
      'Dieser Text geht in den privaten Maintainer-Tracker. Er darf weder die meldende Person noch andere Personen erkennen lassen. Entferne Namen, Mailadressen und Kennungen.',
    titleLabel: 'Titel',
    bodyLabel: 'Text',
    loadingDraft: 'Entwurf wird geladen …',
    cancel: 'Abbrechen',
    confirm: 'Veröffentlichen',
    publishing: 'Wird veröffentlicht …',
    failed: 'Aktion fehlgeschlagen',
  },
  en: {
    contextTitle: 'Report context',
    app: 'App',
    version: 'Version',
    page: 'Page',
    command: 'Command',
    rawContext: 'Context (JSON)',
    published: 'Published on GitHub',
    issue: (n: number) => `Issue #${n}`,
    publish: 'Publish to GitHub',
    editorTitle: 'Publish to GitHub',
    warning:
      'This text goes to the private maintainer tracker. It must not identify the reporter or any other person. Remove names, email addresses and identifiers.',
    titleLabel: 'Title',
    bodyLabel: 'Text',
    loadingDraft: 'Loading draft…',
    cancel: 'Cancel',
    confirm: 'Publish',
    publishing: 'Publishing…',
    failed: 'Action failed',
  },
};

/** App, version, page or command and the raw context of a web or VS Code report. */
export function ReportContext({ report }: { report: TicketReportInfo }) {
  const t = COPY[useUiLanguage()];
  const rows: [string, string | null | undefined][] = [
    [t.app, report.app],
    [t.version, report.version],
    [t.page, report.page],
    [t.command, report.command],
  ];
  const context = report.context && Object.keys(report.context).length > 0 ? report.context : null;
  return (
    <section aria-label={t.contextTitle} className="rounded-lg border border-rule bg-surface p-4 text-sm">
      <h2 className="mb-2 font-medium text-fg">{t.contextTitle}</h2>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-muted">
        {rows
          .filter(([, v]) => !!v)
          .map(([label, value]) => (
            <div key={label} className="contents">
              <dt>{label}</dt>
              <dd className="font-mono text-xs text-fg break-all">{value}</dd>
            </div>
          ))}
      </dl>
      {context && (
        <details className="mt-3">
          <summary className="cursor-pointer text-muted">{t.rawContext}</summary>
          <pre className="mt-2 overflow-x-auto rounded bg-canvas p-2 text-xs">{JSON.stringify(context, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}

/** Issue link once published, else (when allowed) the publish action with its editor. */
export function PublishPanel({
  ticket,
  canPublish,
  onPublished,
}: {
  ticket: TicketGet;
  canPublish: boolean;
  onPublished: (ticket: TicketGet) => void;
}) {
  const t = COPY[useUiLanguage()];
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pub = ticket.publication;
  if (pub) {
    return (
      <p className="text-sm text-muted">
        {t.published}:{' '}
        {pub.issue_url ? (
          <a href={pub.issue_url} target="_blank" rel="noopener noreferrer" className="text-accent-text hover:underline">
            {t.issue(pub.issue_number)}
          </a>
        ) : (
          t.issue(pub.issue_number)
        )}
      </p>
    );
  }
  if (!canPublish || !ticket.report) return null;

  const openEditor = async () => {
    setOpen(true);
    setError(null);
    setLoading(true);
    try {
      const draft = await supportClient.publishDraft(ticket.id);
      setTitle(draft.title);
      setBody(draft.body);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.failed);
    } finally {
      setLoading(false);
    }
  };

  const confirm = async () => {
    setSaving(true);
    setError(null);
    try {
      onPublished(await supportClient.publish(ticket.id, { title, body }));
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.failed);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div>
        <Button variant="secondary" onClick={() => void openEditor()}>
          {t.publish}
        </Button>
      </div>
      {open && (
        <Modal title={t.editorTitle} onClose={() => setOpen(false)} maxWidth="max-w-2xl">
          <div className="space-y-3 px-6 pt-2 pb-6">
            <p role="alert" className="rounded border border-warn-line bg-warn-wash p-3 text-sm text-warn-text">
              {t.warning}
            </p>
            <ErrorBanner>{error}</ErrorBanner>
            {loading ? (
              <p className="text-sm text-muted">{t.loadingDraft}</p>
            ) : (
              <>
                <label className="block text-sm text-muted">
                  {t.titleLabel}
                  <input className={`${inputCls} mt-1`} value={title} maxLength={256} onChange={(e) => setTitle(e.target.value)} />
                </label>
                <label className="block text-sm text-muted">
                  {t.bodyLabel}
                  <textarea className={`${inputCls} mt-1 min-h-64 font-mono`} value={body} onChange={(e) => setBody(e.target.value)} />
                </label>
              </>
            )}
            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={() => setOpen(false)}>
                {t.cancel}
              </Button>
              <Button
                disabled={loading || !title.trim() || !body.trim()}
                loading={saving}
                loadingLabel={t.publishing}
                onClick={() => void confirm()}
              >
                {t.confirm}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  );
}
