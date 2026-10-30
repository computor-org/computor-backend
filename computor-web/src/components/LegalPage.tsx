import Image from 'next/image';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import BilingualLegalText from '@/src/components/BilingualLegalText';
import DocumentLanguage from '@/src/components/DocumentLanguage';
import LegalLinks from '@/src/components/LegalLinks';
import NetideeNotice from '@/src/components/NetideeNotice';
import ReadingLanguageLegalText from '@/src/components/ReadingLanguageLegalText';
import { legalMarkdownComponents } from '@/src/components/legalMarkdown';
import { HAS_OWN_LEGAL_PAGES } from '@/src/config/legal';
import { englishVersionLine, loadLegalDoc, splitBilingual, type BilingualText, type LegalDocName } from '@/src/utils/legalContent';

export interface LanguageSwitch {
  label: string;
  href: string;
  lang: string;
  current: boolean;
}

/**
 * A static legal page (Impressum, Datenschutz, …) rendered from
 * content/legal/*.md at build time. Server component, no client state, so it
 * reads without JavaScript. 404 unless this build uses the computor-at legal
 * profile: other deployments link elsewhere or show no legal pages at all.
 *
 * `lang` says what language the text is in; `titles` that the page holds both
 * languages and names itself in whichever one is being read — the only thing the
 * server cannot know, so that part arrives with the browser.
 */
export default function LegalPage({
  doc,
  lang,
  languages,
  titles,
  headings,
  translation,
}: {
  doc: LegalDocName;
  /** Language of the text, or undefined for a page holding DE and EN. */
  lang?: string;
  languages?: LanguageSwitch[];
  /** Set on a bilingual page, or with `translation`: its tab title in each reading language. */
  titles?: BilingualText;
  /** Set on a bilingual page: its heading in each reading language. */
  headings?: BilingualText;
  /**
   * Set on an authoritative German text: its English translation, shown to an
   * English reader, and a route that always shows the German text.
   */
  translation?: { doc: LegalDocName; germanHref: string };
}) {
  if (!HAS_OWN_LEGAL_PAGES) notFound();
  const legalDoc = loadLegalDoc(doc);
  const { title, version, body } = legalDoc;
  const reading = lang === 'en' ? 'en' : 'de';

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
        <article lang={translation ? undefined : lang} className="max-w-3xl mx-auto">
          {translation && titles ? (
            <ReadingLanguageLegalText
              de={legalDoc}
              en={loadLegalDoc(translation.doc)}
              germanHref={translation.germanHref}
              titles={titles}
            />
          ) : titles ? (
            <BilingualLegalText
              sections={splitBilingual(body)}
              titles={titles}
              headings={headings ?? { de: title, en: title }}
              versions={version ? { de: version, en: englishVersionLine(version) } : null}
            />
          ) : (
            <>
              <h1 className="text-2xl sm:text-3xl font-bold text-fg break-words">{title}</h1>
              {version ? <p className="mt-2 text-sm text-muted">{version}</p> : null}
              <DocumentLanguage language={reading} />
              <div className="prose markdown max-w-none mt-8">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={legalMarkdownComponents}>
                  {body}
                </ReactMarkdown>
              </div>
            </>
          )}
        </article>
      </main>

      <footer className="border-t border-rule bg-surface">
        <div className="container mx-auto px-4 py-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted">
          <LegalLinks language={reading} />
          <NetideeNotice language={reading} />
        </div>
      </footer>
    </div>
  );
}
