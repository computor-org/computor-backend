'use client';

import type { ReactNode } from 'react';
import type { Tone } from './tones';

/**
 * A short inline message about the page's state — "3 contents have a newer
 * example version", "release started".
 *
 * <ErrorBanner> is the error-toned case and stays as the shorthand for it. This
 * covers the other four tones, which pages had been hand-rolling: the same
 * notice appeared as orange-50/orange-200/orange-800 on one page and
 * amber-50/amber-200/amber-900 on another, three lines apart in the same repo.
 *
 * Distinct from Badge: a badge labels a *thing* in a list, a notice speaks about
 * the page. Different shape, so they are never confused at a glance.
 */
const TONE_CLS: Record<Tone, string> = {
  success: 'bg-green-50 border-green-200 text-green-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-900',
  error: 'bg-red-50 border-red-200 text-red-700',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  muted: 'bg-gray-50 border-gray-200 text-gray-700',
};

export default function Notice({
  tone = 'info',
  className = '',
  children,
}: {
  tone?: Tone;
  className?: string;
  children?: ReactNode;
}) {
  if (!children) return null;
  return (
    <div className={`p-3 border rounded text-sm ${TONE_CLS[tone]} ${className}`}>{children}</div>
  );
}
