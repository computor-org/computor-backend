/**
 * Auto-generated client for UserClient.
 * Endpoint: /user
 */

import type { CourseGitDescriptor, CourseMemberProviderAccountUpdate, CourseMemberReadinessStatus, CourseMemberRepositoryGet, CourseMemberRepositoryRegister, CourseMemberValidationRequest, StudentRepositoryProvisioned, UserGet, UserScopes } from 'types/generated';
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
  async getCurrentUserEndpointUserGet({ userId }: { userId?: string | null }): Promise<UserGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<UserGet>(this.basePath, { params: queryParams });
  }

  /**
   * Get Course Git Descriptor Endpoint
   * How the current user obtains their repository for a course.
   * Returns the course's git binding — delivery mode, allowed student-repo
   * backends (Forgejo babysat / GitLab BYO / download), and the
   * ``student-template`` location. Gated on course membership; returns an
   * ``unconfigured`` descriptor when the course has no git binding yet.
   */
  async getCourseGitDescriptorEndpointUserCoursesCourseIdGitGet({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<CourseGitDescriptor> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseGitDescriptor>(this.buildPath('courses', courseId, 'git'), { params: queryParams });
  }

  /**
   * Provision Student Repository Endpoint
   * Babysat Forgejo provisioning for the current student.
   * Forks the course's student-template into the student's own repository and
   * records it. Idempotent — returns the existing repo if already provisioned.
   * Also returns a **one-time** repo-scoped Forgejo clone token (`clone_token` +
   * `clone_username`) so `git clone`/push authenticates; it is rotated on each
   * call and never returned by `GET .../repository`. Requires the course to be
   * bound to a managed Forgejo server offering the ``forgejo`` mode.
   */
  async provisionStudentRepositoryEndpointUserCoursesCourseIdProvisionRepositoryPost({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<StudentRepositoryProvisioned> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<StudentRepositoryProvisioned>(this.buildPath('courses', courseId, 'provision-repository'), { params: queryParams });
  }

  /**
   * Register Current User Course Account
   * Register user's provider account for a course.
   */
  async registerCurrentUserCourseAccountUserCoursesCourseIdRegisterPost({ courseId, userId, body }: { courseId: string | string; userId?: string | null; body: CourseMemberProviderAccountUpdate }): Promise<CourseMemberReadinessStatus> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberReadinessStatus>(this.buildPath('courses', courseId, 'register'), body, { params: queryParams });
  }

  /**
   * Register Gitlab Managed Endpoint
   * Register the current student's GitLab PAT for a managed-GitLab course and
   * grant them access to their repository.
   * ``GET /api/v4/user`` with the student's PAT proves their GitLab identity; the
   * backend links the account and uses the registry's group token to add them as
   * a Maintainer on their repo (Reporter on the template). Provisions the repo
   * first if needed. Idempotent.
   */
  async registerGitlabManagedEndpointUserCoursesCourseIdRegisterGitlabPost({ courseId, userId, body }: { courseId: string | string; userId?: string | null; body: CourseMemberValidationRequest }): Promise<CourseMemberRepositoryGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberRepositoryGet>(this.buildPath('courses', courseId, 'register-gitlab'), body, { params: queryParams });
  }

  /**
   * Register Student Repository Endpoint
   * Record where the current student's BYO repository lives (e.g. a GitLab
   * repo created by the VSCode extension with the student's own PAT).
   * Tracking only — the backend never reads the repo (grading is API upload).
   * Upserts the per-membership record; the course must offer the given mode.
   */
  async registerStudentRepositoryEndpointUserCoursesCourseIdRegisterRepositoryPost({ courseId, userId, body }: { courseId: string | string; userId?: string | null; body: CourseMemberRepositoryRegister }): Promise<CourseMemberRepositoryGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberRepositoryGet>(this.buildPath('courses', courseId, 'register-repository'), body, { params: queryParams });
  }

  /**
   * Get Student Repository Endpoint
   * The current student's repository for a course, or ``null`` if none yet.
   * The babysitting "do I already have a repo?" check — returns the recorded
   * repo (Forgejo babysat or BYO) without creating one. 404 only when the caller
   * is not a member of the course.
   */
  async getStudentRepositoryEndpointUserCoursesCourseIdRepositoryGet({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<CourseMemberRepositoryGet | null> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<CourseMemberRepositoryGet | null>(this.buildPath('courses', courseId, 'repository'), { params: queryParams });
  }

  /**
   * Download Template Archive Endpoint
   * Download the course template as a ZIP (download mode / external-repo seed).
   * The backend fetches the template from the bound managed git server with its
   * service token and returns the archive — the student never handles the token.
   * Membership-gated.
   */
  async downloadTemplateArchiveEndpointUserCoursesCourseIdTemplateArchiveGet({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<void> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<void>(this.buildPath('courses', courseId, 'template', 'archive'), { params: queryParams });
  }

  /**
   * Validate Current User Course
   * Validate user's course membership and provider account.
   */
  async validateCurrentUserCourseUserCoursesCourseIdValidatePost({ courseId, userId, body }: { courseId: string | string; userId?: string | null; body: CourseMemberValidationRequest }): Promise<CourseMemberReadinessStatus> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberReadinessStatus>(this.buildPath('courses', courseId, 'validate'), body, { params: queryParams });
  }

  /**
   * Get Current User Scopes
   * Per-scope role memberships for the current user.
   * Returns ``is_admin`` plus three maps (``organization``,
   * ``course_family``, ``course``) keyed by scope_id, each listing the
   * role labels the user holds on that scope. The client can use this
   * to pre-gate UI against the same authorization data the server uses
   * internally — e.g. only show the "Post organization message" button
   * on orgs where the user has ``_owner``/``_manager``.
   * Admins receive empty maps with ``is_admin=true``; treat that as
   * "every role on every scope".
   */
  async getCurrentUserScopesUserScopesGet(): Promise<UserScopes> {
    return this.client.get<UserScopes>(this.buildPath('scopes'));
  }

  /**
   * Get Course Views For Current User
   * Get available views for the current user.
   * The ``lecturer`` view is the org → course-family → course creation
   * pipeline plus the example library, so it is granted to ``_admin``,
   * ``_organization_manager``, ``_example_manager``, any organization- or
   * course-family-scoped role, and course lecturers (or higher). Computed
   * purely from the principal — no DB hit.
   */
  async getCourseViewsForCurrentUserUserViewsGet(): Promise<string[]> {
    return this.client.get<string[]>(this.buildPath('views'));
  }

  /**
   * Get Course Views For Current User By Course
   * Get available views based on role for a specific course for the current user.
   * student/tutor/lecturer are course-role perspectives (membership-based). The
   * ``management`` view is course administration (member management, …) and is
   * granted to the lecturer cohort — admins, organization managers, and course
   * lecturers or higher — even when they hold no student/tutor/lecturer role.
   */
  async getCourseViewsForCurrentUserByCourseUserViewsCourseIdGet({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<string[]> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.get<string[]>(this.buildPath('views', courseId), { params: queryParams });
  }
}
