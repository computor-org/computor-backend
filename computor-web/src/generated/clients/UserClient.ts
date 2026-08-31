/**
 * Auto-generated client for UserClient.
 * Endpoint: /user
 */

import type { CourseGitDescriptor, CourseMemberGet, CourseMemberProviderAccountUpdate, CourseMemberReadinessStatus, CourseMemberRepositoryGet, CourseMemberRepositoryRegister, CourseMemberValidationRequest, PersonalCloneCredentialGet, StudentRepositoryProvisioned, TemplateAccessGet, UserGet, UserScopes } from 'types/generated';
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
   * Personal Clone Credential Endpoint
   * A clone credential for working OUTSIDE the managed workspace (#342).
   * Deliberately not the workspace's own token: that one (`computor-vscode`)
   * is re-minted by every credential repair, which silently invalidated
   * whatever a student had copied off the course page. This mints a second
   * Forgejo token named `computor-cli` — rotation is keyed by name, so the two
   * never invalidate each other. Returned unchanged on later calls; pass
   * `rotate=true` to revoke it and mint a fresh one. Requires the student's
   * repository to exist (Check access / opening the course in the workspace
   * creates it).
   */
  async personalCloneCredentialEndpointUserCoursesCourseIdCloneCredentialPost({ courseId, rotate, userId }: { courseId: string | string; rotate?: boolean; userId?: string | null }): Promise<PersonalCloneCredentialGet> {
    const queryParams: Record<string, unknown> = {
      rotate,
      user_id: userId,
    };
    return this.client.post<PersonalCloneCredentialGet>(this.buildPath('courses', courseId, 'clone-credential'), { params: queryParams });
  }

  /**
   * Enrol yourself as a student in a public course
   * Create your own ``_student`` membership in a public course.
   * Named ``enroll`` rather than ``register`` because ``POST
   * /user/courses/{course_id}/register`` above already means "register your git
   * provider account for this course" — two unrelated meanings one letter apart
   * would be a trap.
   * The request has no body. The role is not a parameter: self-registration can
   * only ever produce ``_student``, in the course's first existing group (or a
   * ``default`` group created for the purpose). Idempotent — an existing
   * membership of any role comes back unchanged with a 200, so a lecturer who
   * clicks Enrol is not demoted. There is no matching DELETE; course staff
   * remove members.
   * 404 when the course does not exist *or* is not public: a private course
   * must not be distinguishable from a missing one.
   */
  async enrollInPublicCourseUserCoursesCourseIdEnrollPost({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<CourseMemberGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<CourseMemberGet>(this.buildPath('courses', courseId, 'enroll'), { params: queryParams });
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
   * Also returns the repo-scoped Forgejo clone token (`clone_token` +
   * `clone_username`) so `git clone`/push authenticates; it is never returned by
   * `GET .../repository`. Requires the course to be bound to a managed Forgejo
   * server offering the ``forgejo`` mode.
   * The token is minted once and returned unchanged on later calls: Forgejo
   * keeps one token per user and instance, so re-minting would break the copy
   * stored in every repo the student has already cloned. Pass `rotate=true` to
   * force a fresh one — the escape hatch when the credential stopped working —
   * which invalidates the previous token, so the client must then update the
   * remotes of all its clones on that server.
   */
  async provisionStudentRepositoryEndpointUserCoursesCourseIdProvisionRepositoryPost({ courseId, rotate, userId }: { courseId: string | string; rotate?: boolean; userId?: string | null }): Promise<StudentRepositoryProvisioned> {
    const queryParams: Record<string, unknown> = {
      rotate,
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
   * Template Access Endpoint
   * Mint a one-time READ-ONLY git credential for the course's template.
   * Lets the current course member fetch the student-template over git — the
   * extension uses it to seed an external repo with full history and to merge
   * new template commits into the student's repo. The token is rotated on each
   * call under its own name (never touching the provisioning clone token) and
   * cannot push. `token` is null until the member's first git-server SSO login
   * (re-call afterwards). Managed-Forgejo courses only.
   */
  async templateAccessEndpointUserCoursesCourseIdTemplateAccessPost({ courseId, userId }: { courseId: string | string; userId?: string | null }): Promise<TemplateAccessGet> {
    const queryParams: Record<string, unknown> = {
      user_id: userId,
    };
    return this.client.post<TemplateAccessGet>(this.buildPath('courses', courseId, 'template-access'), { params: queryParams });
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
