from typing import Optional
from uuid import UUID
from httpx import Client
from ctutor_backend.client.crud_client import CrudClient
from ctutor_backend.interface.accounts import AccountCreate, AccountGet, AccountInterface, AccountQuery
from ctutor_backend.interface.deployments import ApiConfig, ComputorDeploymentConfig, ExecutionBackendConfig, CourseGroupConfig
from ctutor_backend.interface.course_contents import CourseContentCreate, CourseContentGet, CourseContentInterface, CourseContentQuery, CourseContentUpdate
from ctutor_backend.interface.course_content_types import CourseContentTypeGet, CourseContentTypeInterface, CourseContentTypeQuery
from ctutor_backend.interface.course_members import CourseMemberCreate, CourseMemberGet, CourseMemberInterface, CourseMemberProperties, CourseMemberQuery, CourseMemberUpdate
from ctutor_backend.interface.submission_group_members import SubmissionGroupMemberCreate, SubmissionGroupMemberGet, SubmissionGroupMemberInterface, SubmissionGroupMemberQuery
from ctutor_backend.interface.submission_groups import SubmissionGroupCreate, SubmissionGroupInterface
from ctutor_backend.interface.users import UserCreate, UserGet, UserInterface, UserQuery
from ctutor_backend.interface.course_execution_backends import CourseExecutionBackendCreate, CourseExecutionBackendGet, CourseExecutionBackendInterface, CourseExecutionBackendQuery
from ctutor_backend.interface.execution_backends import ExecutionBackendGet, ExecutionBackendInterface, ExecutionBackendQuery
from ctutor_backend.interface.course_groups import CourseGroupCreate, CourseGroupGet, CourseGroupInterface, CourseGroupQuery
from ctutor_backend.interface.courses import CourseCreate, CourseGet, CourseInterface, CourseProperties, CourseQuery, CourseUpdate
from ctutor_backend.interface.course_families import CourseFamilyCreate, CourseFamilyGet, CourseFamilyInterface, CourseFamilyProperties, CourseFamilyQuery, CourseFamilyUpdate
from ctutor_backend.interface.organizations import OrganizationCreate, OrganizationGet, OrganizationInterface, OrganizationProperties, OrganizationQuery, OrganizationType, OrganizationUpdate

def validate_organization_api(deyployment: ComputorDeploymentConfig, api: ApiConfig, properties: OrganizationProperties = None) -> OrganizationGet:

    client = CrudClient(url_base=api.url,entity_interface=OrganizationInterface,auth=(api.user, api.password))

    entities = client.list(OrganizationQuery(path=deyployment.organization.path, organization_type=OrganizationType.organization))

    # TODO: REFACTORING
    type = None
    if properties.gitlab != None:
        type="gitlab"
    else:
        raise NotImplementedError()
    
    if len(entities) == 0:
        entity = client.create(OrganizationCreate(
                            title=deyployment.organization.name,
                            path=deyployment.organization.path,
                            organization_type=OrganizationType.organization,
                            type=type,
                            properties=properties
                        ))

    elif len(entities) > 0 and properties != None:   
        entity = client.update(str(entities[0].id), OrganizationUpdate(
                            properties=properties
                        ))
    else:
        entity = client.get(entities[0].id)  

    return entity

def validate_course_family_api(deyployment: ComputorDeploymentConfig, api: ApiConfig, organization: OrganizationGet, properties: Optional[CourseFamilyProperties] = None) -> CourseFamilyGet:
    
    client = CrudClient(url_base=api.url,entity_interface=CourseFamilyInterface,auth=(api.user, api.password))
    
    entities = client.list(CourseFamilyQuery(path=deyployment.courseFamily.path, organization_id=organization.id))
    
    if len(entities) == 0:
        entity = client.create(CourseFamilyCreate(
                            title=deyployment.courseFamily.name,
                            path=deyployment.courseFamily.path,
                            description=deyployment.organization.description,
                            organization_id=str(organization.id),
                            properties=properties
                        ))

    elif len(entities) > 0 and properties != None:   
        entity = client.update(str(entities[0].id), CourseFamilyUpdate(
            properties=properties
        ))
    else:
        entity = client.get(entities[0].id)

    return entity

