import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';
import { HAS_OWN_LEGAL_PAGES } from '@/src/config/legal';
import { loadLegalDoc, type LegalDocName } from '@/src/utils/legalContent';

export interface LanguageSwitch {
  label: string;
  href: string;
  lang: string;
  current: boolean;
}

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  return '';
}

function slug(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/**
 * A static legal page (Impressum, Datenschutz, …) rendered from
 * content/legal/*.md at build time. Server component, no client state, so it
 * reads without JavaScript. 404 unless this build uses the computor-at legal
 * profile: other deployments link elsewhere or show no legal pages at all.
 */
export default function LegalPage({
  doc,
  lang,
  languages,
}: {
  doc: LegalDocName;
  /** Language of the text, or undefined for a page holding DE and EN. */
  lang?: string;
  languages?: LanguageSwitch[];
}) {
  if (!HAS_OWN_LEGAL_PAGES) notFound();
  const { title, version, body } = loadLegalDoc(doc);

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <header className="border-b border-rule bg-surface">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <Image src="/computor_logo.png" alt="" width={32} height={32} className="h-8 w-8" />
            <span className="text-xl font-bold text-fg">Computor</span>
          </Link>
          {languages ? (
            <nav aria-label="Sprache / Language" className="flex gap-1 text-sm">
              {languages.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  hrefLang={l.lang}
                  aria-current={l.current ? 'page' : undefined}
                  className={
                    l.current
                      ? 'px-3 py-1 rounded-md bg-accent-wash text-accent-text font-medium'
                      : 'px-3 py-1 rounded-md text-muted hover:text-fg hover:bg-sunken'
                  }
                >
                  {l.label}
                </a>
              ))}
            </nav>
          ) : null}
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-10">
        <article lang={lang} className="max-w-3xl mx-auto">
          <h1 className="text-3xl font-bold text-fg">{title}</h1>
          {version ? <p className="mt-2 text-sm text-muted">{version}</p> : null}
          <div className="prose markdown max-w-none mt-8">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h2: ({ children }) => <h2 id={slug(textOf(children))}>{children}</h2>,
              }}
            >
              {body}
            </ReactMarkdown>
          </div>
        </article>
      </main>

      <footer className="border-t border-rule bg-surface">
        <div className="container mx-auto px-4 py-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted">
          <LegalLinks />
          <NetideeNotice />
        </div>
      </footer>
    </div>
  );
}
