'use client';

import { useSyncExternalStore } from 'react';

export type UiLanguage = 'de' | 'en';

const STORAGE_KEY = 'computor.language';
const CHANGE_EVENT = 'computor-language-change';

function storedLanguage(): UiLanguage | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === 'de' || value === 'en' ? value : null;
  } catch {
    return null;
  }
}

function navigatorLanguage(): UiLanguage {
  const preferred = (navigator.languages?.[0] ?? navigator.language ?? '').toLowerCase();
  return preferred.startsWith('de') ? 'de' : 'en';
}

export function getUiLanguage(initialPreference?: UiLanguage): UiLanguage {
  const stored = storedLanguage();
  if (stored) return stored;
  if (initialPreference) return initialPreference;
  return navigatorLanguage();
}

function subscribe(onChange: () => void) {
  window.addEventListener('storage', onChange);
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener('storage', onChange);
    window.removeEventListener(CHANGE_EVENT, onChange);
  };
}

/** Remember an explicit language choice for all public pages. */
export function setUiLanguage(language: UiLanguage) {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Without storage the choice lasts until the next page load.
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

/**
 * True only when the visitor explicitly chose a language on a signed-out page.
 * Sign-in sends this as `explicit_language` so the backend stores the profile
 * language for a real choice but leaves a new account on Automatic (computor-org/issues#534).
 */
export function hasExplicitUiLanguage(): boolean {
  return typeof window !== 'undefined' && storedLanguage() !== null;
}

/** Drop the explicit choice, so the browser language rules again. */
export function clearUiLanguage() {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing stored to drop.
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

/**
 * The visitor's explicit choice, else German for German-language browsers and
 * English otherwise. The server render uses `fallback`; the browser value
 * applies on hydration. `preferred` supplies a request-selected language ahead
 * of browser detection while a remembered explicit choice still wins.
 */
export function useBrowserLanguage(fallback: UiLanguage = 'de', preferred?: UiLanguage): UiLanguage {
  return useSyncExternalStore(subscribe, () => getUiLanguage(preferred), () => fallback);
}

/** The browser language alone, without a choice stored on a signed-out page. */
export function useNavigatorLanguage(fallback: UiLanguage = 'de'): UiLanguage {
  return useSyncExternalStore(subscribe, navigatorLanguage, () => fallback);
}
