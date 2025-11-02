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