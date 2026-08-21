/**
 * The semantic tone vocabulary from the design spec (§2).
 *
 * Always name the meaning, never the colour: `tone="error"`, not `color="red"`.
 * That is what lets the same component render correctly against this app's fixed
 * palette and against the extension's arbitrary user theme, and it is what makes
 * the eventual dark-mode swap a change to these maps rather than to every caller.
 *
 * One type, several bindings — a chip fills its background, a statistic colours
 * only its number — so each component picks the map that suits it instead of
 * inventing its own set of names.
 */
export type Tone = 'success' | 'warning' | 'error' | 'info' | 'muted';

/** Filled chip: tinted background + readable foreground. Used by Badge. */
export const TONE_CHIP_CLS: Record<Tone, string> = {
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  muted: 'bg-gray-100 text-gray-700',
};

/** Foreground only, for a number or a word sitting on a plain panel. */
export const TONE_TEXT_CLS: Record<Tone, string> = {
  success: 'text-green-700',
  warning: 'text-amber-700',
  error: 'text-red-700',
  info: 'text-blue-700',
  muted: 'text-gray-900',
};
