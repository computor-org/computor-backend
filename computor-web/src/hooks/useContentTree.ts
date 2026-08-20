'use client';

import { useCallback, useMemo, useState } from 'react';
import { buildTree, depthOf, parentPath, type TreeNode } from '@/src/utils/ltree';
import { displayName } from '@/src/utils/displayName';

/**
 * The course content hierarchy, as data.
 *
 * Three pages drew this tree — lecturer assignments, student assignments and the
 * grading breakdown — with three tree builders, three indent scales (18px, 20px,
 * 24px) and three ideas of what starts expanded. They could not share a single
 * component because they disagree on markup: grading renders `<tr>` inside a
 * table, the other two render `<div>` rows. So the shared part is the part that
 * is genuinely the same — build, expand, flatten — and each caller keeps the
 * markup its layout needs. Pair it with <TreeRow> for the `<div>` cases.
 *
 * Returns rows already flattened in render order, so a caller is a `.map()` and
 * never a recursive renderer.
 */

/** A row ready to render: the item, its depth, and its state in the tree. */
export interface ContentTreeRow<T> {
  /** Stable across reloads — the ltree path, not an array index. */
  key: string;
  path: string;
  /** ltree depth: a root is 0. Drives the indent. */
  depth: number;
  /**
   * The backing item, or `null` for a container this tree invented — see
   * `synthesiseContainers`. A caller must handle null before reading fields.
   */
  item: T | null;
  /** Resolved name: the item's title, else the humanised last path segment. */
  label: string;
  hasChildren: boolean;
  expanded: boolean;
  /** Direct children, for a "3 assignments" summary on a unit row. */
  childCount: number;
  /** Everything beneath, at any depth. */
  descendantCount: number;
}

export interface UseContentTreeOptions {
  /**
   * Invent a container for every path segment that has no row of its own.
   *
   * The student endpoint returns bare assignments — an assignment at `week1.a`
   * arrives without a `week1` row when the unit itself is not visible to them —
   * so without this they render as a flat list of leaves and the unit structure
   * disappears. The lecturer endpoint returns the units, so it leaves this off.
   */
  synthesiseContainers?: boolean;
  /**
   * Rows deeper than this start collapsed. Omit to start fully expanded, which
   * is what a lecturer scanning deployment state wants; pass 0 or 1 for a long
   * student tree where the units are the point.
   */
  collapseBelowDepth?: number;
}

/** A path we invented; it has no row in `items`. */
type MaybeSynthetic<T> = { path: string; position?: number | null; __item: T | null };

export function useContentTree<T extends { path: string; position?: number | null; title?: string | null }>(
  items: T[],
  { synthesiseContainers = false, collapseBelowDepth }: UseContentTreeOptions = {},
) {
  // Only paths the user has *explicitly* toggled. Everything else answers to
  // collapseBelowDepth, so a reload that brings new content in does not silently
  // collapse what the user had open, and new siblings inherit the default.
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});

  const roots = useMemo(() => {
    const wrapped = new Map<string, MaybeSynthetic<T>>();
    for (const item of items) {
      wrapped.set(item.path, { path: item.path, position: item.position, __item: item });
    }

    if (synthesiseContainers) {
      for (const item of items) {
        // Walk up to the root, adding any ancestor that has no row of its own.
        for (let p = parentPath(item.path); p; p = parentPath(p)) {
          if (wrapped.has(p)) break; // this ancestor and all above it already exist
          wrapped.set(p, { path: p, position: null, __item: null });
        }
      }
    }

    return buildTree([...wrapped.values()]);
  }, [items, synthesiseContainers]);

  const isExpanded = useCallback(
    (path: string) =>
      overrides[path] ?? (collapseBelowDepth === undefined || depthOf(path) < collapseBelowDepth),
    [overrides, collapseBelowDepth],
  );

  const rows = useMemo(() => {
    const out: ContentTreeRow<T>[] = [];

    const countDescendants = (node: TreeNode<MaybeSynthetic<T>>): number =>
      node.children.reduce((n, child) => n + 1 + countDescendants(child), 0);

    const walk = (nodes: TreeNode<MaybeSynthetic<T>>[]): void => {
      for (const node of nodes) {
        const expanded = isExpanded(node.path);
        out.push({
          key: node.path,
          path: node.path,
          depth: node.depth,
          item: node.__item,
          label: displayName(node.__item ?? { path: node.path }),
          hasChildren: node.children.length > 0,
          expanded,
          childCount: node.children.length,
          descendantCount: countDescendants(node),
        });
        if (expanded) walk(node.children);
      }
    };

    walk(roots);
    return out;
  }, [roots, isExpanded]);

  const toggle = useCallback(
    (path: string) => setOverrides((prev) => ({ ...prev, [path]: !isExpanded(path) })),
    [isExpanded],
  );

  const setAllExpanded = useCallback(
    (expanded: boolean) => {
      const next: Record<string, boolean> = {};
      const walk = (nodes: TreeNode<MaybeSynthetic<T>>[]): void => {
        for (const node of nodes) {
          if (node.children.length > 0) next[node.path] = expanded;
          walk(node.children);
        }
      };
      walk(roots);
      setOverrides(next);
    },
    [roots],
  );

  return { rows, toggle, setAllExpanded, expandAll: () => setAllExpanded(true), collapseAll: () => setAllExpanded(false) };
}

export default useContentTree;
