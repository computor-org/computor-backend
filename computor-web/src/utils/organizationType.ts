import type { UiLanguage } from '@/src/hooks/useUiLanguage';

const LABELS: Record<string, Record<UiLanguage, string>> = {
  organization: { de: 'Organisation', en: 'Organization' },
  community: { de: 'Community', en: 'Community' },
  user: { de: 'Persönlich', en: 'Personal' },
};

/** An organization type ("organization", "community", "user") as a word in the reading language. */
export function organizationTypeLabel(type: string | null | undefined, language: UiLanguage): string {
  if (!type) return '';
  return LABELS[type]?.[language] ?? type;
}
