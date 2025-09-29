/**
 * Auto-generated client for ArtifactsClient.
 * Endpoint: /artifacts
 */

import type { ResultCreate, ResultList, ResultUpdate, SubmissionGradeCreate, SubmissionGradeDetail, SubmissionGradeListItem, SubmissionGradeUpdate, SubmissionReviewCreate, SubmissionReviewListItem, SubmissionReviewUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class ArtifactsClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/artifacts');
  }

  /**
   * Create Artifact Grade
   * Create a grade for an artifact. Requires instructor/tutor permissions.
   */
  async createArtifactGradeArtifactsArtifactIdGradesPost({ artifactId, body }: { artifactId: string; body: SubmissionGradeCreate }): Promise<SubmissionGradeDetail> {
    return this.client.post<SubmissionGradeDetail>(this.buildPath(artifactId, 'grades'), body);
  }

  /**
   * List Artifact Grades
   * List all grades for an artifact. Students can view their own grades, tutors/instructors can view all.
   */
  async listArtifactGradesArtifactsArtifactIdGradesGet({ artifactId }: { artifactId: string }): Promise<SubmissionGradeListItem[]> {
    return this.client.get<SubmissionGradeListItem[]>(this.buildPath(artifactId, 'grades'));
  }

  /**
   * Update Artifact Grade
   * Update an existing grade. Only the grader can update their own grade.
   */
  async updateArtifactGradeArtifactsGradesGradeIdPatch({ gradeId, body }: { gradeId: string; body: SubmissionGradeUpdate }): Promise<SubmissionGradeDetail> {
    return this.client.patch<SubmissionGradeDetail>(this.buildPath('grades', gradeId), body);
  }

  /**
   * Delete Artifact Grade
   * Delete a grade. Only the grader or an admin can delete.
   */
  async deleteArtifactGradeArtifactsGradesGradeIdDelete({ gradeId }: { gradeId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath('grades', gradeId));
  }

  /**
   * Create Artifact Review
   * Create a review for an artifact.
   */
  async createArtifactReviewArtifactsArtifactIdReviewsPost({ artifactId, body }: { artifactId: string; body: SubmissionReviewCreate }): Promise<SubmissionReviewListItem> {
    return this.client.post<SubmissionReviewListItem>(this.buildPath(artifactId, 'reviews'), body);
  }

  /**
   * List Artifact Reviews
   * List all reviews for an artifact. Any course member can view reviews.
   */
  async listArtifactReviewsArtifactsArtifactIdReviewsGet({ artifactId }: { artifactId: string }): Promise<SubmissionReviewListItem[]> {
    return this.client.get<SubmissionReviewListItem[]>(this.buildPath(artifactId, 'reviews'));
  }

  /**
   * Update Artifact Review
   * Update an existing review. Only the reviewer can update their own review.
   */
  async updateArtifactReviewArtifactsReviewsReviewIdPatch({ reviewId, body }: { reviewId: string; body: SubmissionReviewUpdate }): Promise<SubmissionReviewListItem> {
    return this.client.patch<SubmissionReviewListItem>(this.buildPath('reviews', reviewId), body);
  }

  /**
   * Delete Artifact Review
   * Delete a review. Only the reviewer or an admin can delete.
   */
  async deleteArtifactReviewArtifactsReviewsReviewIdDelete({ reviewId }: { reviewId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath('reviews', reviewId));
  }

  /**
   * Create Test Result
   * Create a test result for an artifact. Checks for test limitations.
   */
  async createTestResultArtifactsArtifactIdTestPost({ artifactId, body }: { artifactId: string; body: ResultCreate }): Promise<ResultList> {
    return this.client.post<ResultList>(this.buildPath(artifactId, 'test'), body);
  }

  /**
   * List Artifact Test Results
   * List all test results for an artifact. Students see their own, tutors/instructors see all.
   */
  async listArtifactTestResultsArtifactsArtifactIdTestsGet({ artifactId }: { artifactId: string }): Promise<ResultList[]> {
    return this.client.get<ResultList[]>(this.buildPath(artifactId, 'tests'));
  }

  /**
   * Update Test Result
   * Update a test result (e.g., when test completes). Only the test runner or admin can update.
   */
  async updateTestResultArtifactsTestsTestIdPatch({ testId, body }: { testId: string; body: ResultUpdate }): Promise<ResultList> {
    return this.client.patch<ResultList>(this.buildPath('tests', testId), body);
  }
}
