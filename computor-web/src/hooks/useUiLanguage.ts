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
 * chose one, else the stored or browser language.
 */
export function useUiLanguage(): UiLanguage {
  const { user } = useAuth();
  const browserLanguage = useBrowserLanguage();
  return profileUiLanguage(user?.language) ?? browserLanguage;
}
