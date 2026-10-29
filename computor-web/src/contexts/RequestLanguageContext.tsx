'use client';

import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { CHOSEN_LANGUAGE_COOKIE, writeLanguageCookie, type RequestLanguage } from '@/src/utils/requestLanguage';

const STORAGE_KEY = 'computor.language';

const RequestLanguageContext = createContext<RequestLanguage>({ chosen: null, reading: null, browser: 'de' });

/**
 * The reader's language as the server saw it in the request (cookies and
 * Accept-Language), so the server render and the first client render agree
 * and the page does not flash German before switching (computor-org/issues#453).
 */
export function RequestLanguageProvider({ value, children }: { value: RequestLanguage; children: ReactNode }) {
  useEffect(() => {
    // A choice stored before the cookie existed reaches the server from now on.
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      const chosen = stored === 'de' || stored === 'en' ? stored : null;
      if (chosen !== value.chosen) writeLanguageCookie(CHOSEN_LANGUAGE_COOKIE, chosen);
    } catch {
      // Without storage there is no choice to mirror.
    }
  }, [value.chosen]);
  return <RequestLanguageContext.Provider value={value}>{children}</RequestLanguageContext.Provider>;
}

export function useRequestLanguage(): RequestLanguage {
  return useContext(RequestLanguageContext);
}
