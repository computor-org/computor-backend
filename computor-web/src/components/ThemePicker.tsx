'use client';

import { useSyncExternalStore } from 'react';
import {
  getServerTheme,
  readTheme,
  storeTheme,
  subscribeTheme,
  type ThemePreference,
} from '@/src/utils/theme';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';

type Option = { value: ThemePreference; label: string; hint: string };

const COPY: Record<'de' | 'en', { legend: string; options: Option[] }> = {
  de: {
    legend: 'Darstellung',
    options: [
      { value: 'system', label: 'System', hint: 'Folgt deinem Betriebssystem' },
      { value: 'light', label: 'Hell', hint: 'Immer hell' },
      { value: 'dark', label: 'Dunkel', hint: 'Immer dunkel' },
    ],
  },
  en: {
    legend: 'Appearance',
    options: [
      { value: 'system', label: 'System', hint: 'Follow your operating system' },
      { value: 'light', label: 'Light', hint: 'Always light' },
      { value: 'dark', label: 'Dark', hint: 'Always dark' },
    ],
  },
};

/**
 * Appearance preference.
 *
 * The value lives in localStorage, which the server cannot see, so it is read
 * through useSyncExternalStore rather than in an effect: that gives React an
 * explicit server snapshot ('system') to render against, so hydration does not
 * tear, and it picks up a change made in another tab for free. The theme itself
 * is already on the page by this point — the inline script in the root layout
 * applies it before first paint — so this only has to show which option is on.
 */
export default function ThemePicker() {
  const t = COPY[useUiLanguage()];
  const preference = useSyncExternalStore(subscribeTheme, readTheme, getServerTheme);

  return (
    <fieldset className="flex flex-wrap gap-2">
      <legend className="sr-only">{t.legend}</legend>
      {t.options.map((option) => {
        const active = preference === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => storeTheme(option.value)}
            aria-pressed={active}
            title={option.hint}
            className={`px-4 py-2 text-sm font-medium rounded border transition-colors ${
              active
                ? 'border-accent bg-accent-wash text-accent-text'
                : 'border-rule-strong text-body hover:bg-sunken'
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </fieldset>
  );
}
