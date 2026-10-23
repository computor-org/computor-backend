import type { UiLanguage } from '@/src/hooks/useUiLanguage';

/**
 * When the software in a workspace was built, as "Version vom …".
 *
 * The workspace's own creation date says little: starting an outdated
 * workspace rebuilds it on the template's newest version, so the version's
 * date is what tells a user how current their environment is (issue #401).
 */
export function workspaceVersionLabel(iso: string | null | undefined, language: UiLanguage): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const when = date.toLocaleString(language === 'de' ? 'de-AT' : 'en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
  return language === 'de' ? `Version vom ${when}` : `Version of ${when}`;
}
