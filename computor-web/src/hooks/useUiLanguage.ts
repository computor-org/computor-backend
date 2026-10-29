'use client';

import { useAuth } from '@/src/contexts/AuthContext';
import { useRequestLanguage } from '@/src/contexts/RequestLanguageContext';
import { useBrowserLanguage, useNavigatorLanguage, type UiLanguage } from './useBrowserLanguage';

export type { UiLanguage };

/** The interface language a profile language selects: German for 'de', English for any other. */
export function profileUiLanguage(language?: string | null): UiLanguage | null {
  const code = language?.trim().toLowerCase();
  if (!code) return null;
  return code === 'de' ? 'de' : 'en';
}

/**
 * The language of the signed-in interface: the profile language when the user
 * chose one, else the language the backend resolved from the browser, else the
 * browser language. A choice stored on a signed-out page applies only while
 * signed out, so "Automatic" follows the browser (computor-org/issues#534).
 * An auth callback may provide its request-selected language for the server
 * render and browser fallback. While the session is still being restored, the
 * signed-in language the server saw in its cookie holds, so a signed-in page
 * renders in it from the first paint.
 */
export function useUiLanguage(initialLanguage?: UiLanguage): UiLanguage {
  const { user, isLoading } = useAuth();
  const request = useRequestLanguage();
  const browserLanguage = useBrowserLanguage(initialLanguage, initialLanguage);
  const navigatorLanguage = useNavigatorLanguage(initialLanguage);
  if (!user) return isLoading && request.reading && !initialLanguage ? request.reading : browserLanguage;
  return profileUiLanguage(user.language) ?? user.effectiveLanguage ?? navigatorLanguage;
}
