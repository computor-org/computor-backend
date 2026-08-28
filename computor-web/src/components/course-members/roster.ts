import type { CourseMembersClient } from '@/src/generated/clients/CourseMembersClient';
import type { CourseMemberList } from 'types/generated';

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
