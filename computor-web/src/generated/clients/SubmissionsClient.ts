/**
 * Auto-generated client for SubmissionsClient.
 * Endpoint: /submissions
 */

import type { GradingStatus, ResultCreate, ResultGet, ResultList, ResultUpdate, SubmissionArtifactGet, SubmissionArtifactList, SubmissionArtifactUpdate, SubmissionGradeCreate, SubmissionGradeDetail, SubmissionGradeList, SubmissionGradeUpdate, SubmissionReviewCreate, SubmissionReviewListItem, SubmissionReviewUpdate, SubmissionUploadResponseModel } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SubmissionsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/submissions');
  }

  /**
   * List Submission Artifacts
   * List submission artifacts with optional filtering.
   * Query parameters:
   * - submission_group_id: Filter by submission group
   * - uploaded_by_course_member_id: Filter by uploader
   * - content_type: Filter by content type
   * - submit: Filter by official submissions (True) or test runs (False)
   * - with_latest_result: If True, include latest successful result (status=0) for each artifact
   */
  async listSubmissionArtifactsSubmissionsArtifactsGet({ contentType, courseContentId, id, latest, limit, skip, submissionGroupId, submit, uploadedByCourseMemberId, userId, versionIdentifier, withLatestResult }: { contentType?: string | null; courseContentId?: string | null; id?: string | null; latest?: boolean | null; limit?: number | null; skip?: number | null; submissionGroupId?: string | null; submit?: boolean | null; uploadedByCourseMemberId?: string | null; userId?: string | null; versionIdentifier?: string | null; withLatestResult?: boolean }): Promise<SubmissionArtifactList[]> {
    const queryParams: Record<string, unknown> = {
      content_type: contentType,
      course_content_id: courseContentId,
      id,
      latest,
      limit,
      skip,
      submission_group_id: submissionGroupId,
      submit,
      uploaded_by_course_member_id: uploadedByCourseMemberId,
      user_id: userId,
      version_identifier: versionIdentifier,
      with_latest_result: withLatestResult,
    };
    return this.client.get<SubmissionArtifactList[]>(this.buildPath('artifacts'), { params: queryParams });
  }

  /**
   * Upload Submission
   * Upload a submission file to MinIO and create matching SubmissionArtifact records.
   * Security & Limits:
   * - Maximum file size: 10MB (configurable via MINIO_MAX_UPLOAD_SIZE env var)
   * - Request body size enforced by middleware before processing
   * - File validation: extension, MIME type, and content checks
   * Performance Notes:
   * - Entire file is read into memory for validation
   * - For large files, this endpoint may take 5-15 seconds
   * - Configure uvicorn timeout if needed: --timeout-keep-alive 300
   * - Does NOT block other API requests (async processing)
   */
  async uploadSubmissionSubmissionsArtifactsPost({ userId }: { userId?: string | null }): Promise<SubmissionUploadResponseModel> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<SubmissionUploadResponseModel>(this.buildPath('artifacts'), { params: queryParams });
  }

  /**
   * Download Latest Submission
   * Download the latest submission artifact as a ZIP file.
   * You must provide EITHER:
   * - submission_group_id: Direct submission group ID
   * OR
   * - course_content_id + course_member_id: To find the submission group
   * Optional filters:
   * - version_identifier: Filter by specific version (e.g., "v1.0.0", "commit-abc123")
   * - submit_only: Only include official submissions (submit=True), default: True
   */
  async downloadLatestSubmissionSubmissionsArtifactsDownloadGet({ courseContentId, courseMemberId, submissionGroupId, submitOnly, userId, versionIdentifier }: { courseContentId?: string | null; courseMemberId?: string | null; submissionGroupId?: string | null; submitOnly?: boolean; userId?: string | null; versionIdentifier?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      course_content_id: courseContentId,
      course_member_id: courseMemberId,
      submission_group_id: submissionGroupId,
      submit_only: submitOnly,
      user_id: userId,
      version_identifier: versionIdentifier,
    };
    return this.client.get<void>(this.buildPath('artifacts', 'download'), { params: queryParams });
  }

  /**
   * Get Submission Artifact
   * Get details of a specific submission artifact.
   */
  async getSubmissionArtifactSubmissionsArtifactsArtifactIdGet({ artifactId, userId }: { artifactId: string; userId?: string | null }): Promise<SubmissionArtifactGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<SubmissionArtifactGet>(this.buildPath('artifacts', artifactId), { params: queryParams });
  }

  /**
   * Update Submission Artifact
   * Update a submission artifact (e.g., change submit status).
   */
  async updateSubmissionArtifactSubmissionsArtifactsArtifactIdPatch({ artifactId, userId, body }: { artifactId: string; userId?: string | null; body: SubmissionArtifactUpdate }): Promise<SubmissionArtifactGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<SubmissionArtifactGet>(this.buildPath('artifacts', artifactId), body, { params: queryParams });
  }

  /**
   * Download Submission Artifact
   * Download a specific submission artifact as a ZIP file by artifact ID.
   */
  async downloadSubmissionArtifactSubmissionsArtifactsArtifactIdDownloadGet({ artifactId, userId }: { artifactId: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath('artifacts', artifactId, 'download'), { params: queryParams });
  }

  /**
   * List Artifact Grades
   * List all grades for an artifact. Students can view their own grades, tutors/instructors can view all.
   * Query parameters:
   * - graded_by_course_member_id: Filter by grader
   * - status: Filter by grading status
   * - latest: If True, return only the most recent grade
   * - start_date: Filter grades at or after this datetime
   * - end_date: Filter grades at or before this datetime
   */
  async listArtifactGradesSubmissionsArtifactsArtifactIdGradesGet({ artifactId, courseId, endDate, gradedByCourseMemberId, id, latest, limit, skip, startDate, status, userId }: { artifactId: string; courseId?: string | null; endDate?: string | null; gradedByCourseMemberId?: string | null; id?: string | null; latest?: boolean | null; limit?: number | null; skip?: number | null; startDate?: string | null; status?: GradingStatus | null; userId?: string | null }): Promise<SubmissionGradeList[]> {
    const queryParams: Record<string, unknown> = {
      course_id: courseId,
      end_date: endDate,
      graded_by_course_member_id: gradedByCourseMemberId,
      id,
      latest,
      limit,
      skip,
      start_date: startDate,
      status,
      user_id: userId,
    };
    return this.client.get<SubmissionGradeList[]>(this.buildPath('artifacts', artifactId, 'grades'), { params: queryParams });
  }

  /**
   * Create Artifact Grade Endpoint
   * Create a grade for an artifact. Requires instructor/tutor permissions.
   */
  async createArtifactGradeEndpointSubmissionsArtifactsArtifactIdGradesPost({ artifactId, userId, body }: { artifactId: string; userId?: string | null; body: SubmissionGradeCreate }): Promise<SubmissionGradeDetail> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<SubmissionGradeDetail>(this.buildPath('artifacts', artifactId, 'grades'), body, { params: queryParams });
  }

  /**
   * List Artifact Reviews
   * List all reviews for an artifact. Any course member can view reviews.
   */
  async listArtifactReviewsSubmissionsArtifactsArtifactIdReviewsGet({ artifactId, userId }: { artifactId: string; userId?: string | null }): Promise<SubmissionReviewListItem[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<SubmissionReviewListItem[]>(this.buildPath('artifacts', artifactId, 'reviews'), { params: queryParams });
  }

  /**
   * Create Artifact Review
   * Create a review for an artifact.
   */
  async createArtifactReviewSubmissionsArtifactsArtifactIdReviewsPost({ artifactId, userId, body }: { artifactId: string; userId?: string | null; body: SubmissionReviewCreate }): Promise<SubmissionReviewListItem> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<SubmissionReviewListItem>(this.buildPath('artifacts', artifactId, 'reviews'), body, { params: queryParams });
  }

  /**
   * Create Test Result
   * Create a test result for an artifact. Checks for test limitations.
   */
  async createTestResultSubmissionsArtifactsArtifactIdTestPost({ artifactId, userId, body }: { artifactId: string; userId?: string | null; body: ResultCreate }): Promise<ResultList> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<ResultList>(this.buildPath('artifacts', artifactId, 'test'), body, { params: queryParams });
  }

  /**
   * List Artifact Test Results
   * List test results for an artifact. By default only successful results (status=0) are returned.
   * Use include_failed=true to also include failed/cancelled/crashed results.
   * Students see their own, tutors/instructors see all.
   */
  async listArtifactTestResultsSubmissionsArtifactsArtifactIdTestsGet({ artifactId, includeFailed, userId }: { artifactId: string; includeFailed?: boolean; userId?: string | null }): Promise<ResultGet[]> {
    const queryParams: Record<string, unknown> = {
      include_failed: includeFailed,
      user_id: userId,
    };
    return this.client.get<ResultGet[]>(this.buildPath('artifacts', artifactId, 'tests'), { params: queryParams });
  }

  /**
   * List Grades
   * List submission grades with filtering.
   * Query parameters:
   * - artifact_id: Filter by specific artifact
   * - graded_by_course_member_id: Filter by grader
   * - status: Filter by grading status
   * - course_id: Filter by course
   * - latest: If True, return only the most recent grade per artifact
   * - start_date: Filter grades at or after this datetime
   * - end_date: Filter grades at or before this datetime
   */
  async listGradesSubmissionsGradesGet({ artifactId, courseId, endDate, gradedByCourseMemberId, id, latest, limit, skip, startDate, status, userId }: { artifactId?: string | null; courseId?: string | null; endDate?: string | null; gradedByCourseMemberId?: string | null; id?: string | null; latest?: boolean | null; limit?: number | null; skip?: number | null; startDate?: string | null; status?: GradingStatus | null; userId?: string | null }): Promise<SubmissionGradeList[]> {
    const queryParams: Record<string, unknown> = {
      artifact_id: artifactId,
      course_id: courseId,
      end_date: endDate,
      graded_by_course_member_id: gradedByCourseMemberId,
      id,
      latest,
      limit,
      skip,
      start_date: startDate,
      status,
      user_id: userId,
    };
    return this.client.get<SubmissionGradeList[]>(this.buildPath('grades'), { params: queryParams });
  }

  /**
   * Delete Artifact Grade
   * Delete a grade. Only the grader or an admin can delete.
   */
  async deleteArtifactGradeSubmissionsGradesGradeIdDelete({ gradeId, userId }: { gradeId: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('grades', gradeId), { params: queryParams });
  }

  /**
   * Update Artifact Grade
   * Update an existing grade. Only the grader can update their own grade.
   */
  async updateArtifactGradeSubmissionsGradesGradeIdPatch({ gradeId, userId, body }: { gradeId: string; userId?: string | null; body: SubmissionGradeUpdate }): Promise<SubmissionGradeDetail> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<SubmissionGradeDetail>(this.buildPath('grades', gradeId), body, { params: queryParams });
  }

  /**
   * Delete Artifact Review
   * Delete a review. Only the reviewer or an admin can delete.
   */
  async deleteArtifactReviewSubmissionsReviewsReviewIdDelete({ reviewId, userId }: { reviewId: string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath('reviews', reviewId), { params: queryParams });
  }

  /**
   * Update Artifact Review
   * Update an existing review. Only the reviewer can update their own review.
   */
  async updateArtifactReviewSubmissionsReviewsReviewIdPatch({ reviewId, userId, body }: { reviewId: string; userId?: string | null; body: SubmissionReviewUpdate }): Promise<SubmissionReviewListItem> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<SubmissionReviewListItem>(this.buildPath('reviews', reviewId), body, { params: queryParams });
  }

  /**
   * Update Test Result
   * Update a test result (e.g., when test completes). Only the test runner or admin can update.
   */
  async updateTestResultSubmissionsTestsTestIdPatch({ testId, userId, body }: { testId: string; userId?: string | null; body: ResultUpdate }): Promise<ResultList> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<ResultList>(this.buildPath('tests', testId), body, { params: queryParams });
  }
}
