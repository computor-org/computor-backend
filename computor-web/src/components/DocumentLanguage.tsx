'use client';

import { useEffect } from 'react';
import { applyDocumentLanguage } from '@/src/utils/documentLanguage';

/**
 * Declares the language of a server-rendered page in the document.
 *
 * The root layout stamps German on <html>, because German is all the server can
 * know without reading the request (computor-org/issues#453). A page whose text
 * is in one known language states that here, so the document no longer claims to
 * be German when it is English.
 */
export default function DocumentLanguage({ language }: { language: 'de' | 'en' }) {
  useEffect(() => applyDocumentLanguage(language), [language]);
  return null;
}
