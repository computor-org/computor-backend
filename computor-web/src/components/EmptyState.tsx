'use client';

import { ReactNode } from 'react';

/**
 * Shared "no items yet" block: dashed card with an optional icon, a headline,
 * supporting text, and an optional call-to-action.
 *
 * Capped and centred: a placeholder holds one short sentence, and stretching it
 * to the full width of a wide monitor makes the emptiness look like a bug.
 *
 * `compact` is for an empty region *inside* a populated page — the "No versions."
 * slot under a section heading — where the full-height treatment would shout
 * louder than the content around it. Pages had been hand-rolling that case as a
 * bare dashed div, at three different paddings, which is why the same empty
 * message looked different on neighbouring pages.
 */
export default function EmptyState({
  icon,
  title,
  description,
  action,
  compact = false,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="w-full bg-canvas rounded-lg border border-dashed border-rule-strong p-6 text-center">
        <p className="text-sm text-muted">{title}</p>
        {description && <p className="mt-1 text-xs text-subtle">{description}</p>}
        {action && <div className="mt-3">{action}</div>}
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl bg-canvas rounded-lg border-2 border-dashed border-rule-strong p-12 text-center">
      {icon && <div className="mx-auto h-12 w-12 text-subtle [&>svg]:h-12 [&>svg]:w-12">{icon}</div>}
      <h3 className="mt-4 text-lg font-medium text-fg">{title}</h3>
      {description && <p className="mt-2 text-sm text-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