def validate_course_api(deyployment: ComputorDeploymentConfig, api: ApiConfig, course_family: CourseFamilyGet, properties: Optional[CourseProperties] = None, course_create: Optional[CourseCreate] = None) -> CourseGet:

    client = CrudClient(url_base=api.url,entity_interface=CourseInterface,auth=(api.user, api.password))

    entities = client.list(CourseQuery(path=deyployment.course.path, course_family_id=course_family.id))

    if course_create == None:
        course_create = CourseCreate(
                            title=deyployment.course.name,
                            path=deyployment.course.path,
                            description=deyployment.course.description,
                            course_family_id=str(course_family.id),
                            properties=properties
                        )

    if len(entities) == 0:
        entity = client.create(course_create)

    elif len(entities) > 0 and properties != None:   
        entity = client.update(str(entities[0].id), CourseUpdate(
            properties=properties
        ))

    else:
        entity = client.get(entities[0].id)

    return entity

def validate_course_group_api(api: ApiConfig, course_group_deployment: CourseGroupConfig, course_id: UUID | str) -> CourseGroupGet:

    client = CrudClient(url_base=api.url,entity_interface=CourseGroupInterface,auth=(api.user, api.password))
    
    entities = client.list(CourseGroupQuery(title=course_group_deployment.name, course_id=course_id))

    if len(entities) == 0:
        entity = client.create(CourseGroupCreate(
                            title=course_group_deployment.name,
                            course_id=str(course_id)
                        ))
    else:
        entity = client.get(entities[0].id)

    return entity

def validate_execution_backend_api(api: ApiConfig, execution_backend_deployment: ExecutionBackendConfig) -> ExecutionBackendGet:

    client = CrudClient(url_base=api.url,entity_interface=ExecutionBackendInterface,auth=(api.user, api.password))
    
    entities = client.list(ExecutionBackendQuery(slug=execution_backend_deployment.slug))

    if len(entities) == 0:
        # print(f"Execution backend with slug {execution_backend_deployment.slug} was not registered on api startup.")
        raise Exception("Internal server error")
    else:
        entity = client.get(entities[0].id)

    return client.get(entity.id)

def validate_course_execution_backend_api(api: ApiConfig, execution_backend: ExecutionBackendGet, course: CourseGet) -> CourseExecutionBackendGet:

    client = CrudClient(url_base=api.url,entity_interface=CourseExecutionBackendInterface,auth=(api.user, api.password))
    
    entities = client.list(CourseExecutionBackendQuery(execution_backend_id=execution_backend.id, course_id=course.id))

    if len(entities) == 0:
        entity = client.create(CourseExecutionBackendCreate(
                        execution_backend_id=str(execution_backend.id),
                        course_id=str(course.id),
                        properties=execution_backend.properties
                        ))
    else:
        entity = entities[0]

    return entity

def validate_user_api(api: ApiConfig, user_create: Optional[UserCreate] = None) -> UserGet:

    client = CrudClient(url_base=api.url,entity_interface=UserInterface,auth=(api.user, api.password))

    if user_create != None:
        entities = client.list(UserQuery(email=user_create.email))
    
    else:
        raise Exception()

    if len(entities) == 0:
        entity = client.create(user_create)
    else:
        entity = entities[0]

    return entity

client = Client()

def validate_account_api(api: ApiConfig, account_create: AccountCreate) -> AccountGet:
    
    client = CrudClient(url_base=api.url,entity_interface=AccountInterface,auth=(api.user, api.password))
    
    entities = client.list(AccountQuery(provider=account_create.provider, user_id=account_create.user_id, type=account_create.type))

    if len(entities) == 0:
        entity = client.create(account_create)
    else:
        entity = entities[0]

    return entity

