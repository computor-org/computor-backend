'use client';

import { ReactNode } from 'react';

/**
 * Shared "no items yet" block for list pages: dashed card with an optional
 * icon, a headline, supporting text, and an optional call-to-action.
 */
export default function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
      {icon && <div className="mx-auto h-12 w-12 text-gray-400 [&>svg]:h-12 [&>svg]:w-12">{icon}</div>}
      <h3 className="mt-4 text-lg font-medium text-gray-900">{title}</h3>
      {description && <p className="mt-2 text-sm text-gray-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
