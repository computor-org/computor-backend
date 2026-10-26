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
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:justify-between sm:gap-4">
        <div className="min-w-0 max-w-full">
          <h1 className="text-3xl font-bold text-fg">{title}</h1>
          {subtitle != null && <div className="mt-1 text-muted">{subtitle}</div>}
        </div>
        {actions != null && <div className="flex flex-wrap items-center gap-2 sm:shrink-0 sm:justify-end">{actions}</div>}
      </div>
    </div>
  );
}
