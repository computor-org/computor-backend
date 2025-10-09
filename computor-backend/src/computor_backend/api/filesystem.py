import os
import yaml
import shutil
from uuid import UUID
from sqlalchemy.orm import Session
from aiocache import SimpleMemoryCache
from computor_types.course_contents import CourseContentProperties
from computor_types.organizations import OrganizationProperties
from computor_types.base import EntityInterface
from computor_types.tokens import decrypt_api_key
from computor_backend.model.course import Course, CourseContent, CourseFamily
from computor_backend.model.organization import Organization
from computor_backend.generator.git_helper import clone_or_pull_and_checkout
from computor_backend.settings import settings
from computor_backend.interfaces import CourseInterface, CourseContentInterface

_local_git_cache = SimpleMemoryCache()

_expiry_time = 900 # in seconds

async def cached_clone_or_pull_and_checkout(source_directory_checkout,full_https_git_path, token, commit):

    obj = await _local_git_cache.get(f"{source_directory_checkout}::{full_https_git_path}")

    if obj != None and obj == commit and os.path.exists(os.path.join(source_directory_checkout,".git")):
        return obj
    else:
        clone_or_pull_and_checkout(source_directory_checkout,full_https_git_path, token, commit)

        await _local_git_cache.set(f"{source_directory_checkout}::{full_https_git_path}",commit,_expiry_time)

async def mirror_entity_to_filesystem(id: UUID | str, interface: EntityInterface, db: Session = None):
    
    # not implemented yet
    pass
    # repository_dir = os.path.join(settings.API_LOCAL_STORAGE_DIR,"repositories")

    # if not os.path.exists(repository_dir):
    #     os.makedirs(repository_dir,exist_ok=True)

    # db_type = interface.model

    # if db_type == Course:
    #     query = db.query(db_type,Organization,CourseFamily.path) \
    #         .join(CourseFamily, Course.course_family_id == CourseFamily.id) \
    #             .join(Organization, Course.organization_id == Organization.id) \
    #     .filter(db_type.id == id).first()

    #     course = query[0]
    #     organization = query[1]
        
    #     organization_path = str(organization.path)
    #     course_family_path = str(query[2])
    #     course_path = str(course.path)
        
    #     hirarchy_path = os.path.join(interface.endpoint,organization_path,course_family_path,course_path)
        
    #     organization_properties = OrganizationProperties(**organization.properties)
    #     course_properties = CourseProperties(**course.properties)

    #     if organization_properties.gitlab == None or course_properties.gitlab == None:
    #         raise NotImplementedError("Mirroring ist just for gitlab type organizations implemented yet")
    #     if course.version_identifier == None:
    #         raise Exception("No assignments repository created yet")

    #     token = decrypt_api_key(organization_properties.gitlab.token)
    #     commit = course.version_identifier
    #     full_https_git_path = f"{course_properties.gitlab.web_url}/assignments"

    #     source_directory_checkout = os.path.join(settings.API_LOCAL_STORAGE_DIR,"repositories",str(course.id))
    #     source_directory = source_directory_checkout
    #     destination_directory = os.path.join(settings.API_LOCAL_STORAGE_DIR,hirarchy_path)

    #     await cached_clone_or_pull_and_checkout(source_directory_checkout,full_https_git_path, token, commit)

    #     dir_filter = [".git"]
    #     file_filter = []
    #     dir_whitelist = ["content"]

    #     copy_items = []

    #     for root, dirs, files in os.walk(source_directory):

    #         dirs[:] = [d for d in dirs if d not in dir_filter and d in dir_whitelist]
    #         files[:] = [d for d in files if d not in file_filter]

    #         for name in files + dirs:
    #             source_path = os.path.join(root, name)
    #             relative_path = os.path.relpath(source_path, source_directory)
    #             destination_path = os.path.join(destination_directory, relative_path)

    #             copy_items.append((source_path, destination_path))

    # elif db_type == CourseContent:
    #     query = db.query(db_type,Course,Organization,CourseFamily.path) \
    #         .join(Course, db_type.course_id == Course.id) \
    #             .join(CourseFamily, Course.course_family_id == CourseFamily.id) \
    #                 .join(Organization, Course.organization_id == Organization.id) \
    #     .filter(db_type.id == id).first()

    #     course_content = query[0]
    #     course = query[1]
    #     organization = query[2]

    #     organization_path = str(organization.path)
    #     course_family_path = str(query[3])
    #     course_path = str(course.path)
    #     course_content_path = str(course_content.path)
        
    #     hirarchy_path = os.path.join(interface.endpoint,organization_path,course_family_path,course_path,course_content_path)

    #     organization_properties = OrganizationProperties(**organization.properties)
    #     course_properties = CourseProperties(**course.properties)
    #     course_content_properties = CourseContentProperties(**course_content.properties)

    #     if organization_properties.gitlab == None:
    #         raise NotImplementedError("Mirroring ist just for gitlab type organizations implemented yet")
    #     if course.version_identifier == None:
    #         raise Exception("No assignments repository created yet")
        
    #     course_content_directory_path = course_content_properties.gitlab.directory

    #     commit = course_content.version_identifier

    #     token = decrypt_api_key(organization_properties.gitlab.token)

    #     full_https_git_path = f"{course_properties.gitlab.web_url}/assignments"

    #     source_directory_checkout = os.path.join(repository_dir,str(course.id))
    #     source_directory = os.path.join(repository_dir,str(course.id),course_content_directory_path)
    #     destination_directory = os.path.join(settings.API_LOCAL_STORAGE_DIR,hirarchy_path)

    #     await cached_clone_or_pull_and_checkout(source_directory_checkout,full_https_git_path, token, commit)

    #     dir_filter = [".git"]
    #     file_filter = []
    #     dir_whitelist = ["content","studentTemplates"]

    #     copy_items = []

    #     for root, dirs, files in os.walk(source_directory):

    #         dirs[:] = [d for d in dirs if d not in dir_filter and d in dir_whitelist]
    #         files[:] = [d for d in files if d not in file_filter]

    #         for name in files + dirs:
    #             source_path = os.path.join(root, name)
    #             relative_path = os.path.relpath(source_path, source_directory)
    #             destination_path = os.path.join(destination_directory, relative_path)

    #             copy_items.append((source_path, destination_path))

    # if os.path.exists(destination_directory):# and db_type == CourseContent:

    #     if os.path.exists(os.path.join(destination_directory,".config.yaml")):

    #         with open(os.path.join(destination_directory,".config.yaml"), "r") as file:
    #             config_dict = yaml.safe_load(file)
    #             # TODO: Update to use new commit tracking method
    #             if config_dict.get("commit", config_dict.get("version_identifier")) == commit:
    #                 print("Mirror is up to date")
    #                 return
    #             else:
    #                 shutil.rmtree(destination_directory)
    #     else:
    #         shutil.rmtree(destination_directory)

    # if len(copy_items) == 0:
    #     if not os.path.exists(destination_directory):
    #         os.makedirs(destination_directory,exist_ok=True)
    #     shutil.copytree(os.path.join(source_directory),os.path.join(destination_directory),dirs_exist_ok=True)

    #     with open(os.path.join(destination_directory,".config.yaml"), "w") as file:
    #         yaml.dump({"commit": commit}, file)  # TODO: Update to new tracking method

    # else:
    #     for source, destination in copy_items:
    #         if not os.path.exists(destination_directory):
    #             os.makedirs(destination_directory,exist_ok=True)

    #         source_dir_path = os.path.join(source_directory,source)
    #         destination_dir_path = os.path.join(destination_directory,destination)
    #         if os.path.exists(source_dir_path):
                
    #             if os.path.isfile(source_dir_path):
    #                 shutil.copy(source_dir_path,destination_dir_path)
    #             else:
    #                 shutil.copytree(source_dir_path,destination_dir_path,dirs_exist_ok=True)
                
    #         with open(os.path.join(destination_directory,".config.yaml"), "w") as file:
    #             yaml.dump({"version_identifier": commit}, file)

