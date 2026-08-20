/**
 * Theme preference: 'light', 'dark', or 'system'.
 *
 * 'system' is the default and stamps nothing on <html> — the CSS in globals.css
 * then follows `prefers-color-scheme`. An explicit choice stamps
 * `data-theme="light"` or `"dark"`, which both theme blocks are written to
 * honour over the OS setting.
 */
export type ThemePreference = 'light' | 'dark' | 'system';

export const THEME_STORAGE_KEY = 'computor-theme';

/** Applied to <html>. Removing the attribute is what 'system' means. */
export function applyTheme(preference: ThemePreference): void {
  const root = document.documentElement;
  if (preference === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', preference);
}

export function readTheme(): ThemePreference {
  if (typeof window === 'undefined') return 'system';
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return stored === 'light' || stored === 'dark' ? stored : 'system';
}

export function storeTheme(preference: ThemePreference): void {
  if (preference === 'system') window.localStorage.removeItem(THEME_STORAGE_KEY);
  else window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  applyTheme(preference);
  notify();
}

/**
 * Runs before the first paint, inlined in <head>.
 *
 * Has to be blocking and inline: read the preference in a component and the
 * browser has already painted the light theme, so a dark-theme user gets a
 * white flash on every navigation that reloads the document. Kept tiny and
 * wrapped in try/catch because localStorage throws in some privacy modes, and a
 * theme preference is never worth breaking the page over.
 */
export const THEME_INIT_SCRIPT = `try{var t=localStorage.getItem('${THEME_STORAGE_KEY}');if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}`;

// --- subscription, so React can read the preference without an effect ---------

const listeners = new Set<() => void>();

/** Notified on our own writes and on another tab's (via the storage event). */
export function subscribeTheme(onChange: () => void): () => void {
  listeners.add(onChange);
  window.addEventListener('storage', onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener('storage', onChange);
  };
}

/** The server has no localStorage, so it always renders the 'system' default. */
export function getServerTheme(): ThemePreference {
  return 'system';
}

function notify(): void {
  for (const listener of listeners) listener();
}
