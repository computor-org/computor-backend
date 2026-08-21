import type { GradedByCourseMember } from 'types/generated';

/**
 * The grader's display name, or null when the API did not send one.
 *
 * `GradingAuthor` is deliberately just given/family name — the backend never
 * exposes a grader's email to a student. When even that is missing there is
 * nothing to show: the raw `user_id` UUID is not a name, and printing it (as
 * the VS Code extension's `extractGraderName` does) tells the student nothing
 * while looking like a bug.
 */
export function graderName(grader?: GradedByCourseMember | null): string | null {
  const name = [grader?.user?.given_name, grader?.user?.family_name]
    .filter(Boolean)
    .join(' ')
    .trim();
  return name || null;
}
