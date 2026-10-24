// A learner's own progress through a course, computed from the student
// course-contents listing (issues#408, #525).
//
// What counts: an assignment is done once it is submitted. Submitting is the
// one step the learner takes on purpose to say "this one is finished", and it is
// the state the assignment list already shows as "Eingereicht". A passing test
// result is not required, because many assignments are partly open-ended, and a
// bar that stays short after a deliberate submission would read as a failure.
// Units and other non-submittable content are not counted.
//
// "Weiter mit" points at the first assignment, in course order, that is not yet
// submitted. Course order is the order of the tree on the assignments page
// (siblings by position, then path), so the pointer and the list agree.

import { buildTree, parentPath, type TreeNode } from './ltree';
import { displayName } from './displayName';

export interface ProgressContent {
  id: string;
  path: string;
  position?: number | null;
  title?: string | null;
  course_content_kind_id: string;
  submitted?: boolean | null;
  result?: { result?: number | null } | null;
}

export interface UnitProgress {
  submitted: number;
  total: number;
}

export interface NextAssignment<T> {
  item: T;
  /** Names of the enclosing units, outermost first ("Woche 3"). */
  trail: string[];
}

export interface CourseProgress<T> {
  submitted: number;
  total: number;
  /** Anything submitted or tested yet: "Weiter mit" rather than "Beginne mit". */
  started: boolean;
  /** First assignment not yet submitted, or null when there is none left. */
  next: NextAssignment<T> | null;
  /** Assignment counts beneath every container path, at any depth. */
  units: Map<string, UnitProgress>;
}

export const isAssignment = (c: ProgressContent): boolean => c.course_content_kind_id === 'assignment';

type Node<T> = { path: string; position?: number | null; item: T | null };

/** Assignments in the order the course tree draws them. */
export function assignmentsInCourseOrder<T extends ProgressContent>(contents: T[]): T[] {
  const nodes = new Map<string, Node<T>>();
  for (const c of contents) nodes.set(c.path, { path: c.path, position: c.position, item: c });
  // An assignment whose unit is hidden still sorts under that unit, as on the page.
  for (const c of contents) {
    for (let p = parentPath(c.path); p && !nodes.has(p); p = parentPath(p)) {
      nodes.set(p, { path: p, position: null, item: null });
    }
  }

  const out: T[] = [];
  const walk = (level: TreeNode<Node<T>>[]): void => {
    for (const node of level) {
      if (node.item && isAssignment(node.item)) out.push(node.item);
      walk(node.children);
    }
  };
  walk(buildTree([...nodes.values()]));
  return out;
}

export function courseProgress<T extends ProgressContent>(contents: T[]): CourseProgress<T> {
  const byPath = new Map(contents.map((c) => [c.path, c]));
  const ordered = assignmentsInCourseOrder(contents);
  const units = new Map<string, UnitProgress>();

  for (const a of ordered) {
    for (let p = parentPath(a.path); p; p = parentPath(p)) {
      const u = units.get(p) ?? { submitted: 0, total: 0 };
      u.total += 1;
      if (a.submitted) u.submitted += 1;
      units.set(p, u);
    }
  }

  const nextItem = ordered.find((a) => !a.submitted) ?? null;
  let next: NextAssignment<T> | null = null;
  if (nextItem) {
    const trail: string[] = [];
    for (let p = parentPath(nextItem.path); p; p = parentPath(p)) {
      trail.unshift(displayName(byPath.get(p) ?? { path: p }));
    }
    next = { item: nextItem, trail };
  }

  return {
    submitted: ordered.filter((a) => a.submitted).length,
    total: ordered.length,
    started: ordered.some((a) => a.submitted || a.result != null),
    next,
    units,
  };
}

/** Whole percent, never 100 before the last assignment is in. */
export function progressPercent({ submitted, total }: { submitted: number; total: number }): number {
  if (total <= 0) return 0;
  return submitted >= total ? 100 : Math.min(99, Math.round((submitted / total) * 100));
}
