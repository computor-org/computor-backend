'use client';

import { ReactNode } from 'react';
import { TONE_CHIP_CLS, type Tone } from './ui/tones';

/**
 * Shared status/role chip. One colour per semantic meaning, one shape per
 * concept — replaces the ad-hoc badge spans whose colours drifted per page
 * (green-700 vs green-800, blue vs indigo role tags, rounded vs rounded-full).
 *
 * Prefer `tone`: naming the meaning rather than the colour is what lets the
 * palette move — to a dark theme, or to the extension's user theme — without
 * visiting a single call site. `color` is the original API, kept as a set of
 * aliases so existing callers keep working; it is deprecated and new code
 * should not use it.
 */
export type BadgeColor =
  | 'green' // success / active
  | 'red' // danger / error / archived-with-alarm
  | 'yellow' // warning / pending
  | 'blue' // info / role tag
  | 'purple' // special roles
  | 'gray'; // neutral / archived

/** Deprecated colour name → the tone it always meant. */
const COLOR_ALIAS: Record<BadgeColor, Tone> = {
  green: 'success',
  red: 'error',
  yellow: 'warning',
  blue: 'info',
  // `purple` had exactly one job — the test/submission budget chip — and it read
  // as "extra information about this row", which is what info means. Folding it
  // in costs one hue and removes a tone with no semantics behind it.
  purple: 'info',
  gray: 'muted',
};

export default function Badge({
  tone,
  color,
  pill = false,
  className = '',
  title,
  children,
}: {
  tone?: Tone;
  /** @deprecated Pass `tone` instead — see COLOR_ALIAS for the mapping. */
  color?: BadgeColor;
  /** Pills for live statuses (running/active), squares for classifications. */
  pill?: boolean;
  className?: string;
  /** Hover explanation for a badge whose one-word label needs one. */
  title?: string;
  children: ReactNode;
}) {
  const resolved: Tone = tone ?? (color ? COLOR_ALIAS[color] : 'muted');

  return (
    <span
      title={title}
      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium ${
        pill ? 'rounded-full' : 'rounded'
      } ${TONE_CHIP_CLS[resolved]} ${className}`}
    >
      {children}
    </span>
  );
}
