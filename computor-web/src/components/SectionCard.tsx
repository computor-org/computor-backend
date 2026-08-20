'use client';

import { ReactNode } from 'react';

/**
 * A titled panel on a settings page: white card, heading, optional right-hand
 * slot, optional footer note.
 *
 * This chrome was hand-rolled on every settings section, which is why those
 * pages carried most of the app's raw palette classes. One component, so the
 * card radius and border live in a single place.
 */
export default function SectionCard({
  title,
  action,
  note,
  children,
}: {
  title: string;
  /** Right-aligned slot in the header — a status chip or a small control. */
  action?: ReactNode;
  /** Explanatory paragraph rendered directly under the heading. */
  note?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        {action}
      </div>
      {note && (
        <p className="text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded p-2.5">{note}</p>
      )}
      {children}
    </section>
  );
}

/** Muted status text shown beside a section's save button. */
export function SectionStatus({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <span className="text-sm text-gray-500">{children}</span>;
}

/** Muted explanatory line inside a section body. */
export function SectionHint({ children }: { children: ReactNode }) {
  return <p className="text-sm text-gray-500">{children}</p>;
}
