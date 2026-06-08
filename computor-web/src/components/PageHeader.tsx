'use client';

import type { ReactNode } from 'react';
import Breadcrumbs, { type Crumb } from './Breadcrumbs';

/**
 * Breadcrumb trail + title (+ optional subtitle and right-aligned actions) —
 * the header block shared by list and detail pages.
 */
export default function PageHeader({
  breadcrumbs,
  title,
  subtitle,
  actions,
}: {
  breadcrumbs: Crumb[];
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div>
      <Breadcrumbs items={breadcrumbs} />
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
          {subtitle != null && <div className="mt-1 text-gray-600">{subtitle}</div>}
        </div>
        {actions != null && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
