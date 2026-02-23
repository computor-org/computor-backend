/**
 * Auto-generated client for StudentProfilesClient.
 * Endpoint: /student-profiles
 */

import type { StudentProfileCreate, StudentProfileGet, StudentProfileList, StudentProfileUpdate } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class StudentProfilesClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/student-profiles');
  }

  /**
   * List Student Profiles
   * List student profiles - admins/_user_manager see all, users see only their own
   */
  async listStudentProfilesStudentProfilesGet({ id, limit, organizationId, skip, studentEmail, studentId, userId }: { id?: string | null; limit?: number | null; organizationId?: string | null; skip?: number | null; studentEmail?: string | null; studentId?: string | null; userId?: string | null }): Promise<StudentProfileList[]> {
    const queryParams: Record<string, unknown> = {
      id,
      limit,
      organization_id: organizationId,
      skip,
      student_email: studentEmail,
      student_id: studentId,
      user_id: userId,
    };
    return this.client.get<StudentProfileList[]>(this.basePath, { params: queryParams });
  }

  /**
   * Create Student Profile
   * Create a student profile - users can create for themselves (user_id optional), admins/_user_manager can create for anyone
   */
  async createStudentProfileStudentProfilesPost({ userId, body }: { userId?: string | null; body: StudentProfileCreate }): Promise<StudentProfileGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<StudentProfileGet>(this.basePath, body, { params: queryParams });
  }

  /**
   * Delete Student Profile
   * Delete a student profile - users can only delete their own, admins/_user_manager can delete any
   */
  async deleteStudentProfileStudentProfilesIdDelete({ id, userId }: { id: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.delete<void>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Get Student Profile
   * Get a student profile by ID - users can only get their own, admins/_user_manager can get any
   */
  async getStudentProfileStudentProfilesIdGet({ id, userId }: { id: string | string; userId?: string | null }): Promise<StudentProfileGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<StudentProfileGet>(this.buildPath(id), { params: queryParams });
  }

  /**
   * Update Student Profile
   * Update a student profile - users can only update their own, admins/_user_manager can update any
   */
  async updateStudentProfileStudentProfilesIdPatch({ id, userId, body }: { id: string | string; userId?: string | null; body: StudentProfileUpdate }): Promise<StudentProfileGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.patch<StudentProfileGet>(this.buildPath(id), body, { params: queryParams });
  }
}
