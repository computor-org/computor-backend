import type { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import type { CourseGroupList, CourseMemberList } from 'types/generated';
import { memberName } from '@/src/utils/userName';

/** Rows per request. The API caps nothing; this is only how big a page we ask for. */
const PAGE = 500;

/**
 * Every member of a course, following the API's pagination to the end.
 *
 * The groups page used to ask for `limit: 2000` and treat the answer as the
 * whole roster. That was survivable while the members were only counted — a
 * course past the ceiling showed a low number — but not once they are listed:
 * people would simply be missing from the tree, with nothing on screen saying so.
 *
 * The list endpoint returns a bare array (the total is in an `X-Total-Count`
 * header the generated clients discard), so "done" is a short page, exactly as
 * the members table's pager infers it.
 */
export async function fetchCourseRoster(
  client: CourseMembersClient,
  courseId: string,
): Promise<CourseMemberList[]> {
  const all: CourseMemberList[] = [];
  for (let skip = 0; ; skip += PAGE) {
    const page = await client.listCourseMembersCourseMembersGet({
      courseId,
      skip,
      limit: PAGE,
    });
    all.push(...page);
    if (page.length < PAGE) return all;
  }
}

/** A group and the members in it, ready to render as two tree levels. */
export interface RosterGroup {
  /** The course group, or `null` for the trailing "not assigned yet" bucket. */
  group: CourseGroupList | null;
  /** Stable React key — a group id, or the literal for the unassigned bucket. */
  key: string;
  title: string;
  members: CourseMemberList[];
}

/** Group names sort the way a lecturer reads them: "Lab 2" before "Lab 10". */
const byName = (a: string, b: string) => a.localeCompare(b, undefined, { numeric: true });

/**
 * Bucket a course's members under their groups (#385).
 *
 * Members whose `course_group_id` is null get a bucket of their own at the end.
 * It is not decoration: the API cannot filter on `course_group_id IS NULL`, so
 * "who still needs assigning?" is a question only this page can answer, and the
 * count it used to show could never have raised it.
 *
 * Both levels are sorted here. The list endpoint returns members in primary-key
 * order, which is to say arbitrary.
 */
export function buildRoster(
  groups: CourseGroupList[],
  members: CourseMemberList[],
): RosterGroup[] {
  const buckets = new Map<string, CourseMemberList[]>();
  const unassigned: CourseMemberList[] = [];

  for (const member of members) {
    if (!member.course_group_id) {
      unassigned.push(member);
      continue;
    }
    const bucket = buckets.get(member.course_group_id);
    if (bucket) bucket.push(member);
    else buckets.set(member.course_group_id, [member]);
  }

  const sortMembers = (list: CourseMemberList[]) =>
    [...list].sort((a, b) => byName(memberName(a), memberName(b)));

  const rows: RosterGroup[] = groups
    .map((group) => ({
      group,
      key: group.id,
      title: group.title || 'Untitled group',
      members: sortMembers(buckets.get(group.id) ?? []),
    }))
    .sort((a, b) => byName(a.title, b.title));

  if (unassigned.length > 0) {
    rows.push({
      group: null,
      key: '__unassigned__',
      title: 'Not in a group',
      members: sortMembers(unassigned),
    });
  }

  return rows;
}
