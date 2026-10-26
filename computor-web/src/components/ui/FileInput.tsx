'use client';

import type { ReactNode } from 'react';
import type { UiLanguage } from '@/src/hooks/useUiLanguage';

const COPY = {
  de: { choose: 'Datei auswählen', none: 'Keine Datei ausgewählt' },
  en: { choose: 'Choose file', none: 'No file chosen' },
};

/**
 * A file picker in the page's own language.
 *
 * The native control labels its button and its empty state in the browser's
 * language ("Choose File", "No file chosen"), which no CSS can change, so a
 * German page read half in English. The real input stays in the label for
 * keyboard, screen readers and tests, visually hidden; the visible button and
 * file name are drawn here.
 */
export default function FileInput({
  label,
  accept,
  file,
  onChange,
  language,
  className = '',
}: {
  label: ReactNode;
  accept?: string;
  /** The chosen file, owned by the caller (null when none is chosen). */
  file: File | null;
  onChange: (file: File | null) => void;
  language: UiLanguage;
  className?: string;
}) {
  const t = COPY[language];
  return (
    <label className={`block text-sm text-muted ${className}`}>
      {label}
      <input
        type="file"
        accept={accept}
        className="peer sr-only"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      <span className="mt-1 flex min-w-0 items-center gap-3 rounded peer-focus-visible:ring-2 peer-focus-visible:ring-accent-line">
        <span className="shrink-0 cursor-pointer rounded bg-accent-wash px-4 py-2 text-sm font-medium text-accent-text hover:bg-accent-wash">
          {t.choose}
        </span>
        <span className="min-w-0 truncate">{file ? file.name : t.none}</span>
      </span>
    </label>
  );
}
