from typing import Annotated
from uuid import UUID
from fastapi import Depends
from sqlalchemy.orm import Session

from computor_backend.api.filesystem import mirror_entity_to_filesystem
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.database import get_db
from computor_types.courses import CourseGet
from computor_backend.api.api_builder import CrudRouter
from computor_backend.interfaces import CourseInterface

course_router = CrudRouter(CourseInterface)