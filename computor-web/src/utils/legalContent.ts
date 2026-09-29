// Build-time loader for the legal texts in content/legal/*.md (server only).
//
// The files are the final texts from the legal review, copied verbatim; the
// only edit is a trailing "\" (CommonMark hard line break) on the address
// lines of impressum.md so postal addresses keep their line structure. Read
// with readFileSync so the pages are prerendered into static HTML at build
// time and need no JavaScript to read.

import { readFileSync } from 'node:fs';
import path from 'node:path';

export type LegalDocName =
  | 'impressum'
  | 'datenschutz_de'
  | 'privacy_en'
  | 'nutzungsbedingungen_de'
  | 'terms_en'
  | 'barrierefreiheit'
  | 'meldung_inhalte';

export interface LegalDoc {
  /** Text of the leading "# …" heading. */
  title: string;
  /** The "Version 1.0, gültig ab …" line, shown as the page subtitle. */
  version: string | null;
  /** Everything after the title and version lines. */
  body: string;
}

const CONTENT_DIR = path.join(process.cwd(), 'content', 'legal');

export function loadLegalDoc(name: LegalDocName): LegalDoc {
  const raw = readFileSync(path.join(CONTENT_DIR, `${name}.md`), 'utf-8');
  const lines = raw.split('\n');
  let title = '';
  let version: string | null = null;
  let start = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line === '') continue;
    if (!title && line.startsWith('# ')) {
      title = line.slice(2).trim();
      start = i + 1;
      continue;
    }
    if (title && version === null && line.startsWith('Version ')) {
      version = line;
      start = i + 1;
    }
    break;
  }
  return { title, version, body: lines.slice(start).join('\n').trim() + '\n' };
}
