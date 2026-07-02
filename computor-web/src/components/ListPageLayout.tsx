'use client';

import type { ReactNode } from 'react';

/**
 * Full-height scaffold for pages with a fixed header over a scrolling body.
 *
 * Fills AuthenticatedLayout's scroll area as a flex column so a fixed header
 * (put `<PageHeader>` first), any toolbars, and a pinned footer stay put while
 * only the body scrolls. Give the scrolling body a <ScrollPanel> (bordered, for
 * tables), a <ScrollArea> (borderless, for stacked cards / free content), or a
 * <ListLoading> while loading, so it claims the flexible space; pin a pager by
 * making it the last child with `shrink-0`.
 *
 *   <ListPageLayout>
 *     <PageHeader … />
 *     {loading ? <ListLoading>…</ListLoading> : (
 *       <ScrollPanel>
 *         <table>…<thead className="sticky top-0 z-10">…</table>
 *       </ScrollPanel>
 *     )}
 *     <div className="shrink-0 …">…pager…</div>
 *   </ListPageLayout>
 */
export default function ListPageLayout({ children }: { children: ReactNode }) {
  return <div className="p-6 flex flex-col h-full min-h-0 gap-6">{children}</div>;
}

/**
 * Borderless region that grows to fill the layout and scrolls internally — the
 * body for pages whose content isn't a single table (e.g. a stack of cards).
 * Pass `space-y-*` via className for inter-child spacing.
 */
export function ScrollArea({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return <div className={`flex-1 min-h-0 overflow-y-auto ${className}`}>{children}</div>;
}

/**
 * Bordered card that grows to fill the layout and scrolls both axes — the body
 * for table pages. Pair it with a `sticky top-0 z-10` <thead> so table headers
 * stay pinned while the body scrolls.
 */
export function ScrollPanel({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <ScrollArea className={`overflow-x-auto rounded-lg border border-gray-200 bg-white ${className}`}>
      {children}
    </ScrollArea>
  );
}

/** Centered, borderless placeholder that occupies the scroll body while loading. */
export function ListLoading({ children = 'Loading…' }: { children?: ReactNode }) {
  return <div className="flex-1 min-h-0 flex items-center justify-center text-gray-500">{children}</div>;
}
