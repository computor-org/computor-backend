'use client';

import { useState } from 'react';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

// Sanitised server-side already; this is the second, independent layer. The
// iframe has an empty sandbox (no scripts, no same-origin, no popups) and the
// document carries a CSP that forbids every fetch except inline styles and data: images.
const CSP =
  "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'";

function buildSrcDoc(html: string): string {
  return (
    '<!doctype html><html><head><meta charset="utf-8">' +
    `<meta http-equiv="Content-Security-Policy" content="${CSP}">` +
    '<style>body{font:14px/1.5 system-ui,sans-serif;margin:8px;overflow-wrap:anywhere}' +
    'img{max-width:100%;height:auto}blockquote{margin:0 0 0 8px;padding-left:8px;border-left:2px solid #ccc}</style>' +
    `</head><body>${html}</body></html>`
  );
}

const COPY = {
  de: { plain: 'Nur Text anzeigen', formatted: 'Formatiert anzeigen', frame: 'Formatierte Nachricht' },
  en: { plain: 'Show plain text', formatted: 'Show formatted', frame: 'Formatted message' },
};

/**
 * Message body: plain text by default (always a text node), with an opt-in
 * formatted view for mails that carry sanitised HTML.
 */
export default function MessageBody({ text, html }: { text: string; html?: string | null }) {
  const t = COPY[useUiLanguage()];
  const [formatted, setFormatted] = useState(false);

  return (
    <div>
      {html != null && (
        <button
          type="button"
          onClick={() => setFormatted((v) => !v)}
          className="mb-2 text-xs text-accent-text hover:underline"
        >
          {formatted ? t.plain : t.formatted}
        </button>
      )}
      {html != null && formatted ? (
        <iframe
          title={t.frame}
          sandbox=""
          srcDoc={buildSrcDoc(html)}
          referrerPolicy="no-referrer"
          className="w-full h-96 rounded border border-rule bg-white"
        />
      ) : (
        <pre className="whitespace-pre-wrap break-words font-sans text-sm text-body">{text}</pre>
      )}
    </div>
  );
}
