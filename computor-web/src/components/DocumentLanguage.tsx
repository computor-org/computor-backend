'use client';

import { useEffect } from 'react';
import { applyDocumentLanguage } from '@/src/utils/documentLanguage';

/**
 * Declares the language of a server-rendered page in the document.
 *
 * The root layout stamps the reader's language on <html>, from the request
 * (computor-org/issues#453). A page whose text is in one known language states
 * that here, so an English page does not claim the German reader's language.
 */
export default function DocumentLanguage({ language }: { language: 'de' | 'en' }) {
  useEffect(() => applyDocumentLanguage(language), [language]);
  return null;
}
