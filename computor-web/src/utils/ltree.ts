// Shared helpers for the backend `path` (Postgres ltree) field, e.g.
// "week1.assignment2". Consolidates the depth/segment/parent primitives that
// were re-implemented across the assignment/progress trees.

/** ltree depth: "week1.assignment2" → 1, "week1" → 0. */
export const depthOf = (path: string): number => Math.max(0, path.split('.').length - 1);

/** Last path segment (the node's own label): "week1.assignment2" → "assignment2". */
export const lastSegment = (path: string): string => path.split('.').slice(-1)[0];

/** Parent path, or null at the root: "a.b.c" → "a.b", "a" → null. */
export const parentPath = (path: string): string | null =>
  path.includes('.') ? path.slice(0, path.lastIndexOf('.')) : null;

export type TreeNode<T> = T & { children: TreeNode<T>[]; depth: number };

/**
 * Build a nested tree from a flat list carrying ltree `path`s.
 *
 * Canonical sort order: siblings by `position` ascending, then by `path` as a
 * deterministic tiebreaker (the tree structure already keeps parents before
 * children). An item whose parent path is absent from `items` becomes a root.
 */
export function buildTree<T extends { path: string; position?: number | null }>(
  items: T[],
): TreeNode<T>[] {
  const sorted = [...items].sort((a, b) => {
    const posA = a.position ?? 0;
    const posB = b.position ?? 0;
    if (posA !== posB) return posA - posB;
    return a.path.localeCompare(b.path);
  });

  const nodeMap = new Map<string, TreeNode<T>>();
  const roots: TreeNode<T>[] = [];

  for (const item of sorted) {
    const node: TreeNode<T> = { ...item, children: [], depth: depthOf(item.path) };
    nodeMap.set(item.path, node);

    const parent = parentPath(item.path);
    if (parent && nodeMap.has(parent)) {
      nodeMap.get(parent)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}
