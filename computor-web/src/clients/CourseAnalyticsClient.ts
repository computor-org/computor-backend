/**
 * Client for the lecturer analytics endpoints.
 * Endpoint: /course-analytics
 *
 * Hand-written like InstanceLimitsClient so call sites read well; the DTOs
 * are generated from computor_types.course_analytics.
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';
import type { CourseFlagsGet, StudentActivityGet, TypicalErrorsGet } from 'types/generated';

export class CourseAnalyticsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-analytics');
  }

  /** Failing tests grouped by normalized message, newest `maxResults` imperfect runs. */
  async typicalErrors(
    courseId: string,
    opts: { courseContentId?: string | null; maxResults?: number; language?: 'de' | 'en' } = {},
  ): Promise<TypicalErrorsGet> {
    return this.client.get<TypicalErrorsGet>(this.buildPath('courses', courseId, 'typical-errors'), {
      params: {
        course_content_id: opts.courseContentId ?? undefined,
        max_results: opts.maxResults,
        language: opts.language,
      },
    });
  }

  /** Rule-based flags for every student; only flagged students are returned. */
  async courseFlags(courseId: string, dueAt?: string | null): Promise<CourseFlagsGet> {
    return this.client.get<CourseFlagsGet>(this.buildPath('courses', courseId, 'flags'), {
      params: { due_at: dueAt ?? undefined },
    });
  }

  /** History, attempt timelines and flags of one student. */
  async studentActivity(courseMemberId: string, dueAt?: string | null): Promise<StudentActivityGet> {
    return this.client.get<StudentActivityGet>(
      this.buildPath('course-members', courseMemberId, 'activity'),
      { params: { due_at: dueAt ?? undefined } },
    );
  }
}

export const courseAnalyticsClient = new CourseAnalyticsClient();
