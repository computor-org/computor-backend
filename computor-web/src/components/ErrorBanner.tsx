'use client';

import type { ReactNode } from 'react';

/** The red error box repeated across pages. Renders nothing when empty. */
export default function ErrorBanner({ children }: { children?: ReactNode }) {
  if (!children) return null;
  return <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{children}</div>;
}