def validate_course_member_api(
    api: ApiConfig, 
    user_id: UUID | str, 
    course_id: UUID | str, 
    course_role_id: str, 
    course_group_id: UUID | str | None = None, 
    properties: CourseMemberProperties = None,
    course_member_create: Optional[CourseMemberCreate] = None) -> CourseMemberGet:

    client = CrudClient(url_base=api.url,entity_interface=CourseMemberInterface,auth=(api.user, api.password))
    
    entities = client.list(CourseMemberQuery(user_id=user_id,course_id=course_id))
    
    if course_member_create == None:
        course_member_create = CourseMemberCreate(
            user_id=str(user_id),
            course_id=str(course_id),
            course_group_id=str(course_group_id) if course_group_id != None else None,
            course_role_id=course_role_id,
            properties=properties
        )

    if len(entities) == 0:
        entity = client.create(course_member_create)
    else:
        course_member_update = CourseMemberUpdate(
            course_role_id=course_role_id,
            properties=properties
        )

        entity = client.update(entities[0].id,course_member_update)

    return entity

def validate_course_content_api(api: ApiConfig, course_content_create: CourseContentCreate) -> CourseContentGet:

    client = CrudClient(url_base=api.url,entity_interface=CourseContentInterface,auth=(api.user, api.password))
    
    entities = client.list(CourseContentQuery(path=course_content_create.path,course_id=course_content_create.course_id))

    if len(entities) == 0:
        entity = client.create(course_content_create)
    else:
        course_update = CourseContentUpdate(**course_content_create.model_dump(exclude_unset=True))
        entity = client.update(entities[0].id,course_update)

    return entity

def get_course_content_type_from_slug_api(api: ApiConfig, slug: str, course_content_kind_id: str, course_id: UUID | str) -> CourseContentTypeGet | None:

    client = CrudClient(url_base=api.url,entity_interface=CourseContentTypeInterface,auth=(api.user, api.password))

    list_entity = client.get_first_or_default(CourseContentTypeQuery(slug=slug,course_id=course_id,course_content_kind_id=course_content_kind_id))
    
    if list_entity == None:
        return None

    return client.get(list_entity.id)

def course_update_api(api: ApiConfig, course_id: UUID | str, course_update: CourseUpdate) -> CourseGet:

    client = CrudClient(url_base=api.url,entity_interface=CourseInterface,auth=(api.user, api.password))

    return client.update(course_id, course_update)

def get_course_content_from_path_api(api: ApiConfig, course_id: UUID | str, path: str) -> CourseContentGet | None:

    client = CrudClient(url_base=api.url,entity_interface=CourseContentInterface,auth=(api.user, api.password))
    
    list_entity = client.get_first_or_default(CourseContentQuery(course_id=course_id,path=path))

    if list_entity == None:
        return None

    return client.get(list_entity.id)
    
def get_course_api(api: ApiConfig, course_id: UUID | str):

    client = CrudClient(url_base=api.url,entity_interface=CourseInterface,auth=(api.user, api.password))
    
    return client.get(course_id)

def get_execution_backend_from_slug_api(api: ApiConfig, slug: str) -> ExecutionBackendGet | None:

    client = CrudClient(url_base=api.url,entity_interface=ExecutionBackendInterface,auth=(api.user, api.password))

    list_entity = client.get_first_or_default(ExecutionBackendQuery(slug=slug))

    if list_entity == None:
        return None
    
    return client.get(list_entity.id)

# TODO: create members with group create api
def validate_submission_group_member_api(api: ApiConfig, course_content_get: CourseContentGet, course_member_id: UUID | str) -> SubmissionGroupMemberGet:

    group_client = CrudClient(url_base=api.url,entity_interface=SubmissionGroupInterface,auth=(api.user, api.password))
    member_client = CrudClient(url_base=api.url,entity_interface=SubmissionGroupMemberInterface,auth=(api.user, api.password))
    
    entities = client.list(SubmissionGroupMemberQuery(course_content_id=course_content_get.id,course_member_id=course_member_id))

    if len(entities) == 0:
        group_entity = group_client.create(SubmissionGroupCreate(course_content_id=course_content_get.id))

        entity = member_client.create(SubmissionGroupMemberCreate(course_member_id=course_member_id,submission_group_id=group_entity.id))
    else:
        entity = client.get(entities[0].id)

    return entity