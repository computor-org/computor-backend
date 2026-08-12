// Human-readable names for entities that carry a backend `path` (Postgres
// ltree) alongside an optional `title`.
//
// The ltree path is an internal identifier, not a name: it is unique only
// within its parent scope (four different courses in data/deployments/courses
// all carry `matlab.2027`), so showing it tells the reader nothing and can
// actively mislead. It belongs in edit forms — where it is the immutable slug
// being edited — and nowhere else in the UI.
//
// `title` is nullable on organization / course_family / course / course_content,
// so a fallback is still needed. Fall back to the humanised LAST segment, which
// mirrors the backend's `_humanize` (business_logic/course_deployment.py) — the
// same string the backend itself stores as the title for YAML-deployed content.

import { lastSegment } from './ltree';

/** "logical_indexing" → "Logical Indexing". Mirrors the backend `_humanize`. */
export function humanizeSegment(segment: string): string {
  const words = segment.replace(/[_-]+/g, ' ').split(' ').filter(Boolean);
  return words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') || segment;
}

/**
 * The name to show for a path-carrying entity: its title, else the humanised
 * last path segment, else `fallback`.
 *
 * Never returns an id — a UUID is worse than the generic fallback, since it is
 * neither recognisable nor typeable.
 */
export function displayName(
  entity: { title?: string | null; path?: string | null } | null | undefined,
  fallback = 'Untitled',
): string {
  const title = entity?.title?.trim();
  if (title) return title;
  const path = entity?.path?.trim();
  if (path) return humanizeSegment(lastSegment(path));
  return fallback;
}
