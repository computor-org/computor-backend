from fastapi import APIRouter
from ctutor_backend.api.api_builder import CrudRouter
from ctutor_backend.interface.student_profile import StudentProfileInterface

# Create CRUD router for student profiles
student_profile_crud = CrudRouter(StudentProfileInterface)
student_profile_router = student_profile_crud.router