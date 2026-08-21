'use client';

import { useSyncExternalStore } from 'react';
import {
  getServerTheme,
  readTheme,
  storeTheme,
  subscribeTheme,
  type ThemePreference,
} from '@/src/utils/theme';

const OPTIONS: { value: ThemePreference; label: string; hint: string }[] = [
  { value: 'system', label: 'System', hint: 'Follow your operating system' },
  { value: 'light', label: 'Light', hint: 'Always light' },
  { value: 'dark', label: 'Dark', hint: 'Always dark' },
];

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
  const preference = useSyncExternalStore(subscribeTheme, readTheme, getServerTheme);

  return (
    <fieldset className="flex flex-wrap gap-2">
      <legend className="sr-only">Appearance</legend>
      {OPTIONS.map((option) => {
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
