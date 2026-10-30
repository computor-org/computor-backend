'use client';

import { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { legalMarkdownComponents } from '@/src/components/legalMarkdown';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { applyDocumentLanguage } from '@/src/utils/documentLanguage';
import type { BilingualText, LegalDoc } from '@/src/utils/legalContent';

/**
 * An authoritative German legal text and its English translation on one route.
 * A German reader gets the German text; an English reader gets the translation,
 * opened by a note that the German text applies and a link to it, so "Automatic
 * follows your browser" holds here too.
 */
export default function ReadingLanguageLegalText({
  de,
  en,
  germanHref,
  titles,
}: {
  de: LegalDoc;
  en: LegalDoc;
  /** A route that always shows the German text. */
  germanHref: string;
  /** What the tab calls the page in each reading language. */
  titles: BilingualText;
}) {
  const language = useUiLanguage();
  const { de: titleDe, en: titleEn } = titles;
  useEffect(() => applyDocumentLanguage(language, { de: titleDe, en: titleEn }), [language, titleDe, titleEn]);
  const doc = language === 'en' ? en : de;

  return (
    <div lang={language}>
      {language === 'en' ? (
        <aside role="note" className="mb-6 rounded-lg border border-accent-line bg-accent-wash px-4 py-3 text-sm text-fg">
          <strong className="font-semibold">This is an English translation.</strong>{' '}
          Only the German text is authoritative.{' '}
          <a href={germanHref} hrefLang="de" className="font-medium text-accent-text underline">
            Read the German text
          </a>
          .
        </aside>
      ) : null}
      <h1 className="text-2xl sm:text-3xl font-bold text-fg break-words">{doc.title}</h1>
      {doc.version ? <p className="mt-2 text-sm text-muted">{doc.version}</p> : null}
      <div className="prose markdown max-w-none mt-8">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={legalMarkdownComponents}>
          {doc.body}
        </ReactMarkdown>
      </div>
    </div>
  );
}
