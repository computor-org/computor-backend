/**
 * Auto-generated client for AnalyticsClient.
 * Endpoint: /analytics
 */

import type { AnalyticsCourseAccess, AnalyticsCourseSummary, AnalyticsExampleSource, AnalyticsJobStatus, AnalyticsRefreshRequest, AnalyticsStandardExample, AnalyticsStudentList, AnalyticsStudentReport, AnalyticsStudentTimeline } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class AnalyticsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/analytics');
  }

  /**
   * List Analytics Courses
   */
  async listAnalyticsCoursesAnalyticsCoursesGet({ userId }: { userId?: string | null }): Promise<AnalyticsCourseAccess[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<AnalyticsCourseAccess[]>(this.buildPath('courses'), { params: queryParams });
  }

  /**
   * Get Analytics Example Source
   * Source files of the example deployed to a content. The deployment mapping
   * comes from the analytics snapshot; the files are fetched live from the source
   * instance, server side, so the browser never touches the source. Gated by the
   * analytics read role. 404 (rendered as a calm notice) when the snapshot has no
   * deployment for the content or the source API is unreachable/unconfigured.
   */
  async getAnalyticsExampleSourceAnalyticsCoursesCourseIdExamplesContentIdSourceGet({ contentId, courseId, userId }: { contentId: string; courseId: string; userId?: string | null }): Promise<AnalyticsExampleSource> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<AnalyticsExampleSource>(this.buildPath('courses', courseId, 'examples', contentId, 'source'), { params: queryParams });
  }

  /**
   * List Course Analytics Jobs
   */
  async listCourseAnalyticsJobsAnalyticsCoursesCourseIdJobsGet({ courseId, limit, userId }: { courseId: string; limit?: number; userId?: string | null }): Promise<AnalyticsJobStatus[]> {
    const queryParams: Record<string, unknown> = {
      limit,
      user_id: userId,
    };
    return this.client.get<AnalyticsJobStatus[]>(this.buildPath('courses', courseId, 'jobs'), { params: queryParams });
  }

  /**
   * Refresh Course Analytics
   */
  async refreshCourseAnalyticsAnalyticsCoursesCourseIdRefreshPost({ courseId, userId, body }: { courseId: string; userId?: string | null; body: AnalyticsRefreshRequest }): Promise<AnalyticsJobStatus> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<AnalyticsJobStatus>(this.buildPath('courses', courseId, 'refresh'), body, { params: queryParams });
  }

  /**
   * List Course Analytics Students
   */
  async listCourseAnalyticsStudentsAnalyticsCoursesCourseIdStudentsGet({ courseId, gradingCutoff, submissionCutoff, userId }: { courseId: string; gradingCutoff?: string | null; submissionCutoff?: string | null; userId?: string | null }): Promise<AnalyticsStudentList> {
    const queryParams: Record<string, unknown> = {
      grading_cutoff: gradingCutoff,
      submission_cutoff: submissionCutoff,
      user_id: userId,
    };
    return this.client.get<AnalyticsStudentList>(this.buildPath('courses', courseId, 'students'), { params: queryParams });
  }

  /**
   * Get Course Analytics Student Report
   */
  async getCourseAnalyticsStudentReportAnalyticsCoursesCourseIdStudentsCourseMemberIdGet({ courseId, courseMemberId, gradingCutoff, submissionCutoff, userId }: { courseId: string; courseMemberId: string; gradingCutoff?: string | null; submissionCutoff?: string | null; userId?: string | null }): Promise<AnalyticsStudentReport> {
    const queryParams: Record<string, unknown> = {
      grading_cutoff: gradingCutoff,
      submission_cutoff: submissionCutoff,
      user_id: userId,
    };
    return this.client.get<AnalyticsStudentReport>(this.buildPath('courses', courseId, 'students', courseMemberId), { params: queryParams });
  }

  /**
   * List Course Analytics Student Examples
   */
  async listCourseAnalyticsStudentExamplesAnalyticsCoursesCourseIdStudentsCourseMemberIdExamplesGet({ courseId, courseMemberId, gradingCutoff, submissionCutoff, userId }: { courseId: string; courseMemberId: string; gradingCutoff?: string | null; submissionCutoff?: string | null; userId?: string | null }): Promise<AnalyticsStandardExample[]> {
    const queryParams: Record<string, unknown> = {
      grading_cutoff: gradingCutoff,
      submission_cutoff: submissionCutoff,
      user_id: userId,
    };
    return this.client.get<AnalyticsStandardExample[]>(this.buildPath('courses', courseId, 'students', courseMemberId, 'examples'), { params: queryParams });
  }

  /**
   * Get Course Analytics Student Timeline
   */
  async getCourseAnalyticsStudentTimelineAnalyticsCoursesCourseIdStudentsCourseMemberIdTimelineGet({ courseId, courseMemberId, gradingCutoff, submissionCutoff, userId }: { courseId: string; courseMemberId: string; gradingCutoff?: string | null; submissionCutoff?: string | null; userId?: string | null }): Promise<AnalyticsStudentTimeline> {
    const queryParams: Record<string, unknown> = {
      grading_cutoff: gradingCutoff,
      submission_cutoff: submissionCutoff,
      user_id: userId,
    };
    return this.client.get<AnalyticsStudentTimeline>(this.buildPath('courses', courseId, 'students', courseMemberId, 'timeline'), { params: queryParams });
  }

  /**
   * Get Course Analytics Summary
   */
  async getCourseAnalyticsSummaryAnalyticsCoursesCourseIdSummaryGet({ courseId, gradingCutoff, submissionCutoff, userId }: { courseId: string; gradingCutoff?: string | null; submissionCutoff?: string | null; userId?: string | null }): Promise<AnalyticsCourseSummary> {
    const queryParams: Record<string, unknown> = {
      grading_cutoff: gradingCutoff,
      submission_cutoff: submissionCutoff,
      user_id: userId,
    };
    return this.client.get<AnalyticsCourseSummary>(this.buildPath('courses', courseId, 'summary'), { params: queryParams });
  }

  /**
   * Get Analytics Job
   */
  async getAnalyticsJobAnalyticsJobsJobIdGet({ jobId, userId }: { jobId: string; userId?: string | null }): Promise<AnalyticsJobStatus> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<AnalyticsJobStatus>(this.buildPath('jobs', jobId), { params: queryParams });
  }
}
