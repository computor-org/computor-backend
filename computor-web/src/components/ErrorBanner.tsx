'use client';

import type { ReactNode } from 'react';

/** The red error box repeated across pages. Renders nothing when empty. */
export default function ErrorBanner({ children }: { children?: ReactNode }) {
  if (!children) return null;
  return <div className="p-3 bg-danger-wash border border-danger-line rounded text-sm text-danger-text">{children}</div>;
}