async def mirror_db_to_filesystem(db: Session):

    courses = db.scalars(db.query(Course.id)).all()
    course_contents = db.scalars(db.query(CourseContent.id)).all()

    for item in courses:
        try:
            await mirror_entity_to_filesystem(item,CourseInterface,db)
        except Exception as e:
            print(f"Mirroring course with id {item} failed. Reason: {e.args}")
    for item in course_contents:
        try:
            await mirror_entity_to_filesystem(item,CourseContentInterface,db)
        except Exception as e:
            print(f"Mirroring course_content with id {item} failed. Reason: {e.args}")

async def get_path_course(id: str | UUID, db: Session):

    path = await _local_git_cache.get(f"dir:courses:{id}")

    if path != None:
        return path

    query = db.query(Organization.path,CourseFamily.path,Course.path) \
        .join(CourseFamily,CourseFamily.id == Course.course_family_id) \
        .join(Organization,Organization.id == CourseFamily.organization_id) \
            .filter(Course.id == id).first()

    path = os.path.join(settings.API_LOCAL_STORAGE_DIR,"courses")

    for segment in query:
        path = os.path.join(path,str(segment))

    await _local_git_cache.set(f"dir:courses:{id}",path,36000)

    return path

async def get_path_course_content(id: str | UUID, db: Session):

    path = await _local_git_cache.get(f"dir:course-contents:{id}")

    if path != None:
        return path

    query = db.query(Organization.path,CourseFamily.path,Course.path,CourseContent.path) \
    .join(Course,Course.id == CourseContent.course_id) \
        .join(CourseFamily,CourseFamily.id == Course.course_family_id) \
        .join(Organization,Organization.id == CourseFamily.organization_id) \
            .filter(CourseContent.id == id).first()

    path = os.path.join(settings.API_LOCAL_STORAGE_DIR,"course-contents")

    for segment in query:
        path = os.path.join(path,str(segment))

    await _local_git_cache.set(f"dir:course-contents:{id}",path,36000)

    return path
