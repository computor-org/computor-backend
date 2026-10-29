'use client';

import { Fragment, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { legalMarkdownComponents } from '@/src/components/legalMarkdown';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import type { BilingualText } from '@/src/utils/legalContent';
import { applyDocumentLanguage } from '@/src/utils/documentLanguage';

/**
 * A legal text that holds German and English on one page (impressum,
 * accessibility, report). The reading language decides which section comes first
 * and what the tab calls the page, so a reader is not led through the other
 * language's text first.
 *
 * The server render leads with German, like every public page here, and the
 * browser puts its own language in front after hydration — one route serves
 * both texts, and only the browser knows which one its visitor reads.
 */
export default function BilingualLegalText({
  sections,
  titles,
}: {
  sections: BilingualText;
  /** What the tab calls the page in each reading language. */
  titles: BilingualText;
}) {
  const language = useUiLanguage();
  const { de: titleDe, en: titleEn } = titles;
  useEffect(() => applyDocumentLanguage(language, { de: titleDe, en: titleEn }), [language, titleDe, titleEn]);

  const parts: { lang: 'de' | 'en'; body: string }[] = [
    { lang: 'de' as const, body: sections.de },
    { lang: 'en' as const, body: sections.en },
  ].filter((part) => part.body !== '');
  if (language === 'en') parts.reverse();

  return (
    <div className="prose markdown max-w-none mt-8">
      {parts.map((part, i) => (
        <Fragment key={part.lang}>
          {i > 0 ? <hr /> : null}
          <section lang={part.lang}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={legalMarkdownComponents}>
              {part.body}
            </ReactMarkdown>
          </section>
        </Fragment>
      ))}
    </div>
  );
}
