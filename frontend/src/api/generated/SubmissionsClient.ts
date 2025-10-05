/**
 * Auto-generated client for SubmissionsClient.
 * Endpoint: /submissions
 */

import type { ResultCreate, ResultList, ResultUpdate, SubmissionArtifactGet, SubmissionArtifactList, SubmissionArtifactUpdate, SubmissionGradeCreate, SubmissionGradeDetail, SubmissionGradeListItem, SubmissionGradeUpdate, SubmissionReviewCreate, SubmissionReviewListItem, SubmissionReviewUpdate, SubmissionUploadResponseModel } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class SubmissionsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/submissions');
  }

  /**
   * List Submission Artifacts
   * List submission artifacts with optional filtering.
   */
  async listSubmissionArtifactsSubmissionsArtifactsGet({ courseContentId, limit, offset, submissionGroupId }: { courseContentId?: string | null; limit?: number; offset?: number; submissionGroupId?: string | null }): Promise<SubmissionArtifactList[]> {
    const queryParams: Record<string, unknown> = {
      course_content_id: courseContentId,
      limit,
      offset,
      submission_group_id: submissionGroupId,
    };
    return this.client.get<SubmissionArtifactList[]>(this.buildPath('artifacts'), { params: queryParams });
  }

  /**
   * Upload Submission
   * Upload a submission file to MinIO and create matching SubmissionArtifact records.
   */
  async uploadSubmissionSubmissionsArtifactsPost(): Promise<SubmissionUploadResponseModel> {
    return this.client.post<SubmissionUploadResponseModel>(this.buildPath('artifacts'));
  }

  /**
   * Get Submission Artifact
   * Get details of a specific submission artifact.
   */
  async getSubmissionArtifactSubmissionsArtifactsArtifactIdGet({ artifactId }: { artifactId: string }): Promise<SubmissionArtifactGet> {
    return this.client.get<SubmissionArtifactGet>(this.buildPath('artifacts', artifactId));
  }

  /**
   * Update Submission Artifact
   * Update a submission artifact (e.g., change submit status).
   */
  async updateSubmissionArtifactSubmissionsArtifactsArtifactIdPatch({ artifactId, body }: { artifactId: string; body: SubmissionArtifactUpdate }): Promise<SubmissionArtifactGet> {
    return this.client.patch<SubmissionArtifactGet>(this.buildPath('artifacts', artifactId), body);
  }

  /**
   * List Artifact Grades
   * List all grades for an artifact. Students can view their own grades, tutors/instructors can view all.
   */
  async listArtifactGradesSubmissionsArtifactsArtifactIdGradesGet({ artifactId }: { artifactId: string }): Promise<SubmissionGradeListItem[]> {
    return this.client.get<SubmissionGradeListItem[]>(this.buildPath('artifacts', artifactId, 'grades'));
  }

  /**
   * Create Artifact Grade Endpoint
   * Create a grade for an artifact. Requires instructor/tutor permissions.
   */
  async createArtifactGradeEndpointSubmissionsArtifactsArtifactIdGradesPost({ artifactId, body }: { artifactId: string; body: SubmissionGradeCreate }): Promise<SubmissionGradeDetail> {
    return this.client.post<SubmissionGradeDetail>(this.buildPath('artifacts', artifactId, 'grades'), body);
  }

  /**
   * List Artifact Reviews
   * List all reviews for an artifact. Any course member can view reviews.
   */
  async listArtifactReviewsSubmissionsArtifactsArtifactIdReviewsGet({ artifactId }: { artifactId: string }): Promise<SubmissionReviewListItem[]> {
    return this.client.get<SubmissionReviewListItem[]>(this.buildPath('artifacts', artifactId, 'reviews'));
  }

  /**
   * Create Artifact Review
   * Create a review for an artifact.
   */
  async createArtifactReviewSubmissionsArtifactsArtifactIdReviewsPost({ artifactId, body }: { artifactId: string; body: SubmissionReviewCreate }): Promise<SubmissionReviewListItem> {
    return this.client.post<SubmissionReviewListItem>(this.buildPath('artifacts', artifactId, 'reviews'), body);
  }

  /**
   * Create Test Result
   * Create a test result for an artifact. Checks for test limitations.
   */
  async createTestResultSubmissionsArtifactsArtifactIdTestPost({ artifactId, body }: { artifactId: string; body: ResultCreate }): Promise<ResultList> {
    return this.client.post<ResultList>(this.buildPath('artifacts', artifactId, 'test'), body);
  }

  /**
   * List Artifact Test Results
   * List all test results for an artifact. Students see their own, tutors/instructors see all.
   */
  async listArtifactTestResultsSubmissionsArtifactsArtifactIdTestsGet({ artifactId }: { artifactId: string }): Promise<ResultList[]> {
    return this.client.get<ResultList[]>(this.buildPath('artifacts', artifactId, 'tests'));
  }

  /**
   * Delete Artifact Grade
   * Delete a grade. Only the grader or an admin can delete.
   */
  async deleteArtifactGradeSubmissionsGradesGradeIdDelete({ gradeId }: { gradeId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath('grades', gradeId));
  }

  /**
   * Update Artifact Grade
   * Update an existing grade. Only the grader can update their own grade.
   */
  async updateArtifactGradeSubmissionsGradesGradeIdPatch({ gradeId, body }: { gradeId: string; body: SubmissionGradeUpdate }): Promise<SubmissionGradeDetail> {
    return this.client.patch<SubmissionGradeDetail>(this.buildPath('grades', gradeId), body);
  }

  /**
   * Delete Artifact Review
   * Delete a review. Only the reviewer or an admin can delete.
   */
  async deleteArtifactReviewSubmissionsReviewsReviewIdDelete({ reviewId }: { reviewId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath('reviews', reviewId));
  }

  /**
   * Update Artifact Review
   * Update an existing review. Only the reviewer can update their own review.
   */
  async updateArtifactReviewSubmissionsReviewsReviewIdPatch({ reviewId, body }: { reviewId: string; body: SubmissionReviewUpdate }): Promise<SubmissionReviewListItem> {
    return this.client.patch<SubmissionReviewListItem>(this.buildPath('reviews', reviewId), body);
  }

  /**
   * Update Test Result
   * Update a test result (e.g., when test completes). Only the test runner or admin can update.
   */
  async updateTestResultSubmissionsTestsTestIdPatch({ testId, body }: { testId: string; body: ResultUpdate }): Promise<ResultList> {
    return this.client.patch<ResultList>(this.buildPath('tests', testId), body);
  }
}
