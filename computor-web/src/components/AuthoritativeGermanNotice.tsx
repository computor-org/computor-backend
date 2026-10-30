'use client';

import { useUiLanguage } from '@/src/hooks/useUiLanguage';

/**
 * On a German legal text, tells an English reader in English that this text is
 * the authoritative one and where the translation is. The text itself stays
 * German, since that is the version that applies.
 */
export default function AuthoritativeGermanNotice({ translation }: { translation: string }) {
  if (useUiLanguage() !== 'en') return null;
  return (
    <aside role="note" lang="en" className="mb-6 rounded-lg border border-rule bg-sunken px-4 py-3 text-sm text-fg">
      The German text below is the authoritative version.{' '}
      <a href={translation} hrefLang="en" className="font-medium text-accent-text underline">
        Read the English translation
      </a>
      .
    </aside>
  );
}
