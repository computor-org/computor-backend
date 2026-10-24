'use client';

import { setUiLanguage, useBrowserLanguage, type UiLanguage } from '@/src/hooks/useBrowserLanguage';

const OPTIONS: { language: UiLanguage; short: string; label: string }[] = [
  { language: 'de', short: 'DE', label: 'Deutsch' },
  { language: 'en', short: 'EN', label: 'English' },
];

/**
 * Deutsch/English switch for the public pages. German is the default for
 * German-language browsers; the choice is remembered for all public pages.
 */
export default function LanguageSwitch({ className = '' }: { className?: string }) {
  const current = useBrowserLanguage();
  return (
    <div
      role="group"
      aria-label={current === 'de' ? 'Sprache' : 'Language'}
      className={`inline-flex rounded-md border border-rule bg-surface p-0.5 text-xs font-medium ${className}`}
    >
      {OPTIONS.map(({ language, short, label }) => (
        <button
          key={language}
          type="button"
          lang={language}
          title={label}
          aria-pressed={current === language}
          onClick={() => setUiLanguage(language)}
          className={`rounded px-2 py-1 ${
            current === language ? 'bg-accent text-on-accent' : 'text-muted hover:bg-sunken'
          }`}
        >
          {short}
        </button>
      ))}
    </div>
  );
}
