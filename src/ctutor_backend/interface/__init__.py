from .base import EntityInterface
from .accounts import AccountInterface
from .course_content_kind import CourseContentKindInterface
from .course_content_types import CourseContentTypeInterface
from .course_contents import CourseContentInterface
from .course_execution_backends import CourseExecutionBackendInterface
from .course_families import CourseFamilyInterface
from .course_groups import CourseGroupInterface
from .course_member_comments import CourseMemberCommentInterface
from .course_members import CourseMemberInterface
from .course_roles import CourseRoleInterface
from .courses import CourseInterface
from .execution_backends import ExecutionBackendInterface
from .grading import CourseSubmissionGroupGradingInterface, GradingStatus
from .organizations import OrganizationInterface
from .results import ResultInterface
from .roles import RoleInterface
from .student_course_contents import CourseContentStudentInterface
from .student_courses import CourseStudentInterface
from .student_profile import StudentProfileInterface
from .submission_group_members import SubmissionGroupMemberInterface
from .submission_groups import SubmissionGroupInterface
from .submissions import SubmissionCreate, SubmissionUploadResponseModel, SubmissionUploadedFile
from .course_member_accounts import CourseMemberReadinessStatus, CourseMemberProviderAccountUpdate
from .user_roles import UserRoleInterface
from .users import UserInterface
from .roles_claims import RoleClaimInterface
from .extensions import ExtensionInterface

def get_all_dtos():
    def recurse(cls):
        subs = []
        for sub in cls.__subclasses__():
            subs.append(sub)
            subs += recurse(sub)
        return subs

    return recurse(EntityInterface)
