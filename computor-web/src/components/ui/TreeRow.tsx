'use client';

import type { ReactNode } from 'react';
import { hiddenRowCls, hiddenRowMarkCls, hiddenRowTitleCls, rowTitleCls } from './tokens';

/** 4px ladder, step 5. One indent for every content tree in the app. */
const INDENT_PER_LEVEL = 20;

/**
 * One row of a course content tree.
 *
 * The three trees had picked 18px, 20px and 24px of indent, three marker shapes
 * and three separators, so moving between a lecturer's and a student's view of
 * the same course felt like moving between two products. This is the row; the
 * structure comes from useContentTree.
 *
 * `hidden` dims a row the students cannot see (issue #338) rather than removing
 * it — a lecturer keeps seeing every hidden unit, that is the point of the flag.
 */
export default function TreeRow({
  depth,
  expandable = false,
  expanded = false,
  onToggle,
  markerColor,
  markerTitle,
  label,
  hidden = false,
  children,
}: {
  depth: number;
  expandable?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
  /** The content type's colour. Falls back to a neutral dot when absent. */
  markerColor?: string | null;
  markerTitle?: string;
  label: ReactNode;
  /** Not visible to students, here or via an ancestor. */
  hidden?: boolean;
  /** Right-aligned badges and actions. */
  children?: ReactNode;
}) {
  return (
    // On a phone the badges move to a second line under the title instead of
    // squeezing it to nothing: the title is what the row is about.
    <div className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 px-4 py-2.5 sm:flex-nowrap ${hidden ? hiddenRowCls : ''}`}>
      <div className="flex min-w-0 flex-1 basis-full items-center gap-3 sm:basis-0">
        <div style={{ width: depth * INDENT_PER_LEVEL }} className="shrink-0" />

        {/* The chevron keeps its box on a leaf row, so titles down a level stay
            aligned instead of stepping left wherever a row has no children. */}
        <span className="shrink-0 w-4 h-4 flex items-center justify-center">
          {expandable && (
            <button
              type="button"
              onClick={onToggle}
              aria-expanded={expanded}
              aria-label={expanded ? `Collapse ${typeof label === 'string' ? label : 'section'}` : `Expand ${typeof label === 'string' ? label : 'section'}`}
              className="text-subtle hover:text-body transition-colors"
            >
              <svg
                className={`h-3.5 w-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </span>

        <span
          className={`shrink-0 h-2.5 w-2.5 rounded-full ${hidden ? hiddenRowMarkCls : ''}`}
          style={{ backgroundColor: markerColor || '#cbd5e1' }}
          title={markerTitle}
        />

        <div className="min-w-0 flex-1">
          <div className={`text-sm font-medium truncate ${hidden ? hiddenRowTitleCls : rowTitleCls}`}>
            {label}
          </div>
        </div>
      </div>

      {children != null && children !== false && (
        <div className="ml-auto flex flex-wrap empty:hidden items-center justify-end gap-3 sm:flex-nowrap">{children}</div>
      )}
    </div>
  );
}

/** The bordered card a list of TreeRows sits in. */
export function TreeRows({ children }: { children: ReactNode }) {
  return <div className="bg-surface border border-rule rounded-lg divide-y divide-rule-soft">{children}</div>;
}
