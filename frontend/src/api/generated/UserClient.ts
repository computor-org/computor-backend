/**
 * Auto-generated client for UserClient.
 * Endpoint: /user
 */

import type { CourseMemberProviderAccountUpdate, CourseMemberReadinessStatus, CourseMemberValidationRequest, UserGet, UserPassword } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class UserClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/user');
  }

  /**
   * Get Current User Endpoint
   * Get the current authenticated user.
   */
  async getCurrentUserEndpointUserGet(): Promise<UserGet> {
    return this.client.get<UserGet>(this.basePath);
  }

  /**
   * Register Current User Course Account
   * Register user's provider account for a course.
   */
  async registerCurrentUserCourseAccountUserCoursesCourseIdRegisterPost({ courseId, body }: { courseId: string | string; body: CourseMemberProviderAccountUpdate }): Promise<CourseMemberReadinessStatus> {
    return this.client.post<CourseMemberReadinessStatus>(this.buildPath('courses', courseId, 'register'), body);
  }

  /**
   * Validate Current User Course
   * Validate user's course membership and provider account.
   */
  async validateCurrentUserCourseUserCoursesCourseIdValidatePost({ courseId, body }: { courseId: string | string; body: CourseMemberValidationRequest }): Promise<CourseMemberReadinessStatus> {
    return this.client.post<CourseMemberReadinessStatus>(this.buildPath('courses', courseId, 'validate'), body);
  }

  /**
   * Set User Password Endpoint
   * Set or update user password.
   */
  async setUserPasswordEndpointUserPasswordPost({ body }: { body: UserPassword }): Promise<void> {
    return this.client.post<void>(this.buildPath('password'), body);
  }

  /**
   * Get Course Views For Current User
   * Get available views based on roles across all courses for the current user.
   */
  async getCourseViewsForCurrentUserUserViewsGet(): Promise<string[]> {
    return this.client.get<string[]>(this.buildPath('views'));
  }
}
