from pydantic import BaseModel, ConfigDict
from typing import Optional


    
from computor_types.deployments import GitLabConfigGet
from computor_types.base import BaseEntityGet, EntityInterface, ListQuery
from computor_types.users import UserList

import logging

logger = logging.getLogger(__name__)

class CourseMemberGitLabConfig(GitLabConfigGet):
  full_path_submission: Optional[str] = None

class CourseMemberProperties(BaseModel):
    gitlab: Optional[CourseMemberGitLabConfig] = None
    
    model_config = ConfigDict(
        extra='allow'
    )
    
class CourseMemberCreate(BaseModel):
    id: Optional[str] = None
    properties: Optional[CourseMemberProperties] = None
    user_id: str
    course_id: str
    course_group_id: Optional[str] = None
    course_role_id: str

class CourseMemberGet(BaseEntityGet):
    id: str
    properties: Optional[CourseMemberProperties] = None
    user_id: str
    course_id: str
    course_group_id: Optional[str] = None
    course_role_id: str
    user: Optional[UserList] = None

    model_config = ConfigDict(from_attributes=True)

class CourseMemberList(BaseModel):
    id: str
    user_id: str
    course_id: str
    course_group_id: Optional[str] = None # not done
    course_role_id: str
    user: UserList

    model_config = ConfigDict(from_attributes=True)

class CourseMemberUpdate(BaseModel):
    properties: Optional[CourseMemberProperties] = None
    course_group_id: Optional[str] = None
    course_role_id: Optional[str] = None
    
class CourseMemberQuery(ListQuery):
    id: Optional[str] = None
    user_id: Optional[str] = None
    course_id: Optional[str] = None
    course_group_id: Optional[str] = None
    course_role_id: Optional[str] = None
    properties: Optional[CourseMemberProperties] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None

# BACKEND FUNCTION - Moved to backend in Phase 4
# def course_member_search(db: 'Session', query, params: Optional[CourseMemberQuery]):
#
#     UserA = aliased(User)
#     query = query.join(UserA, UserA.id == CourseMember.user_id)
#
#     if params.id != None:
#         query = query.filter(id == params.id)
#     if params.user_id != None:
#         query = query.filter(user_id == params.user_id)
#     if params.course_id != None:
#         query = query.filter(course_id == params.course_id)
#     if params.course_group_id != None:
#         query = query.filter(course_group_id == params.course_group_id)
#     if params.course_role_id != None:
#         query = query.filter(course_role_id == params.course_role_id)
#
#     if params.given_name != None:
#         query = query.filter(given_name == params.given_name)
#     if params.family_name != None:
#         query = query.filter(family_name == params.family_name)
#
#     return query.order_by(UserA.family_name)
#
# BACKEND FUNCTION - Moved to backend in Phase 4
# async def post_create(course_member: CourseMember, db: Session):
#
#     if course_member.user.user_type != "user":
#         return
#
#     # # Only create submission groups for students
#     # if course_member.course_role_id != "_student":
#     #     return
#
#     # First, let's see what CourseContents exist
#     all_course_contents = db.query(CourseContent).filter(
#         CourseContent.course_id == course_member.course_id
#     ).all()
#     logger.info(f"Total CourseContents in course: {len(all_course_contents)}")
#     for cc in all_course_contents:
#         # Check if the type and kind exist
#         cc_type = db.query(CourseContentType).filter(id == cc.course_content_type_id).first()
#         if cc_type:
#             cc_kind = db.query(CourseContentKind).filter(id == cc_type.course_content_kind_id).first()
#             logger.info(f"  - CourseContent {cc.id}: max_group_size={cc.max_group_size}, type={cc_type.id}, kind={cc_kind.id if cc_kind else 'None'}, submittable={cc_kind.submittable if cc_kind else 'N/A'}")
#         else:
#             logger.info(f"  - CourseContent {cc.id}: max_group_size={cc.max_group_size}, type_id={cc.course_content_type_id} (TYPE NOT FOUND)")
#
#     # Get all individual submittable course contents (max_group_size == 1)
#     course_contents = (
#         db.query(
#             CourseContent.id,
#             CourseContent.course_id,
#             CourseContent.max_test_runs,
#             CourseContent.max_submissions,
#             CourseContent.max_group_size)
#         .join(CourseContentType, CourseContentType.id == CourseContent.course_content_type_id)
#         .join(CourseContentKind, CourseContentKind.id == CourseContentType.course_content_kind_id)
#         .filter(
#             CourseContent.course_id == course_member.course_id,
#             CourseContentKind.submittable == True,
#             CourseContent.max_group_size == 1  # Only individual assignments
#         ).all()
#     )
#
#     submission_group_ids = []
#
#     logger.info(f"Found {len(course_contents)} submittable individual course contents for course {course_member.course_id}")
#
#     # Create submission groups for existing individual course contents
#     for id, course_id, max_test_runs, max_submissions, max_group_size in course_contents:
#         submission_group = SubmissionGroup(
#             course_id=course_id,
#             course_content_id=id,
#             max_group_size=max_group_size,
#             max_test_runs=max_test_runs,
#             max_submissions=max_submissions
#         )
#
#         db.add(submission_group)
#         db.commit()
#         db.refresh(submission_group)
#
#         submission_group_member = SubmissionGroupMember(
#             submission_group_id = submission_group.id,
#             course_member_id = course_member.id,
#             course_id = course_id  # Add course_id for consistency
#         )
#
#         db.add(submission_group_member)
#         db.commit()
#         db.refresh(submission_group_member)
#
#         submission_group_ids.append(str(submission_group.id))
#         logger.info(f"Created submission group {submission_group.id} for course content {id}")
#
#     if submission_group_ids:
#         logger.info(f"Created {len(submission_group_ids)} submission groups for student {course_member.id}")
#     else:
#         logger.info(f"No submission groups created for student {course_member.id} (no submittable individual course contents exist yet)")
#
#     # ALWAYS trigger Temporal workflow to create student repository
#     # Repository should be created even if no course content exists yet
#     try:
#         # Import at runtime to avoid circular dependency
#         from computor_types.tasks import get_task_executor, TaskSubmission
#
#         task_executor = get_task_executor()
#
#         task_submission = TaskSubmission(
#             task_name="StudentRepositoryCreationWorkflow",
#             parameters={
#                 "course_member_id": str(course_member.id),
#                 "course_id": str(course_member.course_id),
#                 "submission_group_ids": submission_group_ids,
#                 "is_team": False
#             },
#             queue="computor-tasks"
#         )
#
#         workflow_id = await task_executor.submit_task(task_submission)
#         logger.info(f"Started student repository creation workflow: {workflow_id}")
#     except Exception as e:
#         logger.error(f"Failed to trigger student repository creation: {e}")
#         # Don't fail the course member creation if repository creation fails
#
class CourseMemberInterface(EntityInterface):
    create = CourseMemberCreate
    get = CourseMemberGet
    list = CourseMemberList
    update = CourseMemberUpdate
    query = CourseMemberQuery
    # post_create = post_create  # Moved to backend in Phase 4
