'use client';

import { useAuth } from '@/src/contexts/AuthContext';
import { useBrowserLanguage, type UiLanguage } from './useBrowserLanguage';

export type { UiLanguage };

/** The interface language a profile language selects: German for 'de', English for any other. */
export function profileUiLanguage(language?: string | null): UiLanguage | null {
  const code = language?.trim().toLowerCase();
  if (!code) return null;
  return code === 'de' ? 'de' : 'en';
}

/**
 * The language of the signed-in interface: the profile language when the user
 * chose one, else the stored or browser language. An auth callback may provide
 * its request-selected language for the server render and browser fallback.
 */
export function useUiLanguage(initialLanguage?: UiLanguage): UiLanguage {
  const { user } = useAuth();
  const browserLanguage = useBrowserLanguage(initialLanguage, initialLanguage);
  return profileUiLanguage(user?.language) ?? browserLanguage;
}
