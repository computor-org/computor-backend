/**
 * Auto-generated client for CourseMemberImportClient.
 * Endpoint: /course-member-import
 */

import type { CourseMemberImportFileParseRequest, CourseMemberImportParseResponse, CourseMemberImportRequest, CourseMemberImportResponse } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class CourseMemberImportClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/course-member-import');
  }

  /**
   * Parse Member File
   * Parse an uploaded member file (CSV/JSON/XLSX/Excel-XML) into preview rows.
   * Read-only: it never touches the database. The client shows the rows for
   * review/edit and then imports selected ones via ``POST /course-member-import/{id}``.
   * **Required Permissions**: Lecturer role or higher (admins and organization
   * managers may parse for any course).
   */
  async parseMemberFileCourseMemberImportParseCourseIdPost({ courseId, userId, body }: { courseId: string; userId?: string | null; body: CourseMemberImportFileParseRequest }): Promise<CourseMemberImportParseResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberImportParseResponse>(this.buildPath('parse', courseId), body, { params: queryParams });
  }

  /**
   * Import Member
   * Import a course member.
   * This endpoint accepts a member's data and imports them into the specified course.
   * If the member already exists, they will be updated.
   * **Required Permissions**: Lecturer role or higher (_lecturer, _maintainer, _owner)
   * Args:
   * course_id: ID of the course to import member into
   * request: Member data including email, name, group, and role
   * permissions: Current user's permissions
   * db: Database session
   * Returns:
   * Import response with created/updated course member and created group (if any)
   * Raises:
   * ForbiddenException: If user lacks lecturer role or higher
   * BadRequestException: If validation fails
   */
  async importMemberCourseMemberImportCourseIdPost({ courseId, userId, body }: { courseId: string; userId?: string | null; body: CourseMemberImportRequest }): Promise<CourseMemberImportResponse> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberImportResponse>(this.buildPath(courseId), body, { params: queryParams });
  }
}
