'use client';

import { useSyncExternalStore } from 'react';

export type UiLanguage = 'de' | 'en';

const subscribe = () => () => {};

function browserLanguage(): UiLanguage {
  const preferred = (navigator.languages?.[0] ?? navigator.language ?? '').toLowerCase();
  return preferred.startsWith('de') ? 'de' : 'en';
}

/**
 * German for German-language browsers, English otherwise. The server render
 * uses `fallback`, and the browser preference applies on hydration.
 */
export function useBrowserLanguage(fallback: UiLanguage = 'de'): UiLanguage {
  return useSyncExternalStore(subscribe, browserLanguage, () => fallback);
}
