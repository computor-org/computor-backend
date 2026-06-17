"""
Repository layer for direct database access with optional caching.

The package root exposes the historical repository names lazily. Importing one
repository must not import every view repository and external integration.
"""

from importlib import import_module

__all__ = [
    "BaseRepository",
    "ViewRepository",
    "RepositoryError",
    "NotFoundError",
    "DuplicateError",
    "OrganizationRepository",
    "CourseRepository",
    "CourseFamilyRepository",
    "CourseMemberRepository",
    "UserRepository",
    "SubmissionGroupRepository",
    "SubmissionArtifactRepository",
    "ResultRepository",
    "MessageRepository",
    "ExampleRepository",
    "CourseContentRepository",
    "ExampleVersionRepository",
    "SubmissionGradeRepository",
    "SubmissionGroupMemberRepository",
    "CourseContentDeploymentRepository",
    "ExampleDependencyRepository",
    "ApiTokenRepository",
    "ServiceRepository",
    "ServiceTypeRepository",
    "StudentViewRepository",
    "TutorViewRepository",
    "LecturerViewRepository",
    "CourseMemberGradingsViewRepository",
]

_EXPORTS = {
    "BaseRepository": ("base", "BaseRepository"),
    "RepositoryError": ("base", "RepositoryError"),
    "NotFoundError": ("base", "NotFoundError"),
    "DuplicateError": ("base", "DuplicateError"),
    "ViewRepository": ("view_base", "ViewRepository"),
    "OrganizationRepository": ("organization", "OrganizationRepository"),
    "CourseRepository": ("course", "CourseRepository"),
    "CourseFamilyRepository": ("course_family", "CourseFamilyRepository"),
    "CourseMemberRepository": ("course_member", "CourseMemberRepository"),
    "UserRepository": ("user", "UserRepository"),
    "SubmissionGroupRepository": ("submission_group", "SubmissionGroupRepository"),
    "SubmissionArtifactRepository": ("submission_artifact", "SubmissionArtifactRepository"),
    "ResultRepository": ("result", "ResultRepository"),
    "MessageRepository": ("message", "MessageRepository"),
    "ExampleRepository": ("example", "ExampleRepository"),
    "CourseContentRepository": ("course_content_repo", "CourseContentRepository"),
    "ExampleVersionRepository": ("example_version_repo", "ExampleVersionRepository"),
    "SubmissionGradeRepository": ("submission_grade_repo", "SubmissionGradeRepository"),
    "SubmissionGroupMemberRepository": (
        "submission_group_member_repo",
        "SubmissionGroupMemberRepository",
    ),
    "CourseContentDeploymentRepository": (
        "course_content_deployment_repo",
        "CourseContentDeploymentRepository",
    ),
    "ExampleDependencyRepository": ("example_dependency_repo", "ExampleDependencyRepository"),
    "ApiTokenRepository": ("api_token", "ApiTokenRepository"),
    "ServiceRepository": ("service", "ServiceRepository"),
    "ServiceTypeRepository": ("service_type", "ServiceTypeRepository"),
    "StudentViewRepository": ("student_view", "StudentViewRepository"),
    "TutorViewRepository": ("tutor_view", "TutorViewRepository"),
    "LecturerViewRepository": ("lecturer_view", "LecturerViewRepository"),
    "CourseMemberGradingsViewRepository": (
        "course_member_gradings_view",
        "CourseMemberGradingsViewRepository",
    ),
}


def __getattr__(name):
    try:
        module_name, export_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = import_module(f".{module_name}", __name__)
    value = getattr(module, export_name)
    globals()[name] = value
    return value
