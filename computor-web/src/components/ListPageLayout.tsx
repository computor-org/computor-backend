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
 *
 * `width` caps how far the page spreads on a large monitor. Default `wide`
 * suits tables and card grids, where column density is the point; `narrow`
 * suits forms, detail pages and anything that is really a column of prose —
 * without it a 2560px monitor stretches a six-field form across the room. The
 * cap wraps the header too, so PageHeader's actions stay aligned with the body
 * beneath them instead of drifting to the far edge.
 *
 * Capped but left-aligned, not centred: the shell already anchors everything to
 * the sidebar, so centring would slide the title sideways each time you moved
 * between a wide list and its narrow create form.
 */
export default function ListPageLayout({
  width = 'wide',
  children,
}: {
  width?: 'wide' | 'narrow';
  children: ReactNode;
}) {
  return (
    <div
      className={`p-6 flex flex-col h-full min-h-0 gap-6 w-full ${
        width === 'narrow' ? 'max-w-4xl' : 'max-w-[110rem]'
      }`}
    >
      {children}
    </div>
  );
}

/**
 * Borderless region that grows to fill the layout and scrolls internally — the
 * body for pages whose content isn't a single table (e.g. a stack of cards).
 *
 * `spacing` names what the children ARE, not how many pixels sit between them.
 * Pages used to pass `space-y-*` themselves and picked 12px, 16px, 24px and
 * 32px for the same job, so moving between two pages of the same kind changed
 * the page's rhythm under you. There are two rhythms and this owns both.
 *
 * `scroll-slim` gives the thumb its inset so it never touches the content, and
 * `scroll-gutter` reserves its width so the content doesn't shift sideways when
 * the list crosses the fold. Bordered bodies opt out of the gutter — see
 * <ScrollPanel>.
 */
export type ScrollAreaSpacing = 'sections' | 'rows' | 'none';

const SPACING_CLS: Record<ScrollAreaSpacing, string> = {
  /** Titled blocks — cards, panels, a summary strip above a list. */
  sections: 'space-y-6',
  /** A stack of peer rows or small cards that read as one list. */
  rows: 'space-y-3',
  /** The body is a grid, or a single child that owns its own spacing. */
  none: '',
};

export function ScrollArea({
  spacing = 'sections',
  className = '',
  gutter = true,
  children,
}: {
  spacing?: ScrollAreaSpacing;
  className?: string;
  gutter?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className={`flex-1 min-h-0 overflow-y-auto scroll-slim scroll-fade ${gutter ? 'scroll-gutter' : ''} ${SPACING_CLS[spacing]} ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Bordered card that grows to fill the layout and scrolls both axes — the body
 * for table pages. Pair it with a `sticky top-0 z-10` <thead> so table headers
 * stay pinned while the body scrolls.
 *
 * No scrollbar gutter here: `scrollbar-gutter: stable` reserves space on every
 * axis whose overflow is `auto`, and this panel is `overflow-x-auto` too, so it
 * would leave a permanent empty strip along the bottom edge inside the border.
 * The table's own cell padding already keeps rows off the thumb.
 */
export function ScrollPanel({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <ScrollArea
      className={`overflow-x-auto rounded-lg border border-rule bg-surface ${className}`}
      gutter={false}
    >
      {children}
    </ScrollArea>
  );
}

/**
 * The surface's commit action, pinned below the scroll body.
 *
 * Rendered as the LAST child of <ListPageLayout>, after the ScrollArea — the
 * arrangement ListPageLayout's own docstring describes for a pager. A Save that
 * lives at the bottom of the scrolling body instead scrolls away exactly when a
 * form is long enough to need it, which is the one case where you want it.
 *
 * For a page whose fields sit in a <form>, keep the submit here and wire it with
 * the HTML `form=` attribute, the way <FormPanel> does, so Enter still submits.
 *
 * Only for a surface with ONE commit. A page whose cards each save separately
 * keeps its buttons in the cards: a single pinned "Save" cannot say which card
 * it means.
 */
export function PageActions({
  className = '',
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`shrink-0 flex flex-wrap items-center gap-3 border-t border-rule pt-4 ${className}`}>
      {children}
    </div>
  );
}

/** Centered, borderless placeholder that occupies the scroll body while loading. */
export function ListLoading({ children = 'Loading…' }: { children?: ReactNode }) {
  return <div className="flex-1 min-h-0 flex items-center justify-center text-muted">{children}</div>;
}

/**
 * The whole page, while it has nothing to show yet.
 *
 * For the moment before a form or a detail page has its data — where pages had
 * been returning a bare `<div className="p-6">Loading…</div>`. That sits at the
 * top-left of an empty viewport, then the real page replaces it with a header
 * 24px lower, so every edit page visibly jumped on load. This occupies the same
 * scaffold the page is about to use, so nothing moves.
 *
 * Default `narrow` matches FormPanel; pass `wide` ahead of a table or grid.
 */
export function PageLoading({
  width = 'narrow',
  children,
}: {
  width?: 'wide' | 'narrow';
  children?: ReactNode;
}) {
  return (
    <ListPageLayout width={width}>
      <ListLoading>{children}</ListLoading>
    </ListPageLayout>
  );
}
