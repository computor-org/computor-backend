'use client';

import type { ReactNode } from 'react';
import type { Crumb } from './Breadcrumbs';
import ListPageLayout, { ScrollArea, ListLoading } from './ListPageLayout';
import PageHeader from './PageHeader';
import ErrorBanner from './ErrorBanner';

/**
 * Standard read-only detail page: a fixed PageHeader (breadcrumb trail, title,
 * subtitle, and the entity's verbs top-right) over a scrolling body.
 *
 * The missing sibling of <FormPanel>. Create and edit already shared a scaffold,
 * so every one of those routes looked identical; detail pages had none, so each
 * hand-rolled its own header — three of them skipped breadcrumbs entirely and
 * offered a "← Back to X" link instead, at two different title sizes.
 *
 * The body owns its own vertical rhythm (`space-y-6`): pages stop passing
 * `space-y-*` per call site, which is how the gap between sections ended up at
 * 12px, 16px, 24px and 32px on neighbouring pages.
 *
 * `width` matches FormPanel's cap. Default `narrow` suits a column of facts;
 * pass `wide` when the body is a table or a card grid that wants the room.
 */
export default function DetailPanel({
  breadcrumbs,
  title,
  subtitle,
  actions,
  error,
  loading,
  loadingLabel,
  width = 'narrow',
  children,
}: {
  breadcrumbs: Crumb[];
  title: string;
  subtitle?: ReactNode;
  /** The entity's verbs — Edit, Delete, Download. Rendered top-right. */
  actions?: ReactNode;
  error?: string | null;
  /** While true the body is replaced by a centred placeholder. */
  loading?: boolean;
  loadingLabel?: string;
  width?: 'wide' | 'narrow';
  children: ReactNode;
}) {
  return (
    <ListPageLayout width={width}>
      <PageHeader breadcrumbs={breadcrumbs} title={title} subtitle={subtitle} actions={actions} />

      <ErrorBanner>{error}</ErrorBanner>

      {loading ? (
        <ListLoading>{loadingLabel}</ListLoading>
      ) : (
        <ScrollArea className="space-y-6">{children}</ScrollArea>
      )}
    </ListPageLayout>
  );
}
