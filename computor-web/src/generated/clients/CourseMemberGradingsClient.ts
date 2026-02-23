/**
 * Auto-generated client for CourseMemberGradingsClient.
 * Endpoint: /course-member-gradings
 */

import type { CourseMemberGradingsGet, CourseMemberGradingsList } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseMemberGradingsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-member-gradings');
  }

  /**
   * List course member grading statistics for a course
   * Get aggregated grading and progress statistics for all course members (students) in a course.
   * Returns full course content hierarchy with submission progress for each student.
   * **Required Parameter:**
   * - `course_id`: The course ID (required)
   * **Returns:**
   * - Full hierarchical grading stats for each student
   * - Breakdown by content type (mandatory, optional, etc.)
   * - Progress percentages at all levels
   * - Latest submission dates
   * **Access Control:**
   * - Admins: Can access any course
   * - Tutors and higher: Can access courses they are assigned to
   * **Caching:**
   * - Results are cached for 30 minutes per student
   * - Cache automatically invalidates on submissions and grading changes
   */
  async listCourseMemberGradingsEndpointCourseMemberGradingsGet({ courseId, limit, skip, userId }: { courseId: string; limit?: number | null; skip?: number | null; userId?: string | null }): Promise<CourseMemberGradingsList[]> {
    const queryParams: Record<string, unknown> = {
      course_id: courseId,
      limit,
      skip,
      user_id: userId,
    };
    return this.client.get<CourseMemberGradingsList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Get course member grading statistics
   * Get aggregated grading and progress statistics for a specific course member.
   * Returns full course content hierarchy with detailed submission progress.
   * **Calculations:**
   * - **Full hierarchy**: All course content levels (no filtering)
   * - **Per ltree layer**: Maximum assignments vs. submitted assignments at each level
   * - **Per content_type**: Breakdown by mandatory, optional, etc.
   * - **Progress percentages**: Calculated at every hierarchical level
   * - **Latest submissions**: Most recent submission date per level
   * **Access Control:**
   * - Admins: Can access any course member
   * - Tutors and higher: Can access members in courses they are assigned to
   * **Caching:**
   * - Results are cached for 30 minutes
   * - Cache automatically invalidates on submissions and grading changes
   */
  async getCourseMemberGradingsEndpointCourseMemberGradingsCourseMemberIdGet({ courseMemberId, courseId, limit, skip, userId }: { courseMemberId: string | string; courseId?: string | null; limit?: number | null; skip?: number | null; userId?: string | null }): Promise<CourseMemberGradingsGet> {
    const queryParams: Record<string, unknown> = {
      course_id: courseId,
      limit,
      skip,
      user_id: userId,
    };
    return this.client.get<CourseMemberGradingsGet>(this.buildPath(courseMemberId), { params: queryParams });
  }
}
